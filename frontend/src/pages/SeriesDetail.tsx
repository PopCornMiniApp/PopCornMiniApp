import { useState, useEffect } from "react";
import { api, type Series, type Episode } from "../api";
import VideoPlayer from "../components/VideoPlayer";
import { ArrowRight, Star, Play, Calendar, Users, Tv, ThumbsUp } from "lucide-react";

interface Props { id: string; navigate: (r: any) => void; goBack: () => void; }

export default function SeriesDetail({ id, navigate, goBack }: Props) {
  const [series, setSeries] = useState<Series | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeSeason, setActiveSeason] = useState<number>(1);
  const [playingEp, setPlayingEp] = useState<Episode | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setLoading(true); setError(""); setPlayingEp(null); setExpanded(false);
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
      {/* Back button */}
      {!playingEp && (
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

      <div style={{ position: "relative" }}>
        {series.backdrop_path && !playingEp && (
          <div style={{ position: "relative", height: "60vw", maxHeight: 300, overflow: "hidden" }}>
            <img src={series.backdrop_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} loading="lazy" />
            <div style={{ position: "absolute", inset: 0,
              background: "linear-gradient(to bottom, rgba(13,13,13,0.15) 0%, rgba(13,13,13,0.6) 60%, #0d0d0d 100%)" }} />
          </div>
        )}
        {playingEp?.stream_url && (
          <VideoPlayer
            streamUrl={playingEp.stream_url}
            title={`${title} — م${playingEp.season_number} ح${playingEp.episode_number}`}
            fileSize={playingEp.file_size}
            onClose={() => setPlayingEp(null)}
          />
        )}
      </div>

      <div style={{ padding: "0 16px 80px" }}>
        <div style={{ display: "flex", gap: 14, marginTop: playingEp ? 16 : -50, position: "relative" }}>
          {series.poster_path && !playingEp && (
            <div style={{ flexShrink: 0, width: 95, height: 142, borderRadius: 12, overflow: "hidden",
              boxShadow: "0 8px 28px rgba(0,0,0,0.7)", border: "2px solid rgba(255,255,255,0.1)" }}>
              <img src={series.poster_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} loading="lazy" />
            </div>
          )}
          <div style={{ flex: 1, paddingTop: playingEp ? 0 : 52 }}>
            <h1 style={{ fontSize: 19, fontWeight: 800, lineHeight: 1.3, marginBottom: 4 }}>{title}</h1>
            {series.title !== series.title_ar && series.title_ar && (
              <p style={{ fontSize: 11, color: "rgba(255,255,255,0.38)", marginBottom: 6 }}>{series.title}</p>
            )}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              {series.rating > 0 && (
                <span style={{ display: "flex", alignItems: "center", gap: 3, color: "#f59e0b", fontSize: 14, fontWeight: 700 }}>
                  <Star size={13} fill="#f59e0b" />{series.rating.toFixed(1)}
                </span>
              )}
              {series.vote_count > 0 && (
                <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 11, color: "rgba(255,255,255,0.4)" }}>
                  <ThumbsUp size={10} />{series.vote_count.toLocaleString()}
                </span>
              )}
              {series.first_air_date && (
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", display: "flex", alignItems: "center", gap: 3 }}>
                  <Calendar size={10} />{series.first_air_date.slice(0, 4)}
                </span>
              )}
              {(series.total_seasons_available ?? 0) > 0 && (
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", display: "flex", alignItems: "center", gap: 3 }}>
                  <Tv size={10} />{series.total_seasons_available} موسم
                </span>
              )}
            </div>
          </div>
        </div>

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
                    color: "#fde68a",
                  }}>{label}</button>
              );
            })}
          </div>
        )}

        {/* Overview */}
        {overview && (
          <div style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: "#f59e0b" }}>القصة</h3>
            <div>
              <p style={{
                fontSize: 13, lineHeight: 1.8, color: "rgba(255,255,255,0.72)",
                overflow: expanded ? "visible" : "hidden",
                display: expanded ? "block" : "-webkit-box",
                WebkitLineClamp: expanded ? undefined : 4,
                WebkitBoxOrient: "vertical" as any,
              }}>{overview}</p>
              {!expanded && overview.length > 200 && (
                <button onClick={() => setExpanded(true)} style={{ color: "#f59e0b", fontSize: 12, marginTop: 4, display: "block" }}>
                  اقرأ المزيد...
                </button>
              )}
            </div>
          </div>
        )}

        {/* Info row */}
        {(series.creator || series.status || series.total_seasons) && (
          <div style={{ marginTop: 18, background: "rgba(255,255,255,0.03)", borderRadius: 14, padding: "14px 16px",
            border: "1px solid rgba(255,255,255,0.07)", display: "flex", flexDirection: "column", gap: 10 }}>
            {series.creator && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>المنشئ</span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{series.creator}</span>
              </div>
            )}
            {series.status && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>الحالة</span>
                <span style={{ fontSize: 13 }}>{series.status}</span>
              </div>
            )}
            {series.total_seasons > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>إجمالي المواسم</span>
                <span style={{ fontSize: 13 }}>{series.total_seasons}</span>
              </div>
            )}
            {series.vote_count > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>عدد التقييمات</span>
                <span style={{ fontSize: 13 }}>{series.vote_count.toLocaleString()}</span>
              </div>
            )}
          </div>
        )}

        {/* Season tabs + episodes */}
        {seasonNums.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "#f59e0b" }}>الحلقات</h3>
            <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 8, scrollbarWidth: "none" } as any}>
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

            <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 10 }}>
              {currentEps.length === 0 ? (
                <div style={{ textAlign: "center", padding: "30px 0", color: "rgba(255,255,255,0.3)", fontSize: 13 }}>
                  لا توجد حلقات لهذا الموسم بعد
                </div>
              ) : currentEps.map(ep => (
                <div key={ep.id} style={{
                  display: "flex", gap: 10, alignItems: "center",
                  background: ep.has_file ? "rgba(245,158,11,0.06)" : "rgba(255,255,255,0.03)",
                  borderRadius: 12, padding: "10px 12px",
                  border: `1px solid ${ep.has_file ? "rgba(245,158,11,0.25)" : "rgba(255,255,255,0.06)"}`,
                }}>
                  {ep.still_path && (
                    <div style={{ flexShrink: 0, width: 82, height: 52, borderRadius: 8, overflow: "hidden" }}>
                      <img src={ep.still_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} loading="lazy" />
                    </div>
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 12, fontWeight: 700, marginBottom: 3, overflow: "hidden",
                      whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
                      {ep.episode_number}. {ep.title || `الحلقة ${ep.episode_number}`}
                    </p>
                    <div style={{ display: "flex", gap: 8 }}>
                      {ep.runtime ? <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{ep.runtime} د</span> : null}
                      {ep.air_date ? <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>{ep.air_date?.slice(0,10)}</span> : null}
                    </div>
                  </div>
                  {ep.has_file ? (
                    <button onClick={() => setPlayingEp(ep)} style={{
                      flexShrink: 0, background: "#f59e0b", borderRadius: "50%",
                      width: 36, height: 36, display: "flex", alignItems: "center", justifyContent: "center",
                      boxShadow: "0 2px 10px rgba(245,158,11,0.4)",
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
