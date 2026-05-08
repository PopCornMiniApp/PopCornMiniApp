import { useState, useEffect } from "react";
import { api, type Movie } from "../api";
import VideoPlayer from "../components/VideoPlayer";
import { ArrowRight, Star, Clock, Play, Calendar, Users, ThumbsUp } from "lucide-react";

interface Props { id: string; navigate: (r: any) => void; goBack: () => void; }

function fmtRuntime(min?: number) {
  if (!min) return "";
  const h = Math.floor(min / 60), m = min % 60;
  return h > 0 ? `${h}س ${m}د` : `${m}د`;
}

export default function MovieDetail({ id, navigate, goBack }: Props) {
  const [movie, setMovie] = useState<Movie | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [playing, setPlaying] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setLoading(true); setError(""); setPlaying(false); setExpanded(false);
    api.movie(id)
      .then(m => { setMovie(m); setLoading(false); })
      .catch(() => { setError("تعذّر تحميل تفاصيل الفيلم"); setLoading(false); });
  }, [id]);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", flexDirection: "column", gap: 12 }}>
      <div style={{ width: 36, height: 36, border: "3px solid rgba(255,255,255,0.1)", borderTopColor: "#f59e0b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  if (error || !movie) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "80vh", gap: 16, padding: 20 }}>
      <span style={{ fontSize: 40 }}>😕</span>
      <p style={{ color: "rgba(255,255,255,0.6)", textAlign: "center" }}>{error || "الفيلم غير موجود"}</p>
      <button onClick={goBack} style={{ background: "#f59e0b", color: "#000", padding: "8px 24px", borderRadius: 20, fontWeight: 700 }}>رجوع</button>
    </div>
  );

  const title = movie.title_ar || movie.title;
  const overview = movie.overview_ar || movie.overview;
  const year = movie.release_date?.slice(0, 4) || "";
  const runtime = fmtRuntime(movie.runtime);
  const genres = Array.isArray(movie.genres) ? movie.genres : [];
  const cast = Array.isArray(movie.cast) ? movie.cast : [];

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      {/* Back button — respects Telegram safe area */}
      {!playing && (
        <button onClick={goBack} style={{
          position: "fixed",
          top: "calc(var(--tg-safe-top, env(safe-area-inset-top, 0px)) + 12px)",
          right: 12, zIndex: 100,
          background: "rgba(0,0,0,0.65)", borderRadius: "50%", padding: 9,
          backdropFilter: "blur(8px)", border: "1px solid rgba(255,255,255,0.12)",
        }}>
          <ArrowRight size={18} />
        </button>
      )}

      {/* Hero backdrop */}
      <div style={{ position: "relative" }}>
        {movie.backdrop_path && !playing && (
          <div style={{ position: "relative", height: "60vw", maxHeight: 300, overflow: "hidden" }}>
            <img src={movie.backdrop_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} loading="lazy" />
            <div style={{ position: "absolute", inset: 0,
              background: "linear-gradient(to bottom, rgba(13,13,13,0.15) 0%, rgba(13,13,13,0.6) 60%, #0d0d0d 100%)" }} />
          </div>
        )}
        {playing && movie.stream_url && (
          <VideoPlayer streamUrl={movie.stream_url} title={title} fileSize={movie.file_size} onClose={() => setPlaying(false)} />
        )}
      </div>

      <div style={{ padding: "0 16px 80px" }}>
        {/* Title + poster */}
        <div style={{ display: "flex", gap: 14, marginTop: playing ? 16 : -50, position: "relative" }}>
          {movie.poster_path && !playing && (
            <div style={{ flexShrink: 0, width: 95, height: 142, borderRadius: 12, overflow: "hidden",
              boxShadow: "0 8px 28px rgba(0,0,0,0.7)", border: "2px solid rgba(255,255,255,0.1)" }}>
              <img src={movie.poster_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} loading="lazy" />
            </div>
          )}
          <div style={{ flex: 1, paddingTop: playing ? 0 : 52 }}>
            <h1 style={{ fontSize: 19, fontWeight: 800, lineHeight: 1.3, marginBottom: 4 }}>{title}</h1>
            {movie.title !== movie.title_ar && movie.title_ar && (
              <p style={{ fontSize: 11, color: "rgba(255,255,255,0.38)", marginBottom: 6 }}>{movie.title}</p>
            )}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              {movie.rating > 0 && (
                <span style={{ display: "flex", alignItems: "center", gap: 3, color: "#f59e0b", fontSize: 14, fontWeight: 700 }}>
                  <Star size={13} fill="#f59e0b" />{movie.rating.toFixed(1)}
                </span>
              )}
              {movie.vote_count > 0 && (
                <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 11, color: "rgba(255,255,255,0.4)" }}>
                  <ThumbsUp size={10} />{movie.vote_count.toLocaleString()}
                </span>
              )}
              {year && <span style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", display: "flex", alignItems: "center", gap: 3 }}><Calendar size={10} />{year}</span>}
              {runtime && <span style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", display: "flex", alignItems: "center", gap: 3 }}><Clock size={10} />{runtime}</span>}
            </div>
          </div>
        </div>

        {/* Watch button */}
        {movie.has_file && !playing && (
          <button onClick={() => setPlaying(true)} style={{
            width: "100%", marginTop: 18,
            background: "linear-gradient(135deg, #f59e0b, #d97706)",
            color: "#000", padding: "14px 24px", borderRadius: 16,
            fontWeight: 800, fontSize: 16,
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            boxShadow: "0 6px 24px rgba(245,158,11,0.5)",
          }}>
            <Play size={20} fill="#000" /> مشاهدة الفيلم
          </button>
        )}
        {!movie.has_file && (
          <div style={{
            width: "100%", marginTop: 18, background: "rgba(255,255,255,0.04)",
            padding: "14px 24px", borderRadius: 16, textAlign: "center",
            color: "rgba(255,255,255,0.35)", fontSize: 13, border: "1px dashed rgba(255,255,255,0.1)",
          }}>⏳ قريباً — الفيلم غير متاح بعد</div>
        )}

        {/* Genres */}
        {genres.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 16 }}>
            {genres.map((g: any) => {
              const label = typeof g === "string" ? g : g.name;
              return (
                <button key={label} onClick={() => navigate({ page: "browse", genre: label })}
                  style={{
                    padding: "5px 14px", borderRadius: 20, fontSize: 11, cursor: "pointer",
                    background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)",
                    color: "#fde68a", transition: "background 0.2s",
                  }}>{label}</button>
              );
            })}
          </div>
        )}

        {/* Overview */}
        {overview && (
          <div style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: "#f59e0b" }}>القصة</h3>
            <div style={{ position: "relative" }}>
              <p style={{
                fontSize: 13, lineHeight: 1.8, color: "rgba(255,255,255,0.72)",
                overflow: expanded ? "visible" : "hidden",
                display: expanded ? "block" : "-webkit-box",
                WebkitLineClamp: expanded ? undefined : 4,
                WebkitBoxOrient: "vertical" as any,
              }}>{overview}</p>
              {!expanded && overview.length > 200 && (
                <button onClick={() => setExpanded(true)} style={{
                  color: "#f59e0b", fontSize: 12, marginTop: 4, display: "block",
                }}>اقرأ المزيد...</button>
              )}
            </div>
          </div>
        )}

        {/* Details row */}
        {(movie.director || movie.release_date) && (
          <div style={{ marginTop: 18, background: "rgba(255,255,255,0.03)", borderRadius: 14, padding: "14px 16px",
            border: "1px solid rgba(255,255,255,0.07)", display: "flex", flexDirection: "column", gap: 10 }}>
            {movie.director && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>المخرج</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#fff" }}>{movie.director}</span>
              </div>
            )}
            {movie.release_date && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>تاريخ الإصدار</span>
                <span style={{ fontSize: 13, color: "#fff" }}>{movie.release_date}</span>
              </div>
            )}
            {movie.runtime > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>المدة</span>
                <span style={{ fontSize: 13, color: "#fff" }}>{fmtRuntime(movie.runtime)}</span>
              </div>
            )}
            {movie.vote_count > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>عدد التقييمات</span>
                <span style={{ fontSize: 13, color: "#fff" }}>{movie.vote_count.toLocaleString()}</span>
              </div>
            )}
          </div>
        )}

        {/* Cast */}
        {cast.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: "#f59e0b", display: "flex", alignItems: "center", gap: 6 }}>
              <Users size={14} /> طاقم العمل
            </h3>
            <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 8, scrollbarWidth: "none" } as any}>
              {cast.slice(0, 12).map((actor: any, i: number) => {
                const name = typeof actor === "string" ? actor : (actor.name || "");
                const char = typeof actor === "object" ? (actor.character || "") : "";
                const photo = typeof actor === "object" ? (actor.profile || actor.profile_path || null) : null;
                return (
                  <div key={i} style={{ flexShrink: 0, textAlign: "center", width: 64 }}>
                    <div style={{ width: 56, height: 56, borderRadius: "50%", overflow: "hidden",
                      background: "rgba(255,255,255,0.08)", margin: "0 auto 6px",
                      border: "2px solid rgba(245,158,11,0.35)" }}>
                      {photo
                        ? <img src={photo} alt={name} style={{ width: "100%", height: "100%", objectFit: "cover" }}
                            loading="lazy"
                            onError={e => { (e.target as HTMLImageElement).style.display = "none"; }} />
                        : <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22 }}>👤</div>
                      }
                    </div>
                    <p style={{ fontSize: 9.5, color: "rgba(255,255,255,0.75)", lineHeight: 1.3,
                      overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any }}>{name}</p>
                    {char && <p style={{ fontSize: 8, color: "rgba(255,255,255,0.35)", marginTop: 2,
                      overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{char}</p>}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
