import { useState, useEffect } from "react";
import { api, type Movie } from "../api";
import VideoPlayer from "../components/VideoPlayer";
import { ArrowRight, Star, Clock, Play, Calendar } from "lucide-react";

interface Props { id: string; navigate: (r: any) => void; goBack: () => void; }

export default function MovieDetail({ id, navigate, goBack }: Props) {
  const [movie, setMovie] = useState<Movie | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    setLoading(true); setError(""); setPlaying(false);
    api.movie(id)
      .then(m => { setMovie(m); setLoading(false); })
      .catch(e => { setError("تعذّر تحميل تفاصيل الفيلم"); setLoading(false); });
  }, [id]);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", flexDirection: "column", gap: 12 }}>
      <div style={{ width: 36, height: 36, border: "3px solid rgba(255,255,255,0.1)", borderTopColor: "#8b5cf6", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  if (error || !movie) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "80vh", gap: 16, padding: 20 }}>
      <span style={{ fontSize: 40 }}>😕</span>
      <p style={{ color: "rgba(255,255,255,0.6)", textAlign: "center" }}>{error || "الفيلم غير موجود"}</p>
      <button onClick={goBack} style={{ background: "#8b5cf6", color: "#fff", padding: "8px 24px", borderRadius: 20, fontWeight: 700 }}>رجوع</button>
    </div>
  );

  const title = movie.title_ar || movie.title;
  const overview = movie.overview_ar || movie.overview;
  const year = movie.release_date?.slice(0, 4) || "";
  const runtime = movie.runtime ? `${Math.floor(movie.runtime / 60)}س ${movie.runtime % 60}د` : "";
  const genres = Array.isArray(movie.genres) ? movie.genres : [];
  const cast = Array.isArray(movie.cast) ? movie.cast : [];

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      {/* Backdrop */}
      <div style={{ position: "relative" }}>
        {movie.backdrop_path && !playing && (
          <div style={{ position: "relative", height: "55vw", maxHeight: 280, overflow: "hidden" }}>
            <img src={movie.backdrop_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            <div style={{
              position: "absolute", inset: 0,
              background: "linear-gradient(to bottom, rgba(13,13,13,0.2) 0%, rgba(13,13,13,0.7) 70%, #0d0d0d 100%)",
            }} />
          </div>
        )}

        {/* Video player */}
        {playing && movie.stream_url && (
          <div style={{ padding: "0 0 0 0" }}>
            <VideoPlayer
              streamUrl={movie.stream_url}
              title={title}
              fileSize={movie.file_size}
              onClose={() => setPlaying(false)}
            />
          </div>
        )}

        {/* Back button */}
        <button onClick={goBack} style={{
          position: "absolute", top: 12, right: 12, zIndex: 30,
          background: "rgba(0,0,0,0.55)", borderRadius: "50%", padding: 8,
          backdropFilter: "blur(4px)",
        }}>
          <ArrowRight size={18} />
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: "0 16px 80px" }}>
        {/* Title + poster row */}
        <div style={{ display: "flex", gap: 14, marginTop: playing ? 16 : -40, position: "relative" }}>
          {movie.poster_path && !playing && (
            <div style={{ flexShrink: 0, width: 90, height: 135, borderRadius: 10, overflow: "hidden",
              boxShadow: "0 8px 24px rgba(0,0,0,0.6)", border: "2px solid rgba(255,255,255,0.1)" }}>
              <img src={movie.poster_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            </div>
          )}
          <div style={{ flex: 1, paddingTop: playing ? 0 : 45 }}>
            <h1 style={{ fontSize: 18, fontWeight: 800, lineHeight: 1.3, marginBottom: 6 }}>{title}</h1>
            {movie.title !== movie.title_ar && movie.title_ar && (
              <p style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", marginBottom: 6 }}>{movie.title}</p>
            )}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              {movie.rating > 0 && (
                <span style={{ display: "flex", alignItems: "center", gap: 3, color: "#f59e0b", fontSize: 13, fontWeight: 700 }}>
                  <Star size={12} fill="#f59e0b" />{movie.rating.toFixed(1)}
                </span>
              )}
              {year && <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", display: "flex", alignItems: "center", gap: 3 }}><Calendar size={11} />{year}</span>}
              {runtime && <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", display: "flex", alignItems: "center", gap: 3 }}><Clock size={11} />{runtime}</span>}
            </div>
          </div>
        </div>

        {/* Watch button */}
        {movie.has_file && !playing && (
          <button onClick={() => setPlaying(true)} style={{
            width: "100%", marginTop: 16,
            background: "linear-gradient(135deg, #8b5cf6, #7c3aed)",
            color: "#fff", padding: "13px 24px", borderRadius: 14,
            fontWeight: 700, fontSize: 15,
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            boxShadow: "0 4px 20px rgba(139,92,246,0.45)",
          }}>
            <Play size={18} fill="#fff" /> مشاهدة الفيلم
          </button>
        )}
        {!movie.has_file && (
          <div style={{
            width: "100%", marginTop: 16, background: "rgba(255,255,255,0.05)",
            padding: "12px 24px", borderRadius: 14, textAlign: "center",
            color: "rgba(255,255,255,0.35)", fontSize: 13, border: "1px dashed rgba(255,255,255,0.1)",
          }}>⏳ قريباً — الفيلم غير متاح بعد</div>
        )}

        {/* Genres */}
        {genres.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 14 }}>
            {genres.map((g: any) => (
              <span key={g} style={{
                padding: "4px 12px", borderRadius: 20, fontSize: 11,
                background: "rgba(139,92,246,0.15)", border: "1px solid rgba(139,92,246,0.35)",
                color: "#c4b5fd",
              }}>{typeof g === "string" ? g : g.name}</span>
            ))}
          </div>
        )}

        {/* Overview */}
        {overview && (
          <div style={{ marginTop: 18 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: "#c4b5fd" }}>القصة</h3>
            <p style={{ fontSize: 13, lineHeight: 1.7, color: "rgba(255,255,255,0.7)" }}>{overview}</p>
          </div>
        )}

        {/* Director */}
        {movie.director && (
          <div style={{ marginTop: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4, color: "#c4b5fd" }}>المخرج</h3>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.65)" }}>{movie.director}</p>
          </div>
        )}

        {/* Cast */}
        {cast.length > 0 && (
          <div style={{ marginTop: 18 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: "#c4b5fd" }}>طاقم العمل</h3>
            <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 4, scrollbarWidth: "none" } as any}>
              {cast.slice(0, 10).map((c: any) => (
                <div key={c.name} style={{ flexShrink: 0, textAlign: "center", width: 64 }}>
                  <div style={{ width: 64, height: 64, borderRadius: "50%", overflow: "hidden", background: "#1a1a2e", marginBottom: 4 }}>
                    {c.profile
                      ? <img src={c.profile} alt={c.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                      : <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>👤</div>}
                  </div>
                  <p style={{ fontSize: 10, lineHeight: 1.2, color: "rgba(255,255,255,0.7)", overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any }}>{c.name}</p>
                  {c.character && <p style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", marginTop: 1, overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{c.character}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
