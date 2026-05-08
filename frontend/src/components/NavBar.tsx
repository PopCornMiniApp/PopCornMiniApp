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
    <div style={{
      position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 100,
      background: "rgba(13,13,13,0.97)", backdropFilter: "blur(14px)",
      borderTop: "1px solid rgba(255,255,255,0.07)",
      display: "flex", justifyContent: "space-around",
      padding: "8px 0 max(10px,env(safe-area-inset-bottom))",
    }}>
      {items.map(({ key, icon: Icon, label, action }) => {
        const active = activeKey === key;
        return (
          <button key={key} onClick={action} style={{
            display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
            padding: "4px 16px", color: active ? "#8b5cf6" : "rgba(255,255,255,0.38)",
            transition: "color 0.2s",
          }}>
            <Icon size={22} strokeWidth={active ? 2.5 : 1.8} />
            <span style={{ fontSize: 10, fontWeight: active ? 700 : 400 }}>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
