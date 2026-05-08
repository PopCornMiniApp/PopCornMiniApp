import { useState, useCallback, useRef } from "react";
import { api, type Movie, type Series } from "../api";
import ContentCard from "../components/ContentCard";
import { Search, X, ArrowRight } from "lucide-react";

interface Props { navigate: (r: any) => void; goBack: () => void; }

export default function SearchPage({ navigate, goBack }: Props) {
  const [query, setQuery] = useState("");
  const [movies, setMovies] = useState<Movie[]>([]);
  const [series, setSeries] = useState<Series[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const doSearch = useCallback((q: string) => {
    if (!q.trim()) { setMovies([]); setSeries([]); setSearched(false); return; }
    setLoading(true);
    api.search(q).then(r => {
      setMovies(r.movies);
      setSeries(r.series);
      setLoading(false);
      setSearched(true);
    }).catch(() => setLoading(false));
  }, []);

  const onChange = (v: string) => {
    setQuery(v);
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => doSearch(v), 400);
  };

  const total = movies.length + series.length;

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      {/* Header */}
      <div style={{
        position: "sticky", top: 0, zIndex: 50,
        background: "rgba(13,13,13,0.97)", backdropFilter: "blur(14px)",
        padding: "12px 16px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button onClick={goBack} style={{ display: "flex", padding: 4 }}>
            <ArrowRight size={20} />
          </button>
          <div style={{
            flex: 1, display: "flex", alignItems: "center", gap: 8,
            background: "rgba(255,255,255,0.07)", borderRadius: 12,
            padding: "9px 14px", border: "1px solid rgba(255,255,255,0.1)",
          }}>
            <Search size={15} color="rgba(255,255,255,0.45)" />
            <input
              ref={inputRef}
              autoFocus
              value={query}
              onChange={e => onChange(e.target.value)}
              placeholder="ابحث عن فيلم أو مسلسل..."
              style={{
                flex: 1, background: "none", border: "none", color: "#fff",
                fontSize: 14, direction: "rtl",
              }}
            />
            {query && (
              <button onClick={() => { setQuery(""); setMovies([]); setSeries([]); setSearched(false); inputRef.current?.focus(); }}>
                <X size={14} color="rgba(255,255,255,0.4)" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div style={{ padding: "16px 16px 80px" }}>
        {loading && (
          <div style={{ display: "flex", justifyContent: "center", padding: "40px 0" }}>
            <div style={{ width: 30, height: 30, border: "3px solid rgba(255,255,255,0.08)", borderTopColor: "#f59e0b", borderRadius: "50%", animation: "spin 0.75s linear infinite" }} />
            <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          </div>
        )}

        {!loading && searched && total === 0 && (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "rgba(255,255,255,0.35)" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🔍</div>
            <p style={{ fontSize: 14 }}>لا توجد نتائج لـ "{query}"</p>
          </div>
        )}

        {!loading && !searched && !query && (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "rgba(255,255,255,0.25)" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🎬</div>
            <p style={{ fontSize: 14 }}>ابدأ الكتابة للبحث...</p>
          </div>
        )}

        {movies.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "#f59e0b" }}>
              أفلام ({movies.length})
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
              {movies.map(m => (
                <ContentCard
                  key={m.id} id={m.id} type="movie"
                  title={m.title} title_ar={m.title_ar}
                  poster_path={m.poster_path} rating={m.rating}
                  has_file={m.has_file ?? (m.file_id != null)}
                  year={m.release_date}
                  onClick={() => navigate({ page: "movie", id: m.id })}
                />
              ))}
            </div>
          </div>
        )}

        {series.length > 0 && (
          <div>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "#f59e0b" }}>
              مسلسلات ({series.length})
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
              {series.map(s => (
                <ContentCard
                  key={s.id} id={s.id} type="series"
                  title={s.title} title_ar={s.title_ar}
                  poster_path={s.poster_path} rating={s.rating}
                  has_file={(s as any).has_file}
                  year={s.first_air_date}
                  onClick={() => navigate({ page: "series", id: s.id })}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
