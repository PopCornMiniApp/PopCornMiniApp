import { useState, useEffect } from "react";
import { BarChart3, TrendingUp, Users, Film, Tv, Eye } from "lucide-react";

interface AnalyticsProps {
  adminApi: any;
}

interface Stats {
  total_movies: number;
  total_series: number;
  total_episodes: number;
  movies_with_files: number;
  episodes_with_files: number;
  total_users: number;
  blocked_users: number;
  premium_users: number;
  views_24h: number;
  searches_24h: number;
  top_movies: Array<{ id: string; title: string; title_ar: string; views: number }>;
  recent_users: Array<{ user_id: number; username: string; first_name: string; last_name: string; last_active: string }>;
}

export default function Analytics({ adminApi }: AnalyticsProps) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getStats();
      setStats(data);
    } catch (error) {
      console.error("Failed to load stats:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 20, textAlign: "center", color: "#999" }}>
        <div style={{ fontSize: 14 }}>جاري تحميل الإحصائيات...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div style={{ padding: 20, textAlign: "center", color: "#f44336" }}>
        فشل تحميل الإحصائيات
      </div>
    );
  }

  const StatCard = ({ icon: Icon, label, value, color }: any) => (
    <div style={{
      background: "linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)",
      borderRadius: 12,
      padding: 20,
      border: "1px solid #333",
      display: "flex",
      alignItems: "center",
      gap: 15
    }}>
      <div style={{
        width: 50,
        height: 50,
        borderRadius: 10,
        background: `${color}20`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center"
      }}>
        <Icon size={24} color={color} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, color: "#999", marginBottom: 4 }}>{label}</div>
        <div style={{ fontSize: 24, fontWeight: "bold", color: "#fff" }}>{value.toLocaleString()}</div>
      </div>
    </div>
  );

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
        <BarChart3 size={24} color="#4CAF50" />
        <h2 style={{ margin: 0, fontSize: 20, color: "#fff" }}>الإحصائيات والتحليلات</h2>
      </div>

      {/* Content Stats */}
      <div style={{ marginBottom: 30 }}>
        <h3 style={{ fontSize: 16, color: "#999", marginBottom: 15 }}>إحصائيات المحتوى</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 15 }}>
          <StatCard icon={Film} label="إجمالي الأفلام" value={stats.total_movies} color="#2196F3" />
          <StatCard icon={Tv} label="إجمالي المسلسلات" value={stats.total_series} color="#9C27B0" />
          <StatCard icon={Film} label="إجمالي الحلقات" value={stats.total_episodes} color="#FF9800" />
          <StatCard icon={Film} label="أفلام بملفات" value={stats.movies_with_files} color="#4CAF50" />
          <StatCard icon={Tv} label="حلقات بملفات" value={stats.episodes_with_files} color="#00BCD4" />
        </div>
      </div>

      {/* User Stats */}
      <div style={{ marginBottom: 30 }}>
        <h3 style={{ fontSize: 16, color: "#999", marginBottom: 15 }}>إحصائيات المستخدمين</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 15 }}>
          <StatCard icon={Users} label="إجمالي المستخدمين" value={stats.total_users} color="#4CAF50" />
          <StatCard icon={Users} label="مستخدمون محظورون" value={stats.blocked_users} color="#f44336" />
          <StatCard icon={Users} label="مستخدمون مميزون" value={stats.premium_users} color="#FFD700" />
        </div>
      </div>

      {/* Activity Stats */}
      <div style={{ marginBottom: 30 }}>
        <h3 style={{ fontSize: 16, color: "#999", marginBottom: 15 }}>النشاط (آخر 24 ساعة)</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 15 }}>
          <StatCard icon={Eye} label="المشاهدات" value={stats.views_24h} color="#2196F3" />
          <StatCard icon={TrendingUp} label="عمليات البحث" value={stats.searches_24h} color="#9C27B0" />
        </div>
      </div>

      {/* Top Movies */}
      {stats.top_movies && stats.top_movies.length > 0 && (
        <div style={{ marginBottom: 30 }}>
          <h3 style={{ fontSize: 16, color: "#999", marginBottom: 15 }}>الأفلام الأكثر مشاهدة (آخر 7 أيام)</h3>
          <div style={{
            background: "#1a1a1a",
            borderRadius: 12,
            border: "1px solid #333",
            overflow: "hidden"
          }}>
            {stats.top_movies.map((movie, idx) => (
              <div key={movie.id} style={{
                padding: 15,
                borderBottom: idx < stats.top_movies.length - 1 ? "1px solid #333" : "none",
                display: "flex",
                alignItems: "center",
                gap: 15
              }}>
                <div style={{
                  width: 30,
                  height: 30,
                  borderRadius: "50%",
                  background: "#2196F3",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 14,
                  fontWeight: "bold"
                }}>
                  {idx + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, color: "#fff", marginBottom: 2 }}>
                    {movie.title_ar || movie.title}
                  </div>
                  <div style={{ fontSize: 12, color: "#999" }}>{movie.title}</div>
                </div>
                <div style={{ fontSize: 14, color: "#4CAF50", fontWeight: "bold" }}>
                  {movie.views} مشاهدة
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Users */}
      {stats.recent_users && stats.recent_users.length > 0 && (
        <div>
          <h3 style={{ fontSize: 16, color: "#999", marginBottom: 15 }}>المستخدمون النشطون مؤخراً</h3>
          <div style={{
            background: "#1a1a1a",
            borderRadius: 12,
            border: "1px solid #333",
            overflow: "hidden"
          }}>
            {stats.recent_users.map((user, idx) => (
              <div key={user.user_id} style={{
                padding: 15,
                borderBottom: idx < stats.recent_users.length - 1 ? "1px solid #333" : "none",
                display: "flex",
                alignItems: "center",
                gap: 15
              }}>
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 16,
                  fontWeight: "bold",
                  color: "#fff"
                }}>
                  {(user.first_name || user.username || "U")[0].toUpperCase()}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, color: "#fff", marginBottom: 2 }}>
                    {user.first_name || user.username || `User ${user.user_id}`}
                  </div>
                  <div style={{ fontSize: 12, color: "#999" }}>
                    @{user.username || user.user_id}
                  </div>
                </div>
                <div style={{ fontSize: 12, color: "#999" }}>
                  {new Date(user.last_active).toLocaleString("ar-DZ")}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Made with Bob
