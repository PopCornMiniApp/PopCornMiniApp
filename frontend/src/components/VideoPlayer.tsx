/**
 * PopCorn VideoPlayer — Professional Streaming Component
 * ────────────────────────────────────────────────────────
 * • Full-screen overlay player optimised for Telegram Mini Apps (WebView)
 * • Progressive / Range-request streaming (works with large files via Pyrogram)
 * • Intelligent loading states: buffering spinner, stall detection, retry logic
 * • Native controls hidden; custom controls layer for consistent cross-platform UX
 * • Seek bar with live scrubbing, skip ±10s, mute, fullscreen
 * • Auto-hides controls after 3.5 s of inactivity
 * • Displays file size in MB during load for user transparency
 */
import { useState, useRef, useEffect, useCallback } from "react";
import {
  Play, Pause, RotateCcw, Maximize2, Volume2, VolumeX,
  X, Rewind, FastForward, Loader2,
} from "lucide-react";

interface Props {
  streamUrl: string;
  title?: string;
  fileSize?: number;
  onClose?: () => void;
}

function fmtTime(s: number) {
  if (!isFinite(s) || isNaN(s) || s < 0) return "0:00";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function fmtMB(bytes: number) {
  if (!bytes) return null;
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(1)} GB`;
  return `${Math.round(bytes / 1048576)} MB`;
}

type PlayerState = "loading" | "playing" | "paused" | "buffering" | "stalled" | "error";

export default function VideoPlayer({ streamUrl, title, fileSize, onClose }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stallTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [state, setState] = useState<PlayerState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);
  const [showCtrl, setShowCtrl] = useState(true);
  const [buffered, setBuffered] = useState(0); // 0-1

  // ── Controls auto-hide ───────────────────────────────────────────────────
  const showControls = useCallback(() => {
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    setShowCtrl(true);
    hideTimerRef.current = setTimeout(() => setShowCtrl(false), 3500);
  }, []);

  useEffect(() => {
    showControls();
    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
      if (stallTimerRef.current) clearTimeout(stallTimerRef.current);
    };
  }, []);

  // ── Auto-play on mount / URL change ──────────────────────────────────────
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    setState("loading");
    setErrorMsg("");
    setCurrentTime(0);
    setDuration(0);

    // Load and attempt play — user gesture may be required in some WebViews
    v.load();
    const p = v.play();
    if (p) {
      p.catch(() => {
        // Autoplay blocked — show paused state so user can tap Play
        setState("paused");
      });
    }
  }, [streamUrl, retryCount]);

  // ── Buffered progress ────────────────────────────────────────────────────
  const updateBuffered = useCallback(() => {
    const v = videoRef.current;
    if (!v || !v.duration) return;
    const buf = v.buffered;
    if (buf.length) {
      setBuffered(buf.end(buf.length - 1) / v.duration);
    }
  }, []);

  // ── Stall guard: if video stalls >8s declare an error ───────────────────
  const startStallTimer = useCallback(() => {
    if (stallTimerRef.current) clearTimeout(stallTimerRef.current);
    stallTimerRef.current = setTimeout(() => {
      setState("stalled");
    }, 8000);
  }, []);

  const clearStallTimer = useCallback(() => {
    if (stallTimerRef.current) clearTimeout(stallTimerRef.current);
  }, []);

  // ── Video event handlers ─────────────────────────────────────────────────
  const onLoadStart = () => setState("loading");

  const onLoadedMetadata = () => {
    const v = videoRef.current;
    if (v) setDuration(v.duration);
    clearStallTimer();
  };

  const onCanPlay = () => {
    clearStallTimer();
    if (state === "loading" || state === "buffering") setState("paused");
  };

  const onPlaying = () => {
    clearStallTimer();
    setState("playing");
    setErrorMsg("");
  };

  const onPause = () => {
    if (state === "playing") setState("paused");
  };

  const onWaiting = () => {
    setState("buffering");
    startStallTimer();
  };

  const onSuspend = () => {
    // Suspended while still loading first frame → show buffering
    if (state === "loading") setState("buffering");
  };

  const onTimeUpdate = () => {
    const v = videoRef.current;
    if (v) {
      setCurrentTime(v.currentTime);
      updateBuffered();
    }
    clearStallTimer();
    if (state === "buffering" || state === "stalled") setState("playing");
  };

  const onEnded = () => setState("paused");

  const onError = () => {
    const v = videoRef.current;
    let msg = "تعذّر تحميل الفيديو — يرجى إعادة المحاولة";
    if (v?.error) {
      switch (v.error.code) {
        case 1: msg = "تم إلغاء التحميل"; break;
        case 2: msg = "خطأ في الشبكة — تحقق من اتصالك"; break;
        case 3: msg = "خطأ في فك ترميز الفيديو"; break;
        case 4: msg = "صيغة الفيديو غير مدعومة أو تعذّر الوصول إليه"; break;
      }
    }
    setErrorMsg(msg);
    setState("error");
  };

  // ── Playback controls ────────────────────────────────────────────────────
  const toggle = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused || v.ended) {
      v.play().catch(e => { setErrorMsg("تعذّر التشغيل: " + e.message); setState("error"); });
    } else {
      v.pause();
    }
    showControls();
  };

  const seek = (delta: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Math.max(0, Math.min(v.duration || 0, v.currentTime + delta));
    showControls();
  };

  const handleSeekBar = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = videoRef.current;
    if (!v) return;
    const t = Number(e.target.value);
    v.currentTime = t;
    setCurrentTime(t);
    showControls();
  };

  const toggleMute = () => {
    setMuted(m => !m);
    showControls();
  };

  const goFullscreen = () => {
    const el = wrapRef.current;
    if (!el) return;
    if (document.fullscreenElement) {
      document.exitFullscreen?.();
    } else {
      (el.requestFullscreen?.() || (el as any).webkitRequestFullscreen?.());
    }
    showControls();
  };

  const handleRetry = () => {
    setErrorMsg("");
    setState("loading");
    setRetryCount(c => c + 1);
  };

  // ── Derived flags ─────────────────────────────────────────────────────────
  const isLoading  = state === "loading" || state === "buffering";
  const isStalled  = state === "stalled";
  const isError    = state === "error";
  const isPlaying  = state === "playing";
  const fileSizeFmt = fileSize ? fmtMB(fileSize) : null;

  // Absolute URL so Telegram WebView doesn't mangle relative paths
  const absUrl = streamUrl.startsWith("http")
    ? streamUrl
    : `${window.location.origin}${streamUrl}`;

  return (
    <div
      ref={wrapRef}
      style={{ position: "relative", background: "#000", width: "100%", aspectRatio: "16/9", overflow: "hidden" }}
      onClick={showControls}
    >
      {/* ── Video element ─────────────────────────────────── */}
      <video
        ref={videoRef}
        key={`${absUrl}-${retryCount}`}
        src={absUrl}
        style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
        playsInline
        preload="metadata"
        muted={muted}
        onLoadStart={onLoadStart}
        onLoadedMetadata={onLoadedMetadata}
        onCanPlay={onCanPlay}
        onPlaying={onPlaying}
        onPause={onPause}
        onWaiting={onWaiting}
        onSuspend={onSuspend}
        onTimeUpdate={onTimeUpdate}
        onProgress={updateBuffered}
        onEnded={onEnded}
        onError={onError}
      />

      {/* ── Buffered track (behind seek bar) ─────────────── */}
      <style>{`
        @keyframes pc-spin { to { transform: rotate(360deg) } }
        @keyframes pc-pulse { 0%,100% { opacity:.6 } 50% { opacity:1 } }
        input[type=range].pc-seek { -webkit-appearance:none; appearance:none; height:3px; border-radius:2px; cursor:pointer; outline:none; }
        input[type=range].pc-seek::-webkit-slider-thumb { -webkit-appearance:none; width:14px; height:14px; border-radius:50%; background:#8b5cf6; cursor:pointer; }
        input[type=range].pc-seek::-moz-range-thumb { width:14px; height:14px; border-radius:50%; background:#8b5cf6; cursor:pointer; border:none; }
      `}</style>

      {/* ── Loading / Buffering overlay ───────────────────── */}
      {(isLoading || isStalled) && !isError && (
        <div style={{
          position: "absolute", inset: 0, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 10,
          background: "rgba(0,0,0,0.6)",
        }}>
          <Loader2
            size={36}
            color="#8b5cf6"
            style={{ animation: "pc-spin 0.8s linear infinite" }}
          />
          <p style={{ fontSize: 12, color: "rgba(255,255,255,0.55)", textAlign: "center", lineHeight: 1.5 }}>
            {isStalled ? "الشبكة بطيئة — يُحاول الاتصال مجدداً…" : "جارٍ التحميل…"}
          </p>
          {fileSizeFmt && (
            <p style={{ fontSize: 10, color: "rgba(255,255,255,0.28)" }}>{fileSizeFmt}</p>
          )}
          {isStalled && (
            <button onClick={handleRetry} style={{
              marginTop: 6, background: "#8b5cf6", color: "#fff",
              padding: "7px 18px", borderRadius: 20, fontSize: 12, fontWeight: 700,
            }}>
              إعادة الاتصال
            </button>
          )}
        </div>
      )}

      {/* ── Error overlay ─────────────────────────────────── */}
      {isError && (
        <div style={{
          position: "absolute", inset: 0, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 14,
          background: "rgba(0,0,0,0.92)", padding: "20px", textAlign: "center",
        }}>
          <span style={{ fontSize: 36 }}>⚠️</span>
          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.75)", lineHeight: 1.6, maxWidth: 260 }}>
            {errorMsg}
          </p>
          {fileSizeFmt && (
            <p style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>
              حجم الملف: {fileSizeFmt}
            </p>
          )}
          <button onClick={handleRetry} style={{
            background: "linear-gradient(135deg,#8b5cf6,#7c3aed)",
            color: "#fff", padding: "10px 24px", borderRadius: 22,
            fontSize: 13, fontWeight: 700,
            display: "flex", alignItems: "center", gap: 7,
            boxShadow: "0 4px 14px rgba(139,92,246,0.4)",
          }}>
            <RotateCcw size={14} />
            إعادة المحاولة {retryCount > 0 ? `(${retryCount})` : ""}
          </button>
          {onClose && (
            <button onClick={onClose} style={{ color: "rgba(255,255,255,0.38)", fontSize: 12, marginTop: 2 }}>
              إغلاق المشغل
            </button>
          )}
        </div>
      )}

      {/* ── Controls overlay ──────────────────────────────── */}
      {!isError && (
        <div style={{
          position: "absolute", inset: 0, display: "flex", flexDirection: "column",
          justifyContent: "space-between",
          opacity: showCtrl ? 1 : 0,
          transition: "opacity 0.28s ease",
          pointerEvents: showCtrl ? "auto" : "none",
        }}>
          {/* Top bar */}
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "10px 14px",
            background: "linear-gradient(to bottom,rgba(0,0,0,0.72) 0%,transparent 100%)",
          }}>
            <span style={{
              fontSize: 12, fontWeight: 700, maxWidth: "80%",
              overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis",
              textShadow: "0 1px 3px rgba(0,0,0,0.8)",
            }}>
              {title || "🍿 PopCorn"}
            </span>
            {onClose && (
              <button
                onClick={onClose}
                style={{ background: "rgba(0,0,0,0.4)", borderRadius: "50%", padding: 5, backdropFilter: "blur(4px)" }}
              >
                <X size={16} />
              </button>
            )}
          </div>

          {/* Center controls */}
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 22 }}>
            <button
              onClick={() => seek(-10)}
              style={{ background: "rgba(0,0,0,0.45)", borderRadius: "50%", padding: 11, backdropFilter: "blur(6px)" }}
            >
              <Rewind size={20} fill="#fff" color="#fff" />
            </button>

            <button
              onClick={toggle}
              style={{
                background: "rgba(0,0,0,0.55)", borderRadius: "50%", padding: 16,
                backdropFilter: "blur(6px)", border: "2px solid rgba(255,255,255,0.25)",
              }}
            >
              {(isLoading) ? (
                <Loader2 size={24} color="#fff" style={{ animation: "pc-spin 0.8s linear infinite" }} />
              ) : isPlaying ? (
                <Pause size={24} fill="#fff" color="#fff" />
              ) : (
                <Play size={24} fill="#fff" color="#fff" />
              )}
            </button>

            <button
              onClick={() => seek(10)}
              style={{ background: "rgba(0,0,0,0.45)", borderRadius: "50%", padding: 11, backdropFilter: "blur(6px)" }}
            >
              <FastForward size={20} fill="#fff" color="#fff" />
            </button>
          </div>

          {/* Bottom controls */}
          <div style={{
            padding: "0 14px 12px",
            background: "linear-gradient(to top,rgba(0,0,0,0.75) 0%,transparent 100%)",
          }}>
            {/* Seek bar */}
            <div style={{ position: "relative", marginBottom: 8 }}>
              {/* Buffered track */}
              <div style={{
                position: "absolute", top: "50%", transform: "translateY(-50%)",
                left: 0, height: 3, borderRadius: 2, pointerEvents: "none",
                width: `${buffered * 100}%`,
                background: "rgba(255,255,255,0.25)",
              }} />
              <input
                className="pc-seek"
                type="range"
                min={0}
                max={duration || 100}
                step={0.5}
                value={currentTime}
                onChange={handleSeekBar}
                style={{
                  width: "100%",
                  background: `linear-gradient(to right, #8b5cf6 ${duration ? (currentTime / duration) * 100 : 0}%, rgba(255,255,255,0.15) 0%)`,
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <button onClick={toggleMute}>
                  {muted ? <VolumeX size={17} color="#fff" /> : <Volume2 size={17} color="#fff" />}
                </button>
                <span style={{ fontSize: 10, color: "rgba(255,255,255,0.6)", fontVariantNumeric: "tabular-nums" }}>
                  {fmtTime(currentTime)} / {fmtTime(duration)}
                </span>
              </div>
              <button onClick={goFullscreen}>
                <Maximize2 size={17} color="#fff" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
