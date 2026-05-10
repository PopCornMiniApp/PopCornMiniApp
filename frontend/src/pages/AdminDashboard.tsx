import { useState } from "react";
import { Shield, BarChart3, Users, Film, Activity, Bell, FileText, X } from "lucide-react";
import { adminApi } from "../api";
import Analytics from "../components/admin/Analytics";
import UserManagement from "../components/admin/UserManagement";
import ContentManagement from "../components/admin/ContentManagement";
import ResourceMonitoring from "../components/admin/ResourceMonitoring";
import NotificationSystem from "../components/admin/NotificationSystem";
import AuditLogs from "../components/admin/AuditLogs";

const ADMIN_ID = 5703679073;

interface AdminDashboardProps {
  goBack: () => void;
}

type Tab = "analytics" | "users" | "content" | "resources" | "notifications" | "logs";

export default function AdminDashboard({ goBack }: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState<Tab>("analytics");
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [authError, setAuthError] = useState(false);

  // Check authorization on mount
  useState(() => {
    const checkAuth = async () => {
      try {
        // Try to fetch admin stats to verify authorization
        await adminApi.getStats();
        setIsAuthorized(true);
      } catch (error) {
        setAuthError(true);
      }
    };
    checkAuth();
  });

  if (authError) {
    return (
      <div style={{
        minHeight: "100vh",
        background: "#0d0d0d",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20
      }}>
        <div style={{
          maxWidth: 400,
          width: "100%",
          background: "#1a1a1a",
          borderRadius: 16,
          border: "2px solid #f44336",
          padding: 40,
          textAlign: "center"
        }}>
          <Shield size={64} color="#f44336" style={{ marginBottom: 20 }} />
          <h2 style={{ fontSize: 24, color: "#fff", marginBottom: 10 }}>غير مصرح</h2>
          <p style={{ fontSize: 14, color: "#999", marginBottom: 30 }}>
            ليس لديك صلاحية الوصول إلى لوحة التحكم الإدارية
          </p>
          <button
            onClick={goBack}
            style={{
              width: "100%",
              padding: "12px",
              background: "#2196F3",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontSize: 14,
              fontWeight: "bold",
              cursor: "pointer"
            }}
          >
            العودة للرئيسية
          </button>
        </div>
      </div>
    );
  }

  if (!isAuthorized) {
    return (
      <div style={{
        minHeight: "100vh",
        background: "#0d0d0d",
        display: "flex",
        alignItems: "center",
        justifyContent: "center"
      }}>
        <div style={{ textAlign: "center", color: "#999" }}>
          <div style={{ fontSize: 14 }}>جاري التحقق من الصلاحيات...</div>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: "analytics" as Tab, label: "الإحصائيات", icon: BarChart3, color: "#4CAF50" },
    { id: "users" as Tab, label: "المستخدمون", icon: Users, color: "#2196F3" },
    { id: "content" as Tab, label: "المحتوى", icon: Film, color: "#9C27B0" },
    { id: "resources" as Tab, label: "الموارد", icon: Activity, color: "#FF9800" },
    { id: "notifications" as Tab, label: "الإشعارات", icon: Bell, color: "#00BCD4" },
    { id: "logs" as Tab, label: "السجلات", icon: FileText, color: "#E91E63" }
  ];

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d", paddingBottom: 20 }}>
      {/* Header */}
      <div style={{
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        padding: "20px 20px 80px 20px",
        position: "relative"
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Shield size={28} color="#fff" />
            <h1 style={{ margin: 0, fontSize: 24, color: "#fff", fontWeight: "bold" }}>
              لوحة التحكم الإدارية
            </h1>
          </div>
          <button
            onClick={goBack}
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.2)",
              border: "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer"
            }}
          >
            <X size={20} color="#fff" />
          </button>
        </div>
        <div style={{ fontSize: 14, color: "rgba(255,255,255,0.9)" }}>
          مرحباً Admin | ID: {ADMIN_ID}
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        marginTop: -60,
        padding: "0 20px",
        overflowX: "auto",
        whiteSpace: "nowrap",
        scrollbarWidth: "none",
        msOverflowStyle: "none"
      }}>
        <div style={{ display: "inline-flex", gap: 10, paddingBottom: 10 }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: "12px 20px",
                  background: isActive ? "#1a1a1a" : "rgba(255,255,255,0.1)",
                  border: isActive ? "2px solid " + tab.color : "2px solid transparent",
                  borderRadius: 12,
                  color: "#fff",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  fontSize: 14,
                  fontWeight: isActive ? "bold" : "normal",
                  transition: "all 0.2s",
                  whiteSpace: "nowrap"
                }}
              >
                <Icon size={18} color={isActive ? tab.color : "#fff"} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div style={{ marginTop: 20 }}>
        {activeTab === "analytics" && <Analytics adminApi={adminApi} />}
        {activeTab === "users" && <UserManagement adminApi={adminApi} />}
        {activeTab === "content" && <ContentManagement adminApi={adminApi} />}
        {activeTab === "resources" && <ResourceMonitoring adminApi={adminApi} />}
        {activeTab === "notifications" && <NotificationSystem adminApi={adminApi} />}
        {activeTab === "logs" && <AuditLogs adminApi={adminApi} />}
      </div>
    </div>
  );
}

// Made with Bob
