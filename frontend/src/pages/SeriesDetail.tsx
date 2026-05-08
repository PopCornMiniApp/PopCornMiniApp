import { useState, useEffect } from "react";
import { api, type Series } from "../api";
import VideoPlayer from "../components/VideoPlayer";
import { ArrowRight, Star, Clock, Play, Calendar, Users, Tv2, ThumbsUp } from "lucide-react";

interface Props { id: string; navigate: (r: any) => void; goBack: () => void; }

export default function SeriesDetail({ id, navigate, goBack }: Props) {
  const [series, setSeries] = useState<Series | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [playEp, setPlayEp] = useState<any>(null);
  const [expanded, setExpanded] = useState(false);
  const [activeSeason, setActiveSeason] = useState(1);

  useEffect(() => {
    setLoading(true); setError(""); setPlayEp(null); setExpanded(false);
    api.seriesDetail(id)
      .then(s => { setSeries(s); setLoading(false); })
      .catch(() => { setError("تعذّر تحميل المسلسل"); setLoading(false); });
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
  const year = series.first_air_date?.slice(0, 4) || "";
  const genres = Array.isArray(series.genres) ? series.genres : [];
  const cast = Array.isArray(series.cast) ? series.cast : [];
  const seasons: Record<string, any[]> = (series as any).seasons || {};
  const seasonNumbers = Object.keys(seasons).map(Number).sort((a, b) => a - b);
  const currentEps: any[] = seasons[String(activeSeason)] || [];

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      {/* Back button — fixed, uses only phone safe area (not Telegram header) */}
      {!playEp && (
        <button onClick={goBack} style={{
          position: "fixed",
          top: "calc(var(--tg-safe-top, env(safe-area-inset-top, 0px)) + 8px)",
          right: 12, zIndex: 100,
          background: "rgba(0,0,0,0.60)", borderRadius: "50%", padding: 8,
          backdropFilter: "blur(8px)", border: "1px solid rgba(255,255,255,0.12)",
        }}>
          <ArrowRight size={19} />
        </button>
      )}

      {!playEp && series.backdrop_path && (
        <div style={{ position: "relative", height: "58vw", maxHeight: 290, overflow: "hidden" }}>
          <img src={series.backdrop_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} loading="lazy" />
          <div style={{ position: "absolute", inset: 0,
            background: "linear-gradient(to bottom, rgba(13,13,13,0.1) 0%, rgba(13,13,13,0.55) 60%, #0d0d0d 100%)" }} />
        </div>
      )}
      {playEp && (
        <VideoPlayer streamUrl={playEp.stream_url} title={`${title} — ${playEp.title || `الحلقة ${playEp.episode_number}`}`}
          fileSize={playEp.file_size} onClose={() => setPlayEp(null)} />
      )}

      <div style={{ padding: "0 16px 80px" }}>
        <div style={{ display: "flex", gap: 14, marginTop: playEp ? 16 : -46, position: "relative" }}>
          {!playEp && series.poster_path && (
            <div style={{ flexShrink: 0, width: 92, height: 138, borderRadius: 12, overflow: "hidden",
              boxShadow: "0 8px 28px rgba(0,0,0,0.7)", border: "2px solid rgba(255,255,255,0.1)" }}>
              <img src={series.poster_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} loading="lazy" />
            </div>
          )}
          <div style={{ flex: 1, paddingTop: playEp ? 0 : 48 }}>
            <h1 style={{ fontSize: 19, fontWeight: 800, lineHeight: 1.3, marginBottom: 4 }}>{title}</h1>
            {series.title !== series.title_ar && series.title_ar && (
              <p style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", marginBottom: 6 }}>{series.title}</p>
            )}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              {series.rating > 0 && (
                <span style={{ display: "flex", alignItems: "center", gap: 3, color: "#f59e0b", fontSize: 14, fontWeight: 700 }}>
                  <Star size={13} fill="#f59e0b" />{series.rating.toFixed(1)}
                </span>
              )}
              {(series as any).vote_count > 0 && (
                <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 11, color: "rgba(255,255,255,0.4)" }}>
                  <ThumbsUp size={10} />{(series as any).vote_count.toLocaleString()}
                </span>
              )}
              {year && <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", display: "flex", alignItems: "center", gap: 3 }}><Calendar size={10} />{year}</span>}
              {series.total_seasons > 0 && (
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", display: "flex", alignItems: "center", gap: 3 }}>
                  <Tv2 size={10} />{series.total_seasons} مواسم
                </span>
              )}
            </div>
          </div>
        </div>

        {genres.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 16 }}>
            {genres.map((g: any) => {
              const label = typeof g === "string" ? g : g.name;
              return (
                <button key={label} onClick={() => navigate({ page: "browse", genre: label })}
                  style={{ padding: "4px 12px", borderRadius: 20, fontSize: 11,
                    background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", color: "#fde68a" }}>
                  {label}
                </button>
              );
            })}
          </div>
        )}

        {overview && (
          <div style={{ marginTop: 18 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: "#f59e0b" }}>القصة</h3>
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
        )}

        {/* Seasons tabs */}
        {seasonNumbers.length > 1 && (
          <div style={{ display: "flex", gap: 8, overflowX: "auto", marginTop: 20, paddingBottom: 4, scrollbarWidth: "none" } as any}>
            {seasonNumbers.map(n => (
              <button key={n} onClick={() => setActiveSeason(n)} style={{
                flexShrink: 0, padding: "6px 16px", borderRadius: 20, fontSize: 12, fontWeight: 600,
                background: activeSeason === n ? "#f59e0b" : "rgba(255,255,255,0.07)",
                color: activeSeason === n ? "#000" : "rgba(255,255,255,0.55)",
                border: activeSeason === n ? "1px solid #f59e0b" : "1px solid rgba(255,255,255,0.1)",
                transition: "all 0.2s",
              }}>الموسم {n}</button>
            ))}
          </div>
        )}

        {/* Episodes list */}
        {currentEps.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: "#f59e0b", display: "flex", alignItems: "center", gap: 6 }}>
              <Tv2 size={14} />
              {seasonNumbers.length > 1 ? `الموسم ${activeSeason}` : "الحلقات"} — {currentEps.length} حلقة
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {currentEps.map((ep: any) => (
                <div key={ep.episode_number} style={{
                  display: "flex", alignItems: "center", gap: 10,
                  background: "rgba(255,255,255,0.04)", borderRadius: 12, padding: "10px 12px",
                  border: "1px solid rgba(255,255,255,0.07)",
                  cursor: ep.has_file ? "pointer" : "default",
                  opacity: ep.has_file ? 1 : 0.55,
                }} onClick={() => ep.has_file && setPlayEp(ep)}>
                  {ep.still_path ? (
                    <div style={{ flexShrink: 0, width: 68, height: 42, borderRadius: 8, overflow: "hidden" }}>
                      <img src={ep.still_path} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} loading="lazy" />
                    </div>
                  ) : (
                    <div style={{ flexShrink: 0, width: 68, height: 42, borderRadius: 8,
                      background: "rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Tv2 size={18} color="rgba(255,255,255,0.3)" />
                    </div>
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>
                      <span style={{ color: "#f59e0b", marginLeft: 4 }}>ح{ep.episode_number}</span>
                      {ep.title || `الحلقة ${ep.episode_number}`}
                    </p>
                    {ep.runtime > 0 && (
                      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.35)", display: "flex", alignItems: "center", gap: 2 }}>
                        <Clock size={9} />{ep.runtime}د
                      </span>
                    )}
                  </div>
                  {ep.has_file
                    ? <Play size={16} color="#f59e0b" />
                    : <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>قريباً</span>
                  }
                </div>
              ))}
            </div>
          </div>
        )}

        {seasonNumbers.length === 0 && (
          <div style={{ marginTop: 24, textAlign: "center", color: "rgba(255,255,255,0.3)", fontSize: 13 }}>
            ⏳ لم تُضف الحلقات بعد
          </div>
        )}

        {/* Info table */}
        <div style={{ marginTop: 18, background: "rgba(255,255,255,0.03)", borderRadius: 14, padding: "14px 16px",
          border: "1px solid rgba(255,255,255,0.07)", display: "flex", flexDirection: "column", gap: 10 }}>
          {(series as any).creator && (
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>المنشئ</span>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{(series as any).creator}</span>
            </div>
          )}
          {series.first_air_date && (
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>تاريخ الإصدار</span>
              <span style={{ fontSize: 13 }}>{series.first_air_date}</span>
            </div>
          )}
          {series.total_seasons > 0 && (
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>المواسم</span>
              <span style={{ fontSize: 13 }}>{series.total_seasons}</span>
            </div>
          )}
          {(series as any).status && (
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>الحالة</span>
              <span style={{ fontSize: 13 }}>{(series as any).status}</span>
            </div>
          )}
        </div>

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
                      border: "2px solid rgba(245,158,11,0.3)" }}>
                      {photo
                        ? <img src={photo} alt={name} style={{ width: "100%", height: "100%", objectFit: "cover" }} loading="lazy"
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
