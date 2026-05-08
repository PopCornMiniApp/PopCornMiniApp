import { Home, Search, Film, Tv } from "lucide-react";

interface Props {
  current: string;
  browseType?: "movies" | "series";
  navigate: (r: any) => void;
}

export default function NavBar({ current, browseType, navigate }: Props) {
  const items = [
    { key: "home",   icon: Home,   label: "الرئيسية", action: () => navigate({ page: "home" }) },
    { key: "movies", icon: Film,   label: "أفلام",    action: () => navigate({ page: "browse", type: "movies" }) },
    { key: "series", icon: Tv,     label: "مسلسلات",  action: () => navigate({ page: "browse", type: "series" }) },
    { key: "search", icon: Search, label: "بحث",      action: () => navigate({ page: "search" }) },
  ];

  const getActiveKey = () => {
    if (current === "browse") return browseType === "series" ? "series" : "movies";
    return current;
  };
  const activeKey = getActiveKey();

  return (
    <nav style={{
      position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 100,
      background: "rgba(13,13,13,0.97)",
      backdropFilter: "blur(20px)",
      borderTop: "1px solid rgba(255,255,255,0.07)",
      display: "flex",
      paddingBottom: "env(safe-area-inset-bottom, 0px)",
    }}>
      {items.map(({ key, icon: Icon, label, action }) => {
        const isActive = activeKey === key;
        return (
          <button
            key={key}
            onClick={action}
            style={{
              flex: 1, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              padding: "10px 0 8px",
              color: isActive ? "#f59e0b" : "rgba(255,255,255,0.38)",
              transition: "color 0.2s",
              gap: 4,
            }}
          >
            <Icon size={22} strokeWidth={isActive ? 2.2 : 1.6} />
            <span style={{ fontSize: 10, fontWeight: isActive ? 700 : 500, letterSpacing: 0.2 }}>
              {label}
            </span>
            {isActive && (
              <span style={{
                position: "absolute",
                bottom: "calc(100% - 2px + env(safe-area-inset-bottom, 0px))",
                width: 24, height: 3, borderRadius: 2,
                background: "#f59e0b",
                marginTop: -2,
              }} />
            )}
          </button>
        );
      })}
    </nav>
  );
}
