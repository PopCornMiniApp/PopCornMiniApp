import { useState, useEffect } from "react";
import { api, type FeaturedItem, type Movie, type Series } from "../api";
import HeroCarousel from "../components/HeroCarousel";
import ContentCard from "../components/ContentCard";
import { Search, ChevronLeft } from "lucide-react";

interface Props { navigate: (r: any) => void; }

function ContentRow({ title, items, type, navigate, onMore }: { title: string; items: any[]; type: string; navigate: any; onMore?: () => void }) {
  if (!items.length) return null;
  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 16px", marginBottom: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>{title}</h2>
        {onMore && (
          <button onClick={onMore} style={{ display: "flex", alignItems: "center", gap: 2, color: "#f59e0b", fontSize: 12 }}>
            المزيد <ChevronLeft size={14} />
          </button>
        )}
      </div>
      <div style={{
        display: "flex", gap: 12, overflowX: "auto", paddingRight: 16, paddingLeft: 16,
        scrollbarWidth: "none", WebkitOverflowScrolling: "touch",
      } as any}>
        {items.map((item: any) => (
          <div key={item.id} style={{ flexShrink: 0, width: 120 }}>
            <ContentCard
              id={item.id}
              type={(item.type || type) as any}
              title={item.title}
              title_ar={item.title_ar}
              poster_path={item.poster_path}
              rating={item.rating}
              has_file={item.has_file ?? (item.file_id != null)}
              year={item.release_date || item.first_air_date || item.date}
              onClick={() => {
                const t = item.type || type;
                if (t === "series") navigate({ page: "series", id: item.id });
                else navigate({ page: "movie", id: item.id });
              }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home({ navigate }: Props) {
  const [featured, setFeatured] = useState<FeaturedItem[]>([]);
  const [movies, setMovies] = useState<Movie[]>([]);
  const [series, setSeries] = useState<Series[]>([]);
  const [topRated, setTopRated] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [genres, setGenres] = useState<string[]>([]);
  const [activeGenre, setActiveGenre] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.featured(),
      api.movies({ limit: 14 }),
      api.series({ limit: 8 }),
      api.movies({ limit: 10, sort: "rating", has_file: true }),
      api.genres(),
    ]).then(([feat, mov, ser, top, gen]) => {
      setFeatured(feat.items);
      setMovies(mov.items);
      setSeries(ser.items);
      setTopRated(top.items);
      setGenres(gen.genres.slice(0, 12));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const filteredMovies = activeGenre
    ? movies.filter(m => (m.genres as any[])?.some((g: any) => (typeof g === "string" ? g : g.name) === activeGenre))
    : movies;
  const filteredSeries = activeGenre
    ? series.filter(s => (s.genres as any[])?.some((g: any) => (typeof g === "string" ? g : g.name) === activeGenre))
    : series;

  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "60vh", gap: 16 }}>
        <div style={{ fontSize: 56 }}>🍿</div>
        <div style={{ width: 36, height: 36, border: "3px solid rgba(255,255,255,0.1)", borderTopColor: "#f59e0b", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    );
  }

  return (
    <div>
      {/* Sticky Header */}
      <div style={{
        position: "sticky", top: 0, zIndex: 50,
        background: "rgba(13,13,13,0.92)", backdropFilter: "blur(14px)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 22 }}>🍿</span>
          <span style={{ fontSize: 18, fontWeight: 800, background: "linear-gradient(135deg,#f59e0b,#fbbf24)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            PopCorn
          </span>
        </div>
        <button onClick={() => navigate({ page: "search" })} style={{
          background: "rgba(255,255,255,0.08)", borderRadius: 20, padding: "7px 14px",
          display: "flex", alignItems: "center", gap: 6, color: "rgba(255,255,255,0.55)", fontSize: 13,
          border: "1px solid rgba(255,255,255,0.08)",
        }}>
          <Search size={14} /> بحث...
        </button>
      </div>

      {/* Hero Carousel */}
      {featured.length > 0 && <HeroCarousel items={featured} navigate={navigate} />}

      {/* Genre pills */}
      {genres.length > 0 && (
        <div style={{ display: "flex", gap: 8, overflowX: "auto", padding: "16px 16px 8px", scrollbarWidth: "none" } as any}>
          <button onClick={() => setActiveGenre(null)} style={{
            flexShrink: 0, padding: "6px 16px", borderRadius: 20, fontSize: 12, fontWeight: 600,
            background: !activeGenre ? "#f59e0b" : "rgba(255,255,255,0.07)",
            color: !activeGenre ? "#000" : "rgba(255,255,255,0.55)",
            border: !activeGenre ? "1px solid #f59e0b" : "1px solid rgba(255,255,255,0.1)",
            transition: "all 0.2s",
          }}>الكل</button>
          {genres.map(g => (
            <button key={g} onClick={() => setActiveGenre(g === activeGenre ? null : g)} style={{
              flexShrink: 0, padding: "6px 16px", borderRadius: 20, fontSize: 12, fontWeight: 600,
              background: activeGenre === g ? "#f59e0b" : "rgba(255,255,255,0.07)",
              color: activeGenre === g ? "#000" : "rgba(255,255,255,0.55)",
              border: activeGenre === g ? "1px solid #f59e0b" : "1px solid rgba(255,255,255,0.1)",
              transition: "all 0.2s",
            }}>{g}</button>
          ))}
        </div>
      )}

      <div style={{ paddingTop: 20 }}>
        {!activeGenre && topRated.length > 0 && (
          <ContentRow title="⭐ الأعلى تقييماً" items={topRated} type="movie" navigate={navigate}
            onMore={() => navigate({ page: "browse", type: "movies" })} />
        )}
        {filteredMovies.length > 0 && (
          <ContentRow title="🎬 أحدث الأفلام" items={filteredMovies} type="movie" navigate={navigate}
            onMore={() => navigate({ page: "browse", type: "movies" })} />
        )}
        {filteredSeries.length > 0 && (
          <ContentRow title="📺 المسلسلات" items={filteredSeries} type="series" navigate={navigate}
            onMore={() => navigate({ page: "browse", type: "series" })} />
        )}
        {filteredMovies.length === 0 && filteredSeries.length === 0 && activeGenre && (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "rgba(255,255,255,0.35)" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🎭</div>
            <p style={{ fontSize: 14 }}>لا يوجد محتوى في تصنيف "{activeGenre}"</p>
          </div>
        )}
      </div>
    </div>
  );
}
