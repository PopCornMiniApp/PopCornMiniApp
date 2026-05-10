import { useState, useEffect } from "react";
import { Bell, Send, Plus, RefreshCw } from "lucide-react";

interface NotificationSystemProps {
  adminApi: any;
}

interface Notification {
  id: number;
  title: string;
  message: string;
  target_type: string;
  target_ids: string;
  scheduled_at: string;
  sent_at: string;
  status: string;
  created_at: string;
}

export default function NotificationSystem({ adminApi }: NotificationSystemProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [sending, setSending] = useState(false);
  
  const [formData, setFormData] = useState({
    title: "",
    message: "",
    target_type: "all",
    target_ids: "",
    scheduled_at: ""
  });

  useEffect(() => {
    loadNotifications();
  }, []);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getNotifications({ limit: 50, offset: 0 });
      setNotifications(data.notifications);
      setTotal(data.total);
    } catch (error) {
      console.error("Failed to load notifications:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.message) {
      alert("الرجاء ملء جميع الحقول المطلوبة");
      return;
    }

    try {
      setSending(true);
      await adminApi.createNotification(formData);
      alert("✅ تم إنشاء الإشعار بنجاح!");
      setFormData({ title: "", message: "", target_type: "all", target_ids: "", scheduled_at: "" });
      setShowForm(false);
      loadNotifications();
    } catch (error) {
      alert("❌ فشل إنشاء الإشعار");
    } finally {
      setSending(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "sent": return "#4CAF50";
      case "pending": return "#FF9800";
      case "failed": return "#f44336";
      case "cancelled": return "#999";
      default: return "#999";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "sent": return "تم الإرسال";
      case "pending": return "قيد الانتظار";
      case "failed": return "فشل";
      case "cancelled": return "ملغي";
      default: return status;
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Bell size={24} color="#FF9800" />
          <h2 style={{ margin: 0, fontSize: 20, color: "#fff" }}>نظام الإشعارات</h2>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={loadNotifications}
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
          <button
            onClick={() => setShowForm(!showForm)}
            style={{
              padding: "10px 20px",
              background: "#4CAF50",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 5
            }}
          >
            <Plus size={16} />
            إشعار جديد
          </button>
        </div>
      </div>

      {/* Create Form */}
      {showForm && (
        <div style={{
          background: "#1a1a1a",
          borderRadius: 12,
          border: "1px solid #333",
          padding: 20,
          marginBottom: 20
        }}>
          <h3 style={{ fontSize: 16, color: "#fff", marginBottom: 15 }}>إنشاء إشعار جديد</h3>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", fontSize: 12, color: "#999", marginBottom: 5 }}>
                العنوان *
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                required
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

            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", fontSize: 12, color: "#999", marginBottom: 5 }}>
                الرسالة *
              </label>
              <textarea
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                required
                rows={4}
                style={{
                  width: "100%",
                  padding: "10px 15px",
                  background: "#0d0d0d",
                  border: "1px solid #333",
                  borderRadius: 8,
                  color: "#fff",
                  fontSize: 14,
                  resize: "vertical"
                }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 15, marginBottom: 15 }}>
              <div>
                <label style={{ display: "block", fontSize: 12, color: "#999", marginBottom: 5 }}>
                  نوع الهدف
                </label>
                <select
                  value={formData.target_type}
                  onChange={(e) => setFormData({ ...formData, target_type: e.target.value })}
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
                  <option value="all">الكل</option>
                  <option value="user">مستخدم محدد</option>
                  <option value="group">مجموعة</option>
                </select>
              </div>

              {formData.target_type !== "all" && (
                <div>
                  <label style={{ display: "block", fontSize: 12, color: "#999", marginBottom: 5 }}>
                    معرفات الهدف (مفصولة بفواصل)
                  </label>
                  <input
                    type="text"
                    value={formData.target_ids}
                    onChange={(e) => setFormData({ ...formData, target_ids: e.target.value })}
                    placeholder="123,456,789"
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
              )}
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <button
                type="submit"
                disabled={sending}
                style={{
                  flex: 1,
                  padding: "12px",
                  background: sending ? "#333" : "#4CAF50",
                  border: "none",
                  borderRadius: 8,
                  color: "#fff",
                  cursor: sending ? "not-allowed" : "pointer",
                  fontSize: 14,
                  fontWeight: "bold",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  opacity: sending ? 0.6 : 1
                }}
              >
                <Send size={16} />
                {sending ? "جاري الإرسال..." : "إرسال الإشعار"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                style={{
                  padding: "12px 20px",
                  background: "#333",
                  border: "none",
                  borderRadius: 8,
                  color: "#fff",
                  cursor: "pointer",
                  fontSize: 14
                }}
              >
                إلغاء
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Notifications List */}
      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
          جاري التحميل...
        </div>
      ) : notifications.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
          لا توجد إشعارات
        </div>
      ) : (
        <div style={{
          background: "#1a1a1a",
          borderRadius: 12,
          border: "1px solid #333",
          overflow: "hidden"
        }}>
          {notifications.map((notif, idx) => (
            <div key={notif.id} style={{
              padding: 20,
              borderBottom: idx < notifications.length - 1 ? "1px solid #333" : "none"
            }}>
              <div style={{ display: "flex", alignItems: "start", gap: 15, marginBottom: 10 }}>
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: "50%",
                  background: `${getStatusColor(notif.status)}20`,
                  border: `2px solid ${getStatusColor(notif.status)}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center"
                }}>
                  <Bell size={18} color={getStatusColor(notif.status)} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
                    <div style={{ fontSize: 16, color: "#fff", fontWeight: "bold" }}>
                      {notif.title}
                    </div>
                    <div style={{
                      padding: "4px 10px",
                      background: `${getStatusColor(notif.status)}20`,
                      border: `1px solid ${getStatusColor(notif.status)}`,
                      borderRadius: 6,
                      fontSize: 11,
                      fontWeight: "bold",
                      color: getStatusColor(notif.status)
                    }}>
                      {getStatusText(notif.status)}
                    </div>
                  </div>
                  <div style={{ fontSize: 14, color: "#ccc", marginBottom: 8 }}>
                    {notif.message}
                  </div>
                  <div style={{ fontSize: 11, color: "#666", display: "flex", gap: 15, flexWrap: "wrap" }}>
                    <span>الهدف: {notif.target_type === "all" ? "الكل" : notif.target_type}</span>
                    <span>تم الإنشاء: {new Date(notif.created_at).toLocaleString("ar-DZ")}</span>
                    {notif.sent_at && (
                      <span>تم الإرسال: {new Date(notif.sent_at).toLocaleString("ar-DZ")}</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Made with Bob
