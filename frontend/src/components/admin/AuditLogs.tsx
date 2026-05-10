import { useState, useEffect } from "react";
import { FileText, Filter, RefreshCw, Download } from "lucide-react";

interface AuditLogsProps {
  adminApi: any;
}

interface AuditLog {
  id: number;
  admin_id: number;
  action_type: string;
  action_details: string;
  target_type: string;
  target_id: string;
  ip_address: string;
  user_agent: string;
  status: string;
  created_at: string;
}

export default function AuditLogs({ adminApi }: AuditLogsProps) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState({
    action_type: "",
    start_date: "",
    end_date: ""
  });
  const limit = 50;

  useEffect(() => {
    loadLogs();
  }, [page]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getAuditLogs({
        limit,
        offset: page * limit,
        action_type: filters.action_type || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined
      });
      setLogs(data.logs);
      setTotal(data.total);
    } catch (error) {
      console.error("Failed to load audit logs:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = () => {
    setPage(0);
    loadLogs();
  };

  const handleClearFilters = () => {
    setFilters({ action_type: "", start_date: "", end_date: "" });
    setPage(0);
    setTimeout(loadLogs, 100);
  };

  const getActionColor = (actionType: string) => {
    if (actionType.includes("delete")) return "#f44336";
    if (actionType.includes("block")) return "#FF9800";
    if (actionType.includes("create") || actionType.includes("add")) return "#4CAF50";
    if (actionType.includes("view") || actionType.includes("get")) return "#2196F3";
    return "#9C27B0";
  };

  const getActionIcon = (actionType: string) => {
    if (actionType.includes("delete")) return "🗑️";
    if (actionType.includes("block")) return "🚫";
    if (actionType.includes("unblock")) return "✅";
    if (actionType.includes("create")) return "➕";
    if (actionType.includes("sync")) return "🔄";
    if (actionType.includes("scan")) return "🔍";
    return "📝";
  };

  const getStatusColor = (status: string) => {
    return status === "success" ? "#4CAF50" : "#f44336";
  };

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <FileText size={24} color="#9C27B0" />
          <h2 style={{ margin: 0, fontSize: 20, color: "#fff" }}>سجلات التدقيق</h2>
        </div>
        <button
          onClick={loadLogs}
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

      {/* Filters */}
      <div style={{
        background: "#1a1a1a",
        borderRadius: 12,
        border: "1px solid #333",
        padding: 20,
        marginBottom: 20
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 15 }}>
          <Filter size={18} color="#999" />
          <h3 style={{ margin: 0, fontSize: 14, color: "#999" }}>تصفية السجلات</h3>
        </div>
        
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 15, marginBottom: 15 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "#999", marginBottom: 5 }}>
              نوع الإجراء
            </label>
            <select
              value={filters.action_type}
              onChange={(e) => setFilters({ ...filters, action_type: e.target.value })}
              style={{
                width: "100%",
                padding: "10px 15px",
                background: "#0d0d0d",
                border: "1px solid #333",
                borderRadius: 8,
                color: "#fff",
                fontSize: 14
              }}
            >
              <option value="">الكل</option>
              <option value="view_stats">عرض الإحصائيات</option>
              <option value="block_user">حظر مستخدم</option>
              <option value="unblock_user">إلغاء حظر مستخدم</option>
              <option value="delete_user">حذف مستخدم</option>
              <option value="delete_movie">حذف فيلم</option>
              <option value="delete_series">حذف مسلسل</option>
              <option value="create_notification">إنشاء إشعار</option>
              <option value="sync_db">مزامنة قاعدة البيانات</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: 12, color: "#999", marginBottom: 5 }}>
              من تاريخ
            </label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
              style={{
                width: "100%",
                padding: "10px 15px",
                background: "#0d0d0d",
                border: "1px solid #333",
                borderRadius: 8,
                color: "#fff",
                fontSize: 14
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: 12, color: "#999", marginBottom: 5 }}>
              إلى تاريخ
            </label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
              style={{
                width: "100%",
                padding: "10px 15px",
                background: "#0d0d0d",
                border: "1px solid #333",
                borderRadius: 8,
                color: "#fff",
                fontSize: 14
              }}
            />
          </div>
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={handleFilter}
            style={{
              padding: "10px 20px",
              background: "#2196F3",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              cursor: "pointer",
              fontSize: 14,
              display: "flex",
              alignItems: "center",
              gap: 5
            }}
          >
            <Filter size={16} />
            تطبيق التصفية
          </button>
          <button
            onClick={handleClearFilters}
            style={{
              padding: "10px 20px",
              background: "#333",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              cursor: "pointer",
              fontSize: 14
            }}
          >
            مسح التصفية
          </button>
        </div>
      </div>

      {/* Stats */}
      <div style={{
        padding: 15,
        background: "#1a1a1a",
        borderRadius: 8,
        border: "1px solid #333",
        marginBottom: 20,
        fontSize: 14,
        color: "#999"
      }}>
        إجمالي السجلات: <span style={{ color: "#fff", fontWeight: "bold" }}>{total}</span>
        {" | "}
        الصفحة: <span style={{ color: "#fff", fontWeight: "bold" }}>{page + 1}</span> من{" "}
        <span style={{ color: "#fff", fontWeight: "bold" }}>{Math.ceil(total / limit)}</span>
      </div>

      {/* Logs List */}
      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
          جاري التحميل...
        </div>
      ) : logs.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
          لا توجد سجلات
        </div>
      ) : (
        <div style={{
          background: "#1a1a1a",
          borderRadius: 12,
          border: "1px solid #333",
          overflow: "hidden"
        }}>
          {logs.map((log, idx) => (
            <div key={log.id} style={{
              padding: 20,
              borderBottom: idx < logs.length - 1 ? "1px solid #333" : "none"
            }}>
              <div style={{ display: "flex", alignItems: "start", gap: 15 }}>
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: "50%",
                  background: `${getActionColor(log.action_type)}20`,
                  border: `2px solid ${getActionColor(log.action_type)}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 18
                }}>
                  {getActionIcon(log.action_type)}
                </div>
                
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5, flexWrap: "wrap" }}>
                    <div style={{
                      padding: "4px 10px",
                      background: `${getActionColor(log.action_type)}20`,
                      border: `1px solid ${getActionColor(log.action_type)}`,
                      borderRadius: 6,
                      fontSize: 12,
                      fontWeight: "bold",
                      color: getActionColor(log.action_type)
                    }}>
                      {log.action_type}
                    </div>
                    <div style={{
                      padding: "4px 10px",
                      background: `${getStatusColor(log.status)}20`,
                      border: `1px solid ${getStatusColor(log.status)}`,
                      borderRadius: 6,
                      fontSize: 11,
                      fontWeight: "bold",
                      color: getStatusColor(log.status)
                    }}>
                      {log.status === "success" ? "نجح" : "فشل"}
                    </div>
                  </div>

                  {log.action_details && (
                    <div style={{ fontSize: 13, color: "#ccc", marginBottom: 8 }}>
                      {log.action_details}
                    </div>
                  )}

                  <div style={{ fontSize: 11, color: "#666", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }}>
                    <div>
                      <span style={{ color: "#999" }}>المسؤول: </span>
                      <span style={{ color: "#fff" }}>{log.admin_id}</span>
                    </div>
                    {log.target_type && (
                      <div>
                        <span style={{ color: "#999" }}>الهدف: </span>
                        <span style={{ color: "#fff" }}>{log.target_type} ({log.target_id})</span>
                      </div>
                    )}
                    <div>
                      <span style={{ color: "#999" }}>IP: </span>
                      <span style={{ color: "#fff" }}>{log.ip_address}</span>
                    </div>
                    <div>
                      <span style={{ color: "#999" }}>التاريخ: </span>
                      <span style={{ color: "#fff" }}>{new Date(log.created_at).toLocaleString("ar-DZ")}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > limit && (
        <div style={{ marginTop: 20, display: "flex", justifyContent: "center", gap: 10 }}>
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            style={{
              padding: "10px 20px",
              background: page === 0 ? "#333" : "#2196F3",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              cursor: page === 0 ? "not-allowed" : "pointer",
              opacity: page === 0 ? 0.5 : 1
            }}
          >
            السابق
          </button>
          <div style={{
            padding: "10px 20px",
            background: "#1a1a1a",
            border: "1px solid #333",
            borderRadius: 8,
            color: "#fff"
          }}>
            {page + 1} / {Math.ceil(total / limit)}
          </div>
          <button
            onClick={() => setPage(Math.min(Math.ceil(total / limit) - 1, page + 1))}
            disabled={page >= Math.ceil(total / limit) - 1}
            style={{
              padding: "10px 20px",
              background: page >= Math.ceil(total / limit) - 1 ? "#333" : "#2196F3",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              cursor: page >= Math.ceil(total / limit) - 1 ? "not-allowed" : "pointer",
              opacity: page >= Math.ceil(total / limit) - 1 ? 0.5 : 1
            }}
          >
            التالي
          </button>
        </div>
      )}
    </div>
  );
}

// Made with Bob
