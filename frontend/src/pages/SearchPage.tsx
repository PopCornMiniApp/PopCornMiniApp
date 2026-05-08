import { useState, useEffect, useRef } from "react";
import { api, type Movie, type Series } from "../api";
import ContentCard from "../components/ContentCard";
import { ArrowRight, Search, X } from "lucide-react";

interface Props { navigate: (r: any) => void; goBack: () => void; }

export default function SearchPage({ navigate, goBack }: Props) {
  const [query, setQuery] = useState("");
  const [movies, setMovies] = useState<Movie[]>([]);
  const [series, setSeries] = useState<Series[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { setTimeout(() => inputRef.current?.focus(), 300); }, []);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (!query.trim()) { setMovies([]); setSeries([]); setSearched(false); return; }
    setLoading(true);
    timer.current = setTimeout(() => {
      api.search(query.trim()).then(r => {
        setMovies(r.movies);
        setSeries(r.series);
        setLoading(false);
        setSearched(true);
      }).catch(() => setLoading(false));
    }, 400);
  }, [query]);

  const total = movies.length + series.length;

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      {/* Header */}
      <div style={{
        position: "sticky", top: 0, zIndex: 50,
        background: "rgba(13,13,13,0.95)", backdropFilter: "blur(14px)",
        padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button onClick={goBack} style={{ color: "rgba(255,255,255,0.6)", flexShrink: 0 }}>
            <ArrowRight size={20} />
          </button>
          <div style={{
            flex: 1, display: "flex", alignItems: "center", gap: 8,
            background: "rgba(255,255,255,0.07)", borderRadius: 14, padding: "9px 14px",
            border: "1px solid rgba(255,255,255,0.1)",
          }}>
            <Search size={15} color="rgba(255,255,255,0.4)" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="ابحث بالعربية أو الإنجليزية..."
              style={{
                flex: 1, background: "none", border: "none", color: "#fff",
                fontSize: 14, direction: "auto",
              }}
            />
            {query && (
              <button onClick={() => setQuery("")} style={{ color: "rgba(255,255,255,0.4)", flexShrink: 0 }}>
                <X size={15} />
              </button>
            )}
          </div>
        </div>
      </div>

      <div style={{ padding: "16px 16px 80px" }}>
        {/* Loading */}
        {loading && (
          <div style={{ display: "flex", justifyContent: "center", padding: "40px 0" }}>
            <div style={{ width: 28, height: 28, border: "2.5px solid rgba(255,255,255,0.1)", borderTopColor: "#8b5cf6", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
            <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          </div>
        )}

        {/* Empty state */}
        {!loading && !query && (
          <div style={{ textAlign: "center", padding: "60px 20px" }}>
            <div style={{ fontSize: 56, marginBottom: 16 }}>🔍</div>
            <p style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>ابحث عن أي عمل</p>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", lineHeight: 1.6 }}>
              يمكنك البحث بالاسم العربي أو الإنجليزي
              <br />مثال: "Stranger Things" أو "ستيف جوبز"
            </p>
          </div>
        )}

        {/* No results */}
        {!loading && searched && total === 0 && query && (
          <div style={{ textAlign: "center", padding: "60px 20px" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🎭</div>
            <p style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>لا توجد نتائج</p>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.4)" }}>لم نجد شيئاً عن "{query}"</p>
          </div>
        )}

        {/* Results */}
        {!loading && searched && total > 0 && (
          <>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", marginBottom: 16 }}>
              {total} نتيجة عن "{query}"
            </p>

            {movies.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "#c4b5fd" }}>🎬 أفلام ({movies.length})</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
                  {movies.map(m => (
                    <ContentCard key={m.id} id={m.id} type="movie" title={m.title} title_ar={m.title_ar}
                      poster_path={m.poster_path} rating={m.rating} has_file={m.has_file}
                      year={m.release_date}
                      onClick={() => navigate({ page: "movie", id: m.id })} />
                  ))}
                </div>
              </div>
            )}

            {series.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "#c4b5fd" }}>📺 مسلسلات ({series.length})</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
                  {series.map(s => (
                    <ContentCard key={s.id} id={s.id} type="series" title={s.title} title_ar={s.title_ar}
                      poster_path={s.poster_path} rating={s.rating} has_file={true}
                      year={s.first_air_date}
                      onClick={() => navigate({ page: "series", id: s.id })} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
