import { useState, useEffect } from "react";
import { Activity, Server, Database, RefreshCw, CheckCircle, XCircle, AlertCircle } from "lucide-react";

interface ResourceMonitoringProps {
  adminApi: any;
}

interface BotStatus {
  bot_name: string;
  bot_type: string;
  status: string;
  last_check: string;
  error_message?: string;
  uptime_seconds?: number;
  requests_count?: number;
}

interface SyncStatus {
  last_message_id: number;
  last_sync_time: string;
  sync_type: string;
}

export default function ResourceMonitoring({ adminApi }: ResourceMonitoringProps) {
  const [botStatus, setBotStatus] = useState<any>(null);
  const [syncStatus, setSyncStatus] = useState<{ sync_status: SyncStatus; stats: any } | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const [botData, syncData] = await Promise.all([
        adminApi.getBotStatus(),
        adminApi.getSyncStatus()
      ]);
      setBotStatus(botData);
      setSyncStatus(syncData);
    } catch (error) {
      console.error("Failed to load status:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncDB = async () => {
    if (!confirm("هل تريد مزامنة قاعدة البيانات مع HuggingFace؟")) return;
    try {
      setSyncing(true);
      await adminApi.syncDB();
      alert("✅ تمت المزامنة بنجاح!");
      loadStatus();
    } catch (error) {
      alert("❌ فشلت المزامنة");
    } finally {
      setSyncing(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <CheckCircle size={20} color="#4CAF50" />;
      case "inactive":
        return <XCircle size={20} color="#f44336" />;
      case "error":
        return <AlertCircle size={20} color="#FF9800" />;
      default:
        return <AlertCircle size={20} color="#999" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "#4CAF50";
      case "inactive":
        return "#f44336";
      case "error":
        return "#FF9800";
      default:
        return "#999";
    }
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Activity size={24} color="#4CAF50" />
          <h2 style={{ margin: 0, fontSize: 20, color: "#fff" }}>مراقبة الموارد</h2>
        </div>
        <button
          onClick={loadStatus}
          disabled={loading}
          style={{
            padding: "10px 20px",
            background: "#2196F3",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            cursor: loading ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: 5,
            opacity: loading ? 0.6 : 1
          }}
        >
          <RefreshCw size={16} />
          تحديث
        </button>
      </div>

      {loading && !botStatus ? (
        <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
          جاري التحميل...
        </div>
      ) : (
        <>
          {/* Pyrogram Status */}
          {botStatus?.pyrogram && (
            <div style={{ marginBottom: 30 }}>
              <h3 style={{ fontSize: 16, color: "#999", marginBottom: 15, display: "flex", alignItems: "center", gap: 8 }}>
                <Server size={18} />
                حالة Pyrogram
              </h3>
              <div style={{
                background: "#1a1a1a",
                borderRadius: 12,
                border: "1px solid #333",
                padding: 20
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 15, marginBottom: 15 }}>
                  {getStatusIcon(botStatus.pyrogram.status)}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 16, color: "#fff", fontWeight: "bold", marginBottom: 4 }}>
                      {botStatus.pyrogram.bot_name}
                    </div>
                    <div style={{ fontSize: 12, color: "#999" }}>
                      النوع: {botStatus.pyrogram.bot_type}
                    </div>
                  </div>
                  <div style={{
                    padding: "6px 12px",
                    background: `${getStatusColor(botStatus.pyrogram.status)}20`,
                    border: `1px solid ${getStatusColor(botStatus.pyrogram.status)}`,
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: "bold",
                    color: getStatusColor(botStatus.pyrogram.status)
                  }}>
                    {botStatus.pyrogram.status === "active" ? "نشط" : "غير نشط"}
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 15 }}>
                  <div>
                    <div style={{ fontSize: 11, color: "#666", marginBottom: 4 }}>عدد العملاء</div>
                    <div style={{ fontSize: 16, color: "#fff", fontWeight: "bold" }}>
                      {botStatus.pyrogram.clients_count}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#666", marginBottom: 4 }}>آخر فحص</div>
                    <div style={{ fontSize: 14, color: "#fff" }}>
                      {botStatus.pyrogram.last_check}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Other Bots */}
          {botStatus?.bots && botStatus.bots.length > 0 && (
            <div style={{ marginBottom: 30 }}>
              <h3 style={{ fontSize: 16, color: "#999", marginBottom: 15, display: "flex", alignItems: "center", gap: 8 }}>
                <Server size={18} />
                البوتات الأخرى
              </h3>
              <div style={{
                background: "#1a1a1a",
                borderRadius: 12,
                border: "1px solid #333",
                overflow: "hidden"
              }}>
                {botStatus.bots.map((bot: BotStatus, idx: number) => (
                  <div key={idx} style={{
                    padding: 20,
                    borderBottom: idx < botStatus.bots.length - 1 ? "1px solid #333" : "none"
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 15, marginBottom: 10 }}>
                      {getStatusIcon(bot.status)}
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 14, color: "#fff", fontWeight: "bold", marginBottom: 2 }}>
                          {bot.bot_name}
                        </div>
                        <div style={{ fontSize: 11, color: "#999" }}>
                          النوع: {bot.bot_type}
                        </div>
                      </div>
                      <div style={{
                        padding: "4px 10px",
                        background: `${getStatusColor(bot.status)}20`,
                        border: `1px solid ${getStatusColor(bot.status)}`,
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: "bold",
                        color: getStatusColor(bot.status)
                      }}>
                        {bot.status}
                      </div>
                    </div>
                    {bot.error_message && (
                      <div style={{
                        padding: 10,
                        background: "#f4433620",
                        border: "1px solid #f44336",
                        borderRadius: 6,
                        fontSize: 11,
                        color: "#f44336",
                        marginBottom: 10
                      }}>
                        {bot.error_message}
                      </div>
                    )}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 10, fontSize: 11 }}>
                      {bot.uptime_seconds !== undefined && (
                        <div>
                          <span style={{ color: "#666" }}>وقت التشغيل: </span>
                          <span style={{ color: "#fff" }}>{formatUptime(bot.uptime_seconds)}</span>
                        </div>
                      )}
                      {bot.requests_count !== undefined && (
                        <div>
                          <span style={{ color: "#666" }}>الطلبات: </span>
                          <span style={{ color: "#fff" }}>{bot.requests_count.toLocaleString()}</span>
                        </div>
                      )}
                      <div>
                        <span style={{ color: "#666" }}>آخر فحص: </span>
                        <span style={{ color: "#fff" }}>{new Date(bot.last_check).toLocaleString("ar-DZ")}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Database Sync Status */}
          {syncStatus && (
            <div style={{ marginBottom: 30 }}>
              <h3 style={{ fontSize: 16, color: "#999", marginBottom: 15, display: "flex", alignItems: "center", gap: 8 }}>
                <Database size={18} />
                حالة قاعدة البيانات
              </h3>
              <div style={{
                background: "#1a1a1a",
                borderRadius: 12,
                border: "1px solid #333",
                padding: 20
              }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 20, marginBottom: 20 }}>
                  <div>
                    <div style={{ fontSize: 11, color: "#666", marginBottom: 4 }}>آخر رسالة</div>
                    <div style={{ fontSize: 18, color: "#fff", fontWeight: "bold" }}>
                      {syncStatus.sync_status.last_message_id}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#666", marginBottom: 4 }}>آخر مزامنة</div>
                    <div style={{ fontSize: 14, color: "#fff" }}>
                      {new Date(syncStatus.sync_status.last_sync_time).toLocaleString("ar-DZ")}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#666", marginBottom: 4 }}>نوع المزامنة</div>
                    <div style={{ fontSize: 14, color: "#fff" }}>
                      {syncStatus.sync_status.sync_type}
                    </div>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 15, marginBottom: 20 }}>
                  <div style={{ padding: 15, background: "#2196F320", borderRadius: 8, border: "1px solid #2196F3" }}>
                    <div style={{ fontSize: 11, color: "#2196F3", marginBottom: 4 }}>الأفلام</div>
                    <div style={{ fontSize: 20, color: "#fff", fontWeight: "bold" }}>
                      {syncStatus.stats.movies_count}
                    </div>
                  </div>
                  <div style={{ padding: 15, background: "#9C27B020", borderRadius: 8, border: "1px solid #9C27B0" }}>
                    <div style={{ fontSize: 11, color: "#9C27B0", marginBottom: 4 }}>المسلسلات</div>
                    <div style={{ fontSize: 20, color: "#fff", fontWeight: "bold" }}>
                      {syncStatus.stats.series_count}
                    </div>
                  </div>
                  <div style={{ padding: 15, background: "#FF980020", borderRadius: 8, border: "1px solid #FF9800" }}>
                    <div style={{ fontSize: 11, color: "#FF9800", marginBottom: 4 }}>الحلقات</div>
                    <div style={{ fontSize: 20, color: "#fff", fontWeight: "bold" }}>
                      {syncStatus.stats.episodes_count}
                    </div>
                  </div>
                </div>

                <button
                  onClick={handleSyncDB}
                  disabled={syncing}
                  style={{
                    width: "100%",
                    padding: "12px",
                    background: syncing ? "#333" : "#4CAF50",
                    border: "none",
                    borderRadius: 8,
                    color: "#fff",
                    cursor: syncing ? "not-allowed" : "pointer",
                    fontSize: 14,
                    fontWeight: "bold",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 8,
                    opacity: syncing ? 0.6 : 1
                  }}
                >
                  <Database size={16} />
                  {syncing ? "جاري المزامنة..." : "مزامنة مع HuggingFace"}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Made with Bob
