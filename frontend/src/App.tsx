import { useState, useEffect } from "react";
import Home from "./pages/Home";
import MovieDetail from "./pages/MovieDetail";
import SeriesDetail from "./pages/SeriesDetail";
import SearchPage from "./pages/SearchPage";
import BrowsePage from "./pages/BrowsePage";
import NavBar from "./components/NavBar";

type Route =
  | { page: "home" }
  | { page: "movie"; id: string }
  | { page: "series"; id: string }
  | { page: "search" }
  | { page: "browse"; type?: "movies" | "series"; genre?: string };

export default function App() {
  const [route, setRoute] = useState<Route>({ page: "home" });
  const [history, setHistory] = useState<Route[]>([]);

  const navigate = (r: Route) => {
    setHistory(h => [...h, route]);
    setRoute(r);
    window.scrollTo(0, 0);
  };

  const goBack = () => {
    if (!history.length) { setRoute({ page: "home" }); return; }
    const prev = history[history.length - 1];
    setHistory(h => h.slice(0, -1));
    setRoute(prev);
    window.scrollTo(0, 0);
  };

  useEffect(() => {
    const h = window.location.hash;
    if (h === "#/movies") navigate({ page: "browse", type: "movies" });
    else if (h === "#/series") navigate({ page: "browse", type: "series" });
    else if (h === "#/search") navigate({ page: "search" });
  }, []);

  const isDetail = route.page === "movie" || route.page === "series";
  const browseType = route.page === "browse" ? (route as any).type : undefined;

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d", paddingBottom: isDetail ? 0 : 70 }}>
      {route.page === "home"   && <Home navigate={navigate} />}
      {route.page === "movie"  && <MovieDetail id={(route as any).id} navigate={navigate} goBack={goBack} />}
      {route.page === "series" && <SeriesDetail id={(route as any).id} navigate={navigate} goBack={goBack} />}
      {route.page === "search" && <SearchPage navigate={navigate} goBack={goBack} />}
      {route.page === "browse" && (
        <BrowsePage
          type={(route as any).type}
          genre={(route as any).genre}
          navigate={navigate}
          goBack={goBack}
        />
      )}
      {!isDetail && <NavBar current={route.page} browseType={browseType} navigate={navigate} />}
    </div>
  );
}
