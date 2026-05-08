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
      <div style={{ width: 36, height: 36, border: "3px solid rgba(255,255,255,0.1)", borderTopColor: "#f59e0b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  if (error || !series) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "80vh", gap: 16, padding: 20 }}>
      <span style={{ fontSize: 40 }}>😕</span>
      <p style={{ color: "rgba(255,255,255,0.6)", textAlign: "center" }}>{error || "المسلسل غير موجود"}</p>
      <button onClick={goBack} style={{ background: "#f59e0b", color: "#000", padding: "8px 24px", borderRadius: 20, fontWeight: 700 }}>رجوع</button>
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
      <div style={{ position: "relative" }}>
        {series.backdrop_path && !playingEp && (
          <div style={{ position: "relative", height: "55vw", maxHeight: 280, overflow: "hidden" }}>
            <img src={series.backdrop_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to bottom, rgba(13,13,13,0.2) 0%, rgba(13,13,13,0.7) 70%, #0d0d0d 100%)" }} />
          </div>
        )}
        {playingEp?.stream_url && (
          <VideoPlayer
            streamUrl={playingEp.stream_url}
            title={`${title} — الموسم ${playingEp.season_number} الحلقة ${playingEp.episode_number}`}
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

      <div style={{ padding: "0 16px 80px" }}>
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
              {(series.total_seasons_available ?? 0) > 0 && (
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)" }}>
                  {series.total_seasons_available} موسم
                </span>
              )}
            </div>
          </div>
        </div>

        {genres.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 14 }}>
            {genres.map((g: any) => (
              <span key={g} style={{ padding: "4px 12px", borderRadius: 20, fontSize: 11,
                background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)", color: "#fde68a" }}>
                {typeof g === "string" ? g : g.name}
              </span>
            ))}
          </div>
        )}

        {overview && (
          <div style={{ marginTop: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: "#f59e0b" }}>القصة</h3>
            <p style={{ fontSize: 13, lineHeight: 1.7, color: "rgba(255,255,255,0.7)" }}>{overview}</p>
          </div>
        )}

        {/* Season tabs */}
        {seasonNums.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 4, scrollbarWidth: "none" } as any}>
              {seasonNums.map(n => (
                <button key={n} onClick={() => setActiveSeason(n)} style={{
                  flexShrink: 0, padding: "7px 18px", borderRadius: 20, fontSize: 12, fontWeight: 700,
                  background: activeSeason === n ? "#f59e0b" : "rgba(255,255,255,0.07)",
                  color: activeSeason === n ? "#000" : "rgba(255,255,255,0.55)",
                  border: activeSeason === n ? "1px solid #f59e0b" : "1px solid rgba(255,255,255,0.1)",
                  transition: "all 0.18s",
                }}>الموسم {n}</button>
              ))}
            </div>

            {/* Episode list */}
            <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
              {currentEps.length === 0 ? (
                <div style={{ textAlign: "center", padding: "30px 0", color: "rgba(255,255,255,0.3)", fontSize: 13 }}>
                  لا توجد حلقات لهذا الموسم بعد
                </div>
              ) : currentEps.map(ep => (
                <div key={ep.id} style={{
                  display: "flex", gap: 10, alignItems: "center",
                  background: "rgba(255,255,255,0.04)", borderRadius: 12,
                  padding: "10px 12px",
                  border: `1px solid ${ep.has_file ? "rgba(245,158,11,0.2)" : "rgba(255,255,255,0.06)"}`,
                }}>
                  {ep.still_path && (
                    <div style={{ flexShrink: 0, width: 80, height: 50, borderRadius: 8, overflow: "hidden" }}>
                      <img src={ep.still_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    </div>
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 12, fontWeight: 700, marginBottom: 2, overflow: "hidden",
                      whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
                      {ep.episode_number}. {ep.title || `الحلقة ${ep.episode_number}`}
                    </p>
                    {ep.runtime ? (
                      <p style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{ep.runtime} دقيقة</p>
                    ) : null}
                  </div>
                  {ep.has_file ? (
                    <button onClick={() => setPlayingEp(ep)} style={{
                      flexShrink: 0, background: "#f59e0b", borderRadius: "50%",
                      width: 34, height: 34, display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <Play size={14} fill="#000" color="#000" />
                    </button>
                  ) : (
                    <span style={{ flexShrink: 0, fontSize: 9, color: "rgba(255,255,255,0.3)",
                      background: "rgba(255,255,255,0.06)", padding: "3px 8px", borderRadius: 6 }}>قريباً</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {seasonNums.length === 0 && (
          <div style={{ marginTop: 20, textAlign: "center", padding: "40px 20px",
            color: "rgba(255,255,255,0.3)", border: "1px dashed rgba(255,255,255,0.08)", borderRadius: 14 }}>
            <div style={{ fontSize: 36, marginBottom: 10 }}>⏳</div>
            <p style={{ fontSize: 13 }}>الحلقات ستكون متاحة قريباً</p>
          </div>
        )}

        {/* Cast */}
        {cast.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: "#f59e0b" }}>طاقم العمل</h3>
            <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 4 }}>
              {cast.slice(0, 10).map((actor: any, i: number) => {
                const name = typeof actor === "string" ? actor : (actor.name || "");
                const char = typeof actor === "object" ? (actor.character || "") : "";
                const photo = typeof actor === "object" ? actor.profile_path : null;
                return (
                  <div key={i} style={{ flexShrink: 0, textAlign: "center", width: 60 }}>
                    <div style={{ width: 52, height: 52, borderRadius: "50%", overflow: "hidden",
                      background: "#1a1a2e", margin: "0 auto 4px", border: "2px solid rgba(245,158,11,0.3)" }}>
                      {photo
                        ? <img src={photo} alt={name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                        : <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>👤</div>
                      }
                    </div>
                    <p style={{ fontSize: 9, color: "rgba(255,255,255,0.7)", lineHeight: 1.3, overflow: "hidden",
                      display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any }}>{name}</p>
                    {char && <p style={{ fontSize: 8, color: "rgba(255,255,255,0.35)", marginTop: 1 }}>{char}</p>}
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
