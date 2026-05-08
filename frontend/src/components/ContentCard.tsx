import { Star, Play, Clock } from "lucide-react";

interface Props {
  id: string;
  type: "movie" | "series";
  title: string;
  title_ar?: string;
  poster_path?: string;
  rating?: number;
  has_file?: boolean;
  year?: string;
  onClick: () => void;
}

export default function ContentCard({ title, title_ar, poster_path, rating, has_file, year, onClick }: Props) {
  const label = title_ar || title;
  const yr = year?.slice(0, 4);

  return (
    <div
      onClick={onClick}
      style={{
        width: "100%",
        cursor: "pointer",
        borderRadius: 12,
        overflow: "hidden",
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.07)",
        transition: "transform 0.15s",
        active: { transform: "scale(0.95)" },
      } as any}
    >
      {/* Poster */}
      <div style={{ position: "relative", aspectRatio: "2/3", overflow: "hidden" }}>
        {poster_path ? (
          <img
            src={poster_path}
            alt={label}
            loading="lazy"
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        ) : (
          <div style={{
            width: "100%", height: "100%",
            background: "linear-gradient(135deg, #1a1a2e, #16213e)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 36,
          }}>🎬</div>
        )}
        {/* Overlay badges */}
        <div style={{ position: "absolute", top: 6, left: 6, right: 6, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          {rating && rating > 0 ? (
            <span style={{
              background: "rgba(0,0,0,0.75)", borderRadius: 6, padding: "2px 6px",
              fontSize: 10, color: "#f59e0b", fontWeight: 700,
              display: "flex", alignItems: "center", gap: 2,
              backdropFilter: "blur(4px)",
            }}>
              <Star size={9} fill="#f59e0b" />{rating.toFixed(1)}
            </span>
          ) : <span />}
          {has_file === false && (
            <span style={{
              background: "rgba(0,0,0,0.75)", borderRadius: 6, padding: "2px 6px",
              fontSize: 9, color: "rgba(255,255,255,0.6)",
              backdropFilter: "blur(4px)",
              display: "flex", alignItems: "center", gap: 2,
            }}>
              <Clock size={8} /> قريباً
            </span>
          )}
          {has_file && (
            <span style={{
              background: "rgba(245,158,11,0.85)", borderRadius: 6, padding: "2px 6px",
              fontSize: 9, color: "#000",
              backdropFilter: "blur(4px)",
              display: "flex", alignItems: "center", gap: 2,
            }}>
              <Play size={8} fill="#000" /> متاح
            </span>
          )}
        </div>
        {/* Bottom gradient */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0, height: "50%",
          background: "linear-gradient(to top, rgba(0,0,0,0.7), transparent)",
        }} />
      </div>
      {/* Text info */}
      <div style={{ padding: "8px 8px 10px" }}>
        <p style={{
          fontSize: 11, fontWeight: 600, lineHeight: 1.3,
          overflow: "hidden", display: "-webkit-box",
          WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any,
          color: "rgba(255,255,255,0.88)",
        }}>{label}</p>
        {yr && (
          <p style={{ fontSize: 10, color: "rgba(255,255,255,0.35)", marginTop: 3 }}>{yr}</p>
        )}
      </div>
    </div>
  );
}
