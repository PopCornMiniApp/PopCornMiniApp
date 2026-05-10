import { useState, useEffect, useCallback } from "react";
import Home from "./pages/Home";
import MovieDetail from "./pages/MovieDetail";
import SeriesDetail from "./pages/SeriesDetail";
import SearchPage from "./pages/SearchPage";
import BrowsePage from "./pages/BrowsePage";
import AdminDashboard from "./pages/AdminDashboard";
import NavBar from "./components/NavBar";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        expand: () => void;
        ready: () => void;
        BackButton: {
          show: () => void; hide: () => void;
          onClick: (fn: () => void) => void;
          offClick: (fn: () => void) => void;
          isVisible: boolean;
        };
        safeAreaInset?: { top: number; bottom: number; left: number; right: number };
      };
    };
  }
}

type Route =
  | { page: "home" }
  | { page: "movie"; id: string }
  | { page: "series"; id: string }
  | { page: "search" }
  | { page: "browse"; type?: "movies" | "series"; genre?: string }
  | { page: "admin" };

export default function App() {
  const [route, setRoute] = useState<Route>({ page: "home" });
  const [history, setHistory] = useState<Route[]>([]);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      /* Only use safeAreaInset — the phone's actual notch/status-bar height.
         contentSafeAreaInset includes Telegram's UI which is OUTSIDE the viewport,
         adding it would create a large unnecessary top gap. */
      const top = tg.safeAreaInset?.top ?? 0;
      document.documentElement.style.setProperty("--tg-safe-top", `${top}px`);
    }
    const h = window.location.hash;
    if (h === "#/movies") navigate({ page: "browse", type: "movies" });
    else if (h === "#/series") navigate({ page: "browse", type: "series" });
    else if (h === "#/search") navigate({ page: "search" });
    else if (h === "#/admin") navigate({ page: "admin" });
  }, []);

  const goBack = useCallback(() => {
    setHistory(h => {
      if (!h.length) { setRoute({ page: "home" }); return h; }
      const prev = h[h.length - 1];
      setRoute(prev);
      window.scrollTo(0, 0);
      return h.slice(0, -1);
    });
  }, []);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg?.BackButton) return;
    if (history.length > 0) {
      tg.BackButton.show();
      tg.BackButton.onClick(goBack);
      return () => tg.BackButton.offClick(goBack);
    } else {
      tg.BackButton.hide();
    }
  }, [history.length, goBack]);

  const navigate = (r: Route) => {
    setHistory(h => [...h, route]);
    setRoute(r);
    window.scrollTo(0, 0);
  };

  const isDetail = route.page === "movie" || route.page === "series";
  const isAdmin = route.page === "admin";
  const browseType = route.page === "browse" ? (route as any).type : undefined;

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d", paddingBottom: isDetail || isAdmin ? 0 : 70 }}>
      {route.page === "home"   && <Home navigate={navigate} />}
      {route.page === "movie"  && <MovieDetail id={(route as any).id} navigate={navigate} goBack={goBack} />}
      {route.page === "series" && <SeriesDetail id={(route as any).id} navigate={navigate} goBack={goBack} />}
      {route.page === "search" && <SearchPage navigate={navigate} goBack={goBack} />}
      {route.page === "browse" && (
        <BrowsePage type={(route as any).type} genre={(route as any).genre} navigate={navigate} goBack={goBack} />
      )}
      {route.page === "admin" && <AdminDashboard goBack={goBack} />}
      {!isDetail && !isAdmin && <NavBar current={route.page} browseType={browseType} navigate={navigate} />}
    </div>
  );
}
