import { useRef, useState, useEffect } from "react";
import { X, Maximize2, Minimize2, Play, Pause, Volume2, VolumeX } from "lucide-react";

interface Props {
  streamUrl: string;
  title: string;
  fileSize?: number;
  onClose: () => void;
}

function fmtSize(bytes?: number) {
  if (!bytes) return "";
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  return `${(bytes / 1e6).toFixed(0)} MB`;
}

function fmtTime(s: number) {
  if (!isFinite(s) || s < 0) return "0:00";
  const m = Math.floor(s / 60), sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function SkipIcon({ seconds, forward }: { seconds: number; forward: boolean }) {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      {forward ? (
        <path d="M14 4 A10 10 0 1 1 6 20" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none"/>
      ) : (
        <path d="M14 4 A10 10 0 1 0 22 20" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none"/>
      )}
      {forward
        ? <polyline points="18,1 22,5 18,9" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        : <polyline points="10,1 6,5 10,9" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
      }
      <text x="14" y="17" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold" fontFamily="system-ui">
        {seconds}
      </text>
    </svg>
  );
}

export default function VideoPlayer({ streamUrl, title, fileSize, onClose }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [controlsVisible, setControlsVisible] = useState(true);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) { v.play().catch(() => {}); }
    else { v.pause(); }
  };

  const toggleMute = () => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
  };

  const seek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = videoRef.current;
    if (!v || !duration) return;
    const t = (Number(e.target.value) / 100) * duration;
    v.currentTime = t;
    setCurrentTime(t);
  };

  const skipSeconds = (sec: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Math.max(0, Math.min((v.currentTime || 0) + sec, duration || 0));
  };

  const toggleFullscreen = async () => {
    const el = containerRef.current;
    if (!el) return;
    try {
      if (!isFullscreen) {
        if (el.requestFullscreen) await el.requestFullscreen();
        else if ((el as any).webkitRequestFullscreen) await (el as any).webkitRequestFullscreen();
        else if ((el as any).mozRequestFullScreen) await (el as any).mozRequestFullScreen();
        else setIsFullscreen(true);
      } else {
        if (document.exitFullscreen) await document.exitFullscreen();
        else if ((document as any).webkitExitFullscreen) await (document as any).webkitExitFullscreen();
        else setIsFullscreen(false);
      }
    } catch {
      setIsFullscreen(v => !v);
    }
  };

  useEffect(() => {
    const onFsChange = () => {
      const fs = !!(document.fullscreenElement || (document as any).webkitFullscreenElement);
      setIsFullscreen(fs);
    };
    document.addEventListener("fullscreenchange", onFsChange);
    document.addEventListener("webkitfullscreenchange", onFsChange);
    return () => {
      document.removeEventListener("fullscreenchange", onFsChange);
      document.removeEventListener("webkitfullscreenchange", onFsChange);
    };
  }, []);

  const showControls = () => {
    setControlsVisible(true);
    if (hideTimer.current) clearTimeout(hideTimer.current);
    if (playing) hideTimer.current = setTimeout(() => setControlsVisible(false), 3000);
  };

  useEffect(() => () => { if (hideTimer.current) clearTimeout(hideTimer.current); }, []);

  const progress = duration ? (currentTime / duration) * 100 : 0;
  const isCssFs = isFullscreen && !document.fullscreenElement;

  return (
    <div
      ref={containerRef}
      onClick={showControls}
      style={{
        position: isCssFs ? "fixed" : "relative",
        inset: isCssFs ? 0 : undefined,
        zIndex: isCssFs ? 9999 : undefined,
        background: "#000",
        aspectRatio: isCssFs ? undefined : "16/9",
        width: "100%",
        height: isCssFs ? "100%" : undefined,
        overflow: "hidden",
      }}
    >
      <video
        ref={videoRef}
        src={streamUrl}
        style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
        playsInline
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime || 0)}
        onLoadedMetadata={() => setDuration(videoRef.current?.duration || 0)}
        onEnded={() => setPlaying(false)}
      />

      <div style={{
        position: "absolute", inset: 0,
        background: controlsVisible
          ? "linear-gradient(to bottom, rgba(0,0,0,0.6) 0%, transparent 25%, transparent 60%, rgba(0,0,0,0.85) 100%)"
          : "transparent",
        opacity: controlsVisible ? 1 : 0,
        transition: "opacity 0.3s",
        display: "flex", flexDirection: "column", justifyContent: "space-between",
        padding: "10px 12px",
        pointerEvents: controlsVisible ? "auto" : "none",
      }}>
        {/* Top bar */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <button onClick={e => { e.stopPropagation(); onClose(); }}
            style={{ background: "rgba(0,0,0,0.5)", borderRadius: "50%", padding: 6, display: "flex" }}>
            <X size={18} />
          </button>
          <p style={{ fontSize: 12, fontWeight: 600, color: "#fff", maxWidth: "65%",
            overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{title}</p>
          <button onClick={e => { e.stopPropagation(); toggleFullscreen(); }}
            style={{ background: "rgba(0,0,0,0.5)", borderRadius: "50%", padding: 6, display: "flex" }}>
            {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
        </div>

        {/* Center controls: skip-back | play | skip-forward */}
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 28 }}>
          <button
            onClick={e => { e.stopPropagation(); skipSeconds(-10); }}
            style={{ background: "rgba(0,0,0,0.45)", borderRadius: "50%", padding: 10, display: "flex",
              backdropFilter: "blur(4px)", border: "1px solid rgba(255,255,255,0.15)" }}>
            <SkipIcon seconds={10} forward={false} />
          </button>
          <button onClick={e => { e.stopPropagation(); togglePlay(); }}
            style={{ background: "rgba(0,0,0,0.65)", borderRadius: "50%", padding: 16, display: "flex",
              backdropFilter: "blur(4px)", border: "2px solid rgba(255,255,255,0.25)" }}>
            {playing ? <Pause size={30} /> : <Play size={30} fill="#fff" />}
          </button>
          <button
            onClick={e => { e.stopPropagation(); skipSeconds(10); }}
            style={{ background: "rgba(0,0,0,0.45)", borderRadius: "50%", padding: 10, display: "flex",
              backdropFilter: "blur(4px)", border: "1px solid rgba(255,255,255,0.15)" }}>
            <SkipIcon seconds={10} forward={true} />
          </button>
        </div>

        {/* Bottom controls */}
        <div>
          <input type="range" min={0} max={100} value={progress} onChange={seek}
            onClick={e => e.stopPropagation()}
            style={{
              width: "100%", height: 3, cursor: "pointer", marginBottom: 8,
              accentColor: "#f59e0b",
              background: `linear-gradient(to right, #f59e0b ${progress}%, rgba(255,255,255,0.2) ${progress}%)`,
              borderRadius: 2,
            }}
          />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button onClick={e => { e.stopPropagation(); toggleMute(); }} style={{ display: "flex" }}>
                {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.7)" }}>
                {fmtTime(currentTime)} / {fmtTime(duration)}
              </span>
            </div>
            {fileSize && (
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{fmtSize(fileSize)}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
