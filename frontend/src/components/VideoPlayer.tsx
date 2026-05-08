import { useState, useRef, useEffect } from "react";
import { Play, Pause, RotateCcw, Maximize2, Volume2, VolumeX, X, Rewind, FastForward } from "lucide-react";

interface Props { streamUrl: string; title?: string; fileSize?: number; onClose?: () => void; }

function fmt(s: number) {
  if (!isFinite(s) || isNaN(s)) return "0:00";
  const m = Math.floor(s / 60), sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export default function VideoPlayer({ streamUrl, title, fileSize, onClose }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);
  const [showCtrl, setShowCtrl] = useState(true);
  const hideT = useRef<ReturnType<typeof setTimeout> | null>(null);

  const bump = () => {
    if (hideT.current) clearTimeout(hideT.current);
    setShowCtrl(true);
    hideT.current = setTimeout(() => setShowCtrl(false), 3500);
  };

  useEffect(() => {
    bump();
    return () => { if (hideT.current) clearTimeout(hideT.current); };
  }, []);

  // Auto-play on load
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    v.load();
    v.play().catch(() => {});
  }, [streamUrl]);

  const toggle = () => {
    const v = videoRef.current; if (!v) return;
    if (v.paused) { v.play().catch(e => setError("تعذّر التشغيل: " + e.message)); setPlaying(true); }
    else { v.pause(); setPlaying(false); }
    bump();
  };

  const seek = (delta: number) => {
    const v = videoRef.current; if (!v) return;
    v.currentTime = Math.max(0, Math.min(v.duration || 0, v.currentTime + delta));
    bump();
  };

  const handleRetry = () => {
    setError(""); setLoading(true); setRetryCount(c => c + 1);
    const v = videoRef.current; if (!v) return;
    v.load();
    v.play().catch(() => {});
  };

  const fileMB = fileSize ? (fileSize / (1024 * 1024)).toFixed(0) : null;

  return (
    <div style={{ position: "relative", background: "#000", width: "100%", aspectRatio: "16/9" }} onClick={bump}>
      <video
        ref={videoRef}
        src={streamUrl}
        key={`${streamUrl}-${retryCount}`}
        style={{ width: "100%", height: "100%", objectFit: "contain" }}
        playsInline preload="auto" muted={muted}
        onLoadStart={() => setLoading(true)}
        onLoadedMetadata={() => { setDuration(videoRef.current?.duration || 0); setLoading(false); }}
        onCanPlay={() => setLoading(false)}
        onWaiting={() => setLoading(true)}
        onPlaying={() => { setLoading(false); setPlaying(true); }}
        onPause={() => setPlaying(false)}
        onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime || 0)}
        onError={() => setError("تعذّر تحميل الفيديو. تحقق من اتصالك أو أعد المحاولة.")}
        onEnded={() => setPlaying(false)}
      />

      {/* Loading overlay */}
      {loading && !error && (
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, background: "rgba(0,0,0,0.55)" }}>
          <div style={{ width: 34, height: 34, border: "3px solid rgba(255,255,255,0.15)", borderTopColor: "#8b5cf6", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
          <span style={{ fontSize: 12, color: "rgba(255,255,255,0.5)" }}>
            جارٍ التحميل{fileMB ? ` · ${fileMB} MB` : ""}
          </span>
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </div>
      )}

      {/* Error overlay */}
      {error && (
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, background: "rgba(0,0,0,0.9)", padding: 20, textAlign: "center" }}>
          <span style={{ fontSize: 32 }}>⚠️</span>
          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.75)", lineHeight: 1.5 }}>{error}</p>
          {fileMB && (
            <p style={{ fontSize: 11, color: "rgba(255,255,255,0.35)" }}>حجم الملف: {fileMB} MB</p>
          )}
          <button
            onClick={handleRetry}
            style={{ background: "#8b5cf6", color: "#fff", padding: "9px 22px", borderRadius: 20, fontSize: 13, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}
          >
            <RotateCcw size={14} /> إعادة المحاولة {retryCount > 0 ? `(${retryCount})` : ""}
          </button>
          {onClose && (
            <button onClick={onClose} style={{ color: "rgba(255,255,255,0.45)", fontSize: 12, marginTop: 4 }}>
              إغلاق المشغل
            </button>
          )}
        </div>
      )}

      {/* Controls overlay */}
      {!error && (
        <div style={{
          position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "space-between",
          opacity: showCtrl ? 1 : 0, transition: "opacity 0.3s", pointerEvents: showCtrl ? "auto" : "none",
        }}>
          {/* Top bar */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", background: "linear-gradient(to bottom,rgba(0,0,0,0.75),transparent)" }}>
            <span style={{ fontSize: 12, fontWeight: 600, maxWidth: "80%", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
              {title || "مشغل PopCorn 🍿"}
            </span>
            {onClose && (
              <button onClick={onClose} style={{ opacity: 0.8, padding: 4 }}>
                <X size={18} />
              </button>
            )}
          </div>

          {/* Center controls */}
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 20 }}>
            <button onClick={() => seek(-10)} style={{ background: "rgba(0,0,0,0.45)", borderRadius: "50%", padding: 10, backdropFilter: "blur(4px)" }}>
              <Rewind size={18} fill="#fff" color="#fff" />
            </button>
            <button onClick={toggle} style={{ background: "rgba(0,0,0,0.55)", borderRadius: "50%", padding: 14, backdropFilter: "blur(4px)", border: "2px solid rgba(255,255,255,0.3)" }}>
              {playing ? <Pause size={22} fill="#fff" /> : <Play size={22} fill="#fff" />}
            </button>
            <button onClick={() => seek(10)} style={{ background: "rgba(0,0,0,0.45)", borderRadius: "50%", padding: 10, backdropFilter: "blur(4px)" }}>
              <FastForward size={18} fill="#fff" color="#fff" />
            </button>
          </div>

          {/* Bottom controls */}
          <div style={{ padding: "0 12px 10px", background: "linear-gradient(to top,rgba(0,0,0,0.75),transparent)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.7)", minWidth: 36 }}>{fmt(currentTime)}</span>
              <input
                type="range" min={0} max={duration || 100} step={1} value={currentTime}
                onChange={e => { const v = videoRef.current; if (v) v.currentTime = Number(e.target.value); bump(); }}
                style={{ flex: 1, accentColor: "#8b5cf6", height: 3, cursor: "pointer" }}
              />
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.7)", minWidth: 36, textAlign: "left" }}>{fmt(duration)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button onClick={() => { setMuted(!muted); bump(); }}>
                {muted ? <VolumeX size={16} color="#fff" /> : <Volume2 size={16} color="#fff" />}
              </button>
              <button onClick={() => { videoRef.current?.requestFullscreen?.(); bump(); }}>
                <Maximize2 size={16} color="#fff" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
