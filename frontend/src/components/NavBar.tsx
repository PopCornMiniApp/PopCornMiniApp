import { Home, Search, Grid, Tv } from "lucide-react";

interface Props {
  current: string;
  browseType?: string;
  navigate: (r: any) => void;
}

export default function NavBar({ current, browseType, navigate }: Props) {
  const tabs = [
    { id: "home",   label: "الرئيسية", icon: <Home size={20} /> },
    { id: "movies", label: "أفلام",    icon: <Grid size={20} /> },
    { id: "series", label: "مسلسلات",  icon: <Tv size={20} /> },
    { id: "search", label: "بحث",      icon: <Search size={20} /> },
  ];

  const isActive = (id: string) => {
    if (id === "home") return current === "home";
    if (id === "movies") return current === "browse" && browseType !== "series";
    if (id === "series") return current === "browse" && browseType === "series";
    return current === id;
  };

  return (
    <nav style={{
      position: "fixed",
      bottom: 0, left: 0, right: 0,
      zIndex: 90,
      background: "rgba(13,13,13,0.96)",
      backdropFilter: "blur(20px)",
      borderTop: "1px solid rgba(255,255,255,0.07)",
      display: "flex",
      paddingBottom: "calc(var(--tg-safe-bottom, env(safe-area-inset-bottom, 0px)) + 4px)",
    }}>
      {tabs.map(t => {
        const active = isActive(t.id);
        return (
          <button
            key={t.id}
            onClick={() => {
              if (t.id === "home")   navigate({ page: "home" });
              else if (t.id === "movies") navigate({ page: "browse", type: "movies" });
              else if (t.id === "series") navigate({ page: "browse", type: "series" });
              else navigate({ page: "search" });
            }}
            style={{
              flex: 1, padding: "10px 0 6px", display: "flex", flexDirection: "column",
              alignItems: "center", gap: 3,
              color: active ? "#f59e0b" : "rgba(255,255,255,0.4)",
              transition: "color 0.2s",
            }}
          >
            <div style={{
              padding: "4px 12px", borderRadius: 12,
              background: active ? "rgba(245,158,11,0.12)" : "transparent",
              transition: "background 0.2s",
            }}>
              {t.icon}
            </div>
            <span style={{ fontSize: 10, fontWeight: active ? 700 : 400 }}>{t.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
