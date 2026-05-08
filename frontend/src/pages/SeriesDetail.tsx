import { useState, useEffect } from "react";
import { api, type Series, type Episode } from "../api";
import VideoPlayer from "../components/VideoPlayer";
import { ArrowRight, Star, Play, Calendar } from "lucide-react";

interface Props { id: string; navigate: (r: any) => void; goBack: () => void; }

export default function SeriesDetail({ id, navigate, goBack }: Props) {
  const [series, setSeries] = useState<Series | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeSeason, setActiveSeason] = useState<number>(1);
  const [playingEp, setPlayingEp] = useState<Episode | null>(null);

  useEffect(() => {
    setLoading(true); setError(""); setPlayingEp(null);
    api.seriesDetail(id)
      .then(s => { setSeries(s); setActiveSeason(1); setLoading(false); })
      .catch(() => { setError("تعذّر تحميل تفاصيل المسلسل"); setLoading(false); });
  }, [id]);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", flexDirection: "column", gap: 12 }}>
      <div style={{ width: 36, height: 36, border: "3px solid rgba(255,255,255,0.1)", borderTopColor: "#8b5cf6", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  if (error || !series) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "80vh", gap: 16, padding: 20 }}>
      <span style={{ fontSize: 40 }}>😕</span>
      <p style={{ color: "rgba(255,255,255,0.6)", textAlign: "center" }}>{error || "المسلسل غير موجود"}</p>
      <button onClick={goBack} style={{ background: "#8b5cf6", color: "#fff", padding: "8px 24px", borderRadius: 20, fontWeight: 700 }}>رجوع</button>
    </div>
  );

  const title = series.title_ar || series.title;
  const overview = series.overview_ar || series.overview;
  const genres = Array.isArray(series.genres) ? series.genres : [];
  const cast = Array.isArray(series.cast) ? series.cast : [];
  const seasons = series.seasons || {};
  const seasonNums = Object.keys(seasons).map(Number).sort((a, b) => a - b);
  const currentEps: Episode[] = seasons[String(activeSeason)] || [];

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      {/* Backdrop */}
      <div style={{ position: "relative" }}>
        {series.backdrop_path && !playingEp && (
          <div style={{ position: "relative", height: "55vw", maxHeight: 280, overflow: "hidden" }}>
            <img src={series.backdrop_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            <div style={{
              position: "absolute", inset: 0,
              background: "linear-gradient(to bottom, rgba(13,13,13,0.2) 0%, rgba(13,13,13,0.7) 70%, #0d0d0d 100%)",
            }} />
          </div>
        )}
        {playingEp?.stream_url && (
          <VideoPlayer
            streamUrl={playingEp.stream_url}
            title={`${title} — الموسم ${playingEp.season_number} الحلقة ${playingEp.episode_number}${playingEp.title ? ` — ${playingEp.title}` : ""}`}
            fileSize={playingEp.file_size}
            onClose={() => setPlayingEp(null)}
          />
        )}
        <button onClick={goBack} style={{
          position: "absolute", top: 12, right: 12, zIndex: 30,
          background: "rgba(0,0,0,0.55)", borderRadius: "50%", padding: 8, backdropFilter: "blur(4px)",
        }}>
          <ArrowRight size={18} />
        </button>
      </div>

      <div style={{ padding: "0 16px 100px" }}>
        {/* Header info */}
        <div style={{ display: "flex", gap: 14, marginTop: playingEp ? 16 : -40, position: "relative" }}>
          {series.poster_path && !playingEp && (
            <div style={{ flexShrink: 0, width: 90, height: 135, borderRadius: 10, overflow: "hidden",
              boxShadow: "0 8px 24px rgba(0,0,0,0.6)", border: "2px solid rgba(255,255,255,0.1)" }}>
              <img src={series.poster_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            </div>
          )}
          <div style={{ flex: 1, paddingTop: playingEp ? 0 : 45 }}>
            <h1 style={{ fontSize: 18, fontWeight: 800, lineHeight: 1.3, marginBottom: 6 }}>{title}</h1>
            {series.title !== series.title_ar && series.title_ar && (
              <p style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", marginBottom: 6 }}>{series.title}</p>
            )}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              {series.rating > 0 && (
                <span style={{ display: "flex", alignItems: "center", gap: 3, color: "#f59e0b", fontSize: 13, fontWeight: 700 }}>
                  <Star size={12} fill="#f59e0b" />{series.rating.toFixed(1)}
                </span>
              )}
              {series.first_air_date && (
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", display: "flex", alignItems: "center", gap: 3 }}>
                  <Calendar size={11} />{series.first_air_date.slice(0, 4)}
                </span>
              )}
              {seasonNums.length > 0 && (
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>{seasonNums.length} موسم</span>
              )}
              {series.status && (
                <span style={{
                  fontSize: 10, padding: "2px 8px", borderRadius: 10,
                  background: series.status === "Ended" ? "rgba(239,68,68,0.2)" : "rgba(16,185,129,0.2)",
                  color: series.status === "Ended" ? "#fca5a5" : "#6ee7b7",
                  border: `1px solid ${series.status === "Ended" ? "rgba(239,68,68,0.3)" : "rgba(16,185,129,0.3)"}`,
                }}>{series.status === "Ended" ? "منتهي" : "مستمر"}</span>
              )}
            </div>
          </div>
        </div>

        {/* Genres */}
        {genres.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 14 }}>
            {genres.map((g: any) => (
              <span key={typeof g === "string" ? g : g.name} style={{
                padding: "4px 12px", borderRadius: 20, fontSize: 11,
                background: "rgba(139,92,246,0.15)", border: "1px solid rgba(139,92,246,0.35)", color: "#c4b5fd",
              }}>{typeof g === "string" ? g : g.name}</span>
            ))}
          </div>
        )}

        {/* Overview */}
        {overview && (
          <div style={{ marginTop: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: "#c4b5fd" }}>القصة</h3>
            <p style={{ fontSize: 13, lineHeight: 1.7, color: "rgba(255,255,255,0.7)" }}>{overview}</p>
          </div>
        )}

        {/* Season selector — tabs for ≤5, dropdown for >5 */}
        {seasonNums.length > 0 && (
          <div style={{ marginTop: 22 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>الحلقات</h3>
              {/* Dropdown for more than 5 seasons */}
              {seasonNums.length > 5 && (
                <select
                  value={activeSeason}
                  onChange={e => setActiveSeason(Number(e.target.value))}
                  style={{
                    background: "rgba(255,255,255,0.08)", color: "#fff", border: "1px solid rgba(255,255,255,0.15)",
                    borderRadius: 8, padding: "5px 10px", fontSize: 12, outline: "none",
                  }}
                >
                  {seasonNums.map(n => (
                    <option key={n} value={n} style={{ background: "#1a1a1a" }}>
                      الموسم {n} ({(seasons[String(n)] || []).length} حلقة)
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Tab buttons for ≤5 seasons */}
            {seasonNums.length <= 5 && (
              <div style={{ display: "flex", gap: 8, marginBottom: 14, overflowX: "auto", scrollbarWidth: "none" } as any}>
                {seasonNums.map(n => (
                  <button key={n} onClick={() => setActiveSeason(n)} style={{
                    flexShrink: 0, padding: "6px 16px", borderRadius: 20, fontSize: 12, fontWeight: 600,
                    background: activeSeason === n ? "#8b5cf6" : "rgba(255,255,255,0.07)",
                    color: activeSeason === n ? "#fff" : "rgba(255,255,255,0.5)",
                    border: activeSeason === n ? "1px solid #8b5cf6" : "1px solid rgba(255,255,255,0.1)",
                    transition: "all 0.2s",
                  }}>
                    الموسم {n}
                    <span style={{ marginRight: 4, opacity: 0.6, fontSize: 10 }}>
                      ({(seasons[String(n)] || []).length})
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* Episodes list */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {currentEps.length === 0 && (
                <div style={{ textAlign: "center", padding: "30px 20px", color: "rgba(255,255,255,0.35)", fontSize: 13 }}>
                  لا توجد حلقات متاحة لهذا الموسم بعد
                </div>
              )}
              {currentEps.map((ep) => (
                <div key={ep.id} onClick={() => ep.has_file && setPlayingEp(ep)} style={{
                  display: "flex", gap: 12, alignItems: "center",
                  background: playingEp?.id === ep.id ? "rgba(139,92,246,0.15)" : "rgba(255,255,255,0.04)",
                  border: playingEp?.id === ep.id ? "1px solid rgba(139,92,246,0.4)" : "1px solid rgba(255,255,255,0.06)",
                  borderRadius: 12, padding: "10px 12px",
                  cursor: ep.has_file ? "pointer" : "default",
                  transition: "background 0.2s",
                }}>
                  {/* Episode thumbnail or number */}
                  <div style={{
                    flexShrink: 0, width: 60, height: 40, borderRadius: 8, overflow: "hidden",
                    background: "#1a1a2e", position: "relative",
                  }}>
                    {ep.still_path
                      ? <img src={ep.still_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                      : <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center",
                          justifyContent: "center", fontSize: 18, color: "rgba(255,255,255,0.2)" }}>
                          {ep.episode_number}
                        </div>
                    }
                    {ep.has_file && (
                      <div style={{
                        position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                        background: "rgba(0,0,0,0.45)",
                      }}>
                        <Play size={14} fill="#fff" color="#fff" />
                      </div>
                    )}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>
                      {ep.episode_number}. {ep.title || `الحلقة ${ep.episode_number}`}
                    </p>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      {ep.runtime > 0 && <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{ep.runtime} د</span>}
                      {ep.air_date && <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>{ep.air_date.slice(0, 10)}</span>}
                    </div>
                  </div>

                  {!ep.has_file && (
                    <span style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", flexShrink: 0 }}>قريباً</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cast */}
        {cast.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: "#c4b5fd" }}>طاقم العمل</h3>
            <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 4, scrollbarWidth: "none" } as any}>
              {cast.slice(0, 10).map((c: any) => (
                <div key={c.name} style={{ flexShrink: 0, textAlign: "center", width: 64 }}>
                  <div style={{ width: 64, height: 64, borderRadius: "50%", overflow: "hidden", background: "#1a1a2e", marginBottom: 4 }}>
                    {c.profile
                      ? <img src={c.profile} alt={c.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                      : <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>👤</div>}
                  </div>
                  <p style={{ fontSize: 10, lineHeight: 1.2, color: "rgba(255,255,255,0.7)", overflow: "hidden",
                    display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any }}>{c.name}</p>
                  {c.character && <p style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", marginTop: 1,
                    overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{c.character}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
