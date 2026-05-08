import { useState, useEffect, useCallback, useRef } from "react";
import { api, type Movie, type Series } from "../api";
import ContentCard from "../components/ContentCard";
import { SlidersHorizontal, X, ChevronDown } from "lucide-react";

interface Props {
  type?: "movies" | "series";
  genre?: string;
  navigate: (r: any) => void;
  goBack: () => void;
}

const LIMIT = 24;

export default function BrowsePage({ type: initType = "movies", genre: initGenre, navigate }: Props) {
  const contentType = initType;
  const [items, setItems] = useState<(Movie | Series)[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [genres, setGenres] = useState<string[]>([]);
  const [activeGenre, setActiveGenre] = useState<string | null>(initGenre || null);
  const [sort, setSort] = useState<"newest" | "rating">("newest");
  const [showFilters, setShowFilters] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    api.genres().then(g => { if (mountedRef.current) setGenres(g.genres); });
  }, []);

  const load = useCallback((reset = false, overrideOffset?: number) => {
    const off = reset ? 0 : (overrideOffset ?? offset);
    setLoading(true);
    const params = { limit: LIMIT, offset: off, genre: activeGenre || undefined, sort };
    const fn = contentType === "movies" ? api.movies(params) : api.series(params);
    fn.then(r => {
      if (!mountedRef.current) return;
      setItems(prev => reset ? r.items : [...prev, ...r.items]);
      setTotal(r.total);
      setOffset(off + LIMIT);
      setLoading(false);
    }).catch(() => { if (mountedRef.current) setLoading(false); });
  }, [contentType, activeGenre, sort, offset]);

  useEffect(() => {
    setItems([]);
    setOffset(0);
    setTotal(0);
    load(true);
  }, [contentType, activeGenre, sort]);

  const hasMore = items.length < total;
  const isMovies = contentType === "movies";

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>

      {/* ── Sticky header ───────────────────────────────────── */}
      <div style={{
        position: "sticky", top: 0, zIndex: 50,
        background: "rgba(13,13,13,0.97)", backdropFilter: "blur(16px)",
        padding: "14px 16px 10px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h1 style={{ fontSize: 18, fontWeight: 800, letterSpacing: -0.3 }}>
            {isMovies ? "🎬 الأفلام" : "📺 المسلسلات"}
          </h1>
          <button
            onClick={() => setShowFilters(v => !v)}
            style={{
              display: "flex", alignItems: "center", gap: 5,
              padding: "6px 13px", borderRadius: 10,
              background: showFilters ? "rgba(139,92,246,0.22)" : "rgba(255,255,255,0.07)",
              border: showFilters ? "1px solid rgba(139,92,246,0.45)" : "1px solid rgba(255,255,255,0.1)",
              color: showFilters ? "#c4b5fd" : "rgba(255,255,255,0.6)", fontSize: 12, fontWeight: 600,
            }}
          >
            <SlidersHorizontal size={13} />
            فلترة
            {(activeGenre || sort !== "newest") && (
              <span style={{
                width: 6, height: 6, borderRadius: "50%",
                background: "#8b5cf6", display: "inline-block",
              }} />
            )}
          </button>
        </div>
      </div>

      {/* ── Filter panel ────────────────────────────────────── */}
      {showFilters && (
        <div style={{
          background: "rgba(20,18,38,0.98)", padding: "16px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          animation: "slideDown 0.2s ease",
        }}>
          <style>{`
            @keyframes slideDown { from { opacity:0; transform:translateY(-8px) } to { opacity:1; transform:translateY(0) } }
            @keyframes spin { to { transform:rotate(360deg) } }
          `}</style>

          {/* Sort */}
          <p style={{ fontSize: 11, color: "rgba(255,255,255,0.38)", marginBottom: 8, fontWeight: 600, letterSpacing: 0.5 }}>
            الترتيب
          </p>
          <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
            {[{ v: "newest", l: "الأحدث" }, { v: "rating", l: "الأعلى تقييماً" }].map(({ v, l }) => (
              <button key={v} onClick={() => setSort(v as any)} style={{
                padding: "6px 16px", borderRadius: 20, fontSize: 12, fontWeight: 700,
                background: sort === v ? "#8b5cf6" : "rgba(255,255,255,0.07)",
                color: sort === v ? "#fff" : "rgba(255,255,255,0.5)",
                border: sort === v ? "1px solid #8b5cf6" : "1px solid rgba(255,255,255,0.1)",
                transition: "all 0.18s",
              }}>{l}</button>
            ))}
          </div>

          {/* Genres */}
          {genres.length > 0 && (
            <>
              <p style={{ fontSize: 11, color: "rgba(255,255,255,0.38)", marginBottom: 8, fontWeight: 600, letterSpacing: 0.5 }}>
                التصنيف
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
                <button onClick={() => setActiveGenre(null)} style={{
                  padding: "5px 14px", borderRadius: 20, fontSize: 11, fontWeight: 700,
                  background: !activeGenre ? "#8b5cf6" : "rgba(255,255,255,0.07)",
                  color: !activeGenre ? "#fff" : "rgba(255,255,255,0.5)",
                  border: !activeGenre ? "1px solid #8b5cf6" : "1px solid rgba(255,255,255,0.1)",
                }}>الكل</button>
                {genres.map(g => (
                  <button key={g} onClick={() => setActiveGenre(g === activeGenre ? null : g)} style={{
                    padding: "5px 14px", borderRadius: 20, fontSize: 11, fontWeight: 700,
                    background: activeGenre === g ? "#8b5cf6" : "rgba(255,255,255,0.07)",
                    color: activeGenre === g ? "#fff" : "rgba(255,255,255,0.5)",
                    border: activeGenre === g ? "1px solid #8b5cf6" : "1px solid rgba(255,255,255,0.1)",
                    transition: "all 0.18s",
                  }}>{g}</button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Active filter chips ──────────────────────────────── */}
      {activeGenre && (
        <div style={{ padding: "8px 16px 0", display: "flex", gap: 6 }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 5,
            background: "rgba(139,92,246,0.18)", border: "1px solid rgba(139,92,246,0.4)",
            borderRadius: 20, padding: "4px 10px 4px 12px",
            fontSize: 11, color: "#c4b5fd", fontWeight: 600,
          }}>
            {activeGenre}
            <button onClick={() => setActiveGenre(null)} style={{ color: "#c4b5fd", display: "flex" }}>
              <X size={12} />
            </button>
          </div>
        </div>
      )}

      {/* ── Results count ────────────────────────────────────── */}
      {total > 0 && (
        <div style={{ padding: "10px 16px 0" }}>
          <p style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", fontWeight: 500 }}>
            {total} {isMovies ? "فيلم" : "مسلسل"}
            {activeGenre ? ` · ${activeGenre}` : ""}
          </p>
        </div>
      )}

      {/* ── Grid ─────────────────────────────────────────────── */}
      <div style={{ padding: "12px 16px 90px" }}>
        {loading && items.length === 0 ? (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: "80px 0", gap: 14 }}>
            <div style={{ width: 34, height: 34, border: "3px solid rgba(255,255,255,0.08)", borderTopColor: "#8b5cf6", borderRadius: "50%", animation: "spin 0.75s linear infinite" }} />
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.3)" }}>جارٍ التحميل…</span>
          </div>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
              {items.map((item: any) => (
                <ContentCard
                  key={item.id}
                  id={item.id}
                  type={isMovies ? "movie" : "series"}
                  title={item.title}
                  title_ar={item.title_ar}
                  poster_path={item.poster_path}
                  rating={item.rating}
                  has_file={item.has_file ?? (item.file_id != null)}
                  year={item.release_date || item.first_air_date}
                  onClick={() => navigate({ page: isMovies ? "movie" : "series", id: item.id })}
                />
              ))}
            </div>

            {items.length === 0 && !loading && (
              <div style={{ textAlign: "center", padding: "80px 20px", color: "rgba(255,255,255,0.3)" }}>
                <div style={{ fontSize: 52, marginBottom: 14 }}>📭</div>
                <p style={{ fontSize: 14 }}>لا يوجد محتوى متاح بعد</p>
              </div>
            )}

            {hasMore && !loading && (
              <button
                onClick={() => load(false)}
                style={{
                  width: "100%", marginTop: 22, padding: "13px 0",
                  background: "rgba(139,92,246,0.13)", border: "1px solid rgba(139,92,246,0.3)",
                  borderRadius: 13, color: "#c4b5fd", fontSize: 13, fontWeight: 700,
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                }}
              >
                <ChevronDown size={16} />
                تحميل المزيد ({total - items.length} متبقي)
              </button>
            )}

            {loading && items.length > 0 && (
              <div style={{ display: "flex", justifyContent: "center", padding: "24px 0" }}>
                <div style={{ width: 26, height: 26, border: "2.5px solid rgba(255,255,255,0.08)", borderTopColor: "#8b5cf6", borderRadius: "50%", animation: "spin 0.75s linear infinite" }} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
