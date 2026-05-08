import { useState, useEffect, useCallback } from "react";
import { api, type Movie, type Series } from "../api";
import ContentCard from "../components/ContentCard";
import { ArrowRight, SlidersHorizontal, X } from "lucide-react";

interface Props {
  type?: "movies" | "series";
  genre?: string;
  navigate: (r: any) => void;
  goBack: () => void;
}

export default function BrowsePage({ type: initType = "movies", genre: initGenre, navigate, goBack }: Props) {
  const [contentType, setContentType] = useState<"movies" | "series">(initType);
  const [items, setItems] = useState<(Movie | Series)[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [genres, setGenres] = useState<string[]>([]);
  const [activeGenre, setActiveGenre] = useState<string | null>(initGenre || null);
  const [sort, setSort] = useState<"newest" | "rating">("newest");
  const [showFilters, setShowFilters] = useState(false);
  const LIMIT = 24;

  useEffect(() => { api.genres().then(g => setGenres(g.genres)); }, []);

  const load = useCallback((reset = false) => {
    const off = reset ? 0 : offset;
    setLoading(true);
    const params = { limit: LIMIT, offset: off, genre: activeGenre || undefined, sort };
    const fn = contentType === "movies" ? api.movies(params) : api.series(params);
    fn.then(r => {
      setItems(prev => reset ? r.items : [...prev, ...r.items]);
      setTotal(r.total);
      setOffset(off + LIMIT);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [contentType, activeGenre, sort, offset]);

  useEffect(() => { setItems([]); setOffset(0); setTotal(0); load(true); }, [contentType, activeGenre, sort]);

  const hasMore = items.length < total;

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      {/* Header */}
      <div style={{
        position: "sticky", top: 0, zIndex: 50,
        background: "rgba(13,13,13,0.95)", backdropFilter: "blur(14px)",
        padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button onClick={goBack} style={{ color: "rgba(255,255,255,0.6)" }}><ArrowRight size={20} /></button>
            <h1 style={{ fontSize: 17, fontWeight: 800 }}>
              {contentType === "movies" ? "🎬 الأفلام" : "📺 المسلسلات"}
            </h1>
          </div>
          <button onClick={() => setShowFilters(!showFilters)} style={{
            display: "flex", alignItems: "center", gap: 5, padding: "6px 12px", borderRadius: 10,
            background: showFilters ? "rgba(139,92,246,0.2)" : "rgba(255,255,255,0.07)",
            border: showFilters ? "1px solid rgba(139,92,246,0.4)" : "1px solid rgba(255,255,255,0.1)",
            color: showFilters ? "#c4b5fd" : "rgba(255,255,255,0.6)", fontSize: 12,
          }}>
            <SlidersHorizontal size={14} /> فلترة
          </button>
        </div>

        {/* Type toggle */}
        <div style={{ display: "flex", gap: 6, background: "rgba(255,255,255,0.05)", padding: 4, borderRadius: 12 }}>
          {(["movies", "series"] as const).map(t => (
            <button key={t} onClick={() => setContentType(t)} style={{
              flex: 1, padding: "7px 0", borderRadius: 9, fontSize: 13, fontWeight: 600,
              background: contentType === t ? "#8b5cf6" : "transparent",
              color: contentType === t ? "#fff" : "rgba(255,255,255,0.45)",
              transition: "all 0.2s",
            }}>
              {t === "movies" ? "🎬 أفلام" : "📺 مسلسلات"}
            </button>
          ))}
        </div>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div style={{
          background: "rgba(26,26,46,0.95)", padding: "14px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}>
          {/* Sort */}
          <div style={{ marginBottom: 14 }}>
            <p style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", marginBottom: 8 }}>الترتيب</p>
            <div style={{ display: "flex", gap: 8 }}>
              {[{ v: "newest", l: "الأحدث" }, { v: "rating", l: "الأعلى تقييماً" }].map(({ v, l }) => (
                <button key={v} onClick={() => setSort(v as any)} style={{
                  padding: "5px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600,
                  background: sort === v ? "#8b5cf6" : "rgba(255,255,255,0.07)",
                  color: sort === v ? "#fff" : "rgba(255,255,255,0.5)",
                  border: sort === v ? "none" : "1px solid rgba(255,255,255,0.1)",
                }}>{l}</button>
              ))}
            </div>
          </div>

          {/* Genres */}
          {genres.length > 0 && (
            <div>
              <p style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", marginBottom: 8 }}>التصنيف</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                <button onClick={() => setActiveGenre(null)} style={{
                  padding: "4px 12px", borderRadius: 20, fontSize: 11, fontWeight: 600,
                  background: !activeGenre ? "#8b5cf6" : "rgba(255,255,255,0.07)",
                  color: !activeGenre ? "#fff" : "rgba(255,255,255,0.5)",
                  border: !activeGenre ? "none" : "1px solid rgba(255,255,255,0.1)",
                }}>الكل</button>
                {genres.map(g => (
                  <button key={g} onClick={() => setActiveGenre(g === activeGenre ? null : g)} style={{
                    padding: "4px 12px", borderRadius: 20, fontSize: 11, fontWeight: 600,
                    background: activeGenre === g ? "#8b5cf6" : "rgba(255,255,255,0.07)",
                    color: activeGenre === g ? "#fff" : "rgba(255,255,255,0.5)",
                    border: activeGenre === g ? "none" : "1px solid rgba(255,255,255,0.1)",
                    transition: "all 0.2s",
                  }}>{g}</button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Active filters indicator */}
      {(activeGenre || sort !== "newest") && (
        <div style={{ padding: "8px 16px", display: "flex", gap: 6, flexWrap: "wrap" }}>
          {activeGenre && (
            <div style={{
              display: "flex", alignItems: "center", gap: 4,
              background: "rgba(139,92,246,0.2)", border: "1px solid rgba(139,92,246,0.4)",
              borderRadius: 20, padding: "3px 10px", fontSize: 11, color: "#c4b5fd",
            }}>
              {activeGenre}
              <button onClick={() => setActiveGenre(null)} style={{ color: "#c4b5fd" }}><X size={11} /></button>
            </div>
          )}
        </div>
      )}

      {/* Grid */}
      <div style={{ padding: "12px 16px 80px" }}>
        {loading && items.length === 0 ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "60px 0", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <div style={{ width: 32, height: 32, border: "3px solid rgba(255,255,255,0.1)", borderTopColor: "#8b5cf6", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
            <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          </div>
        ) : (
          <>
            {items.length > 0 && (
              <p style={{ fontSize: 12, color: "rgba(255,255,255,0.35)", marginBottom: 12 }}>
                {items.length} من {total} {contentType === "movies" ? "فيلم" : "مسلسل"}
              </p>
            )}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              {items.map((item: any) => (
                <ContentCard
                  key={item.id}
                  id={item.id}
                  type={contentType === "movies" ? "movie" : "series"}
                  title={item.title}
                  title_ar={item.title_ar}
                  poster_path={item.poster_path}
                  rating={item.rating}
                  has_file={item.has_file ?? (item.file_id != null)}
                  year={item.release_date || item.first_air_date}
                  onClick={() => navigate({ page: contentType === "movies" ? "movie" : "series", id: item.id })}
                />
              ))}
            </div>

            {items.length === 0 && !loading && (
              <div style={{ textAlign: "center", padding: "60px 20px", color: "rgba(255,255,255,0.35)" }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>📭</div>
                <p>لا يوجد محتوى متاح بعد</p>
              </div>
            )}

            {hasMore && !loading && (
              <button onClick={() => load()} style={{
                width: "100%", marginTop: 20, padding: "12px 0",
                background: "rgba(139,92,246,0.15)", border: "1px solid rgba(139,92,246,0.3)",
                borderRadius: 12, color: "#c4b5fd", fontSize: 13, fontWeight: 600,
              }}>
                تحميل المزيد ({total - items.length} متبقي)
              </button>
            )}

            {loading && items.length > 0 && (
              <div style={{ display: "flex", justifyContent: "center", padding: "20px 0" }}>
                <div style={{ width: 24, height: 24, border: "2.5px solid rgba(255,255,255,0.1)", borderTopColor: "#8b5cf6", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
