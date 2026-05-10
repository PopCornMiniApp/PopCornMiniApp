import { useState, useEffect } from "react";
import { Users, Search, Ban, Unlock, Trash2, RefreshCw, UserX } from "lucide-react";

interface UserManagementProps {
  adminApi: any;
}

interface User {
  user_id: number;
  username: string;
  first_name: string;
  last_name: string;
  is_blocked: number;
  is_premium: number;
  language_code: string;
  created_at: string;
  last_active: string;
}

export default function UserManagement({ adminApi }: UserManagementProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [blockedOnly, setBlockedOnly] = useState(false);
  const [page, setPage] = useState(0);
  const limit = 20;

  useEffect(() => {
    loadUsers();
  }, [page, blockedOnly]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getUsers({
        limit,
        offset: page * limit,
        search: search || undefined,
        blocked_only: blockedOnly
      });
      setUsers(data.users);
      setTotal(data.total);
    } catch (error) {
      console.error("Failed to load users:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(0);
    loadUsers();
  };

  const handleBlock = async (userId: number) => {
    if (!confirm(`هل أنت متأكد من حظر المستخدم ${userId}؟`)) return;
    try {
      await adminApi.blockUser(userId);
      loadUsers();
    } catch (error) {
      alert("فشل حظر المستخدم");
    }
  };

  const handleUnblock = async (userId: number) => {
    try {
      await adminApi.unblockUser(userId);
      loadUsers();
    } catch (error) {
      alert("فشل إلغاء حظر المستخدم");
    }
  };

  const handleDelete = async (userId: number) => {
    if (!confirm(`⚠️ هل أنت متأكد من حذف المستخدم ${userId} وجميع بياناته؟ هذا الإجراء لا يمكن التراجع عنه!`)) return;
    try {
      await adminApi.deleteUser(userId);
      loadUsers();
    } catch (error) {
      alert("فشل حذف المستخدم");
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
        <Users size={24} color="#2196F3" />
        <h2 style={{ margin: 0, fontSize: 20, color: "#fff" }}>إدارة المستخدمين</h2>
      </div>

      {/* Search and Filters */}
      <div style={{ marginBottom: 20, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 200, display: "flex", gap: 10 }}>
          <input
            type="text"
            placeholder="البحث عن مستخدم..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSearch()}
            style={{
              flex: 1,
              padding: "10px 15px",
              background: "#1a1a1a",
              border: "1px solid #333",
              borderRadius: 8,
              color: "#fff",
              fontSize: 14
            }}
          />
          <button
            onClick={handleSearch}
            style={{
              padding: "10px 20px",
              background: "#2196F3",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 5
            }}
          >
            <Search size={16} />
            بحث
          </button>
        </div>
        <button
          onClick={() => { setBlockedOnly(!blockedOnly); setPage(0); }}
          style={{
            padding: "10px 20px",
            background: blockedOnly ? "#f44336" : "#333",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 5
          }}
        >
          <UserX size={16} />
          {blockedOnly ? "الكل" : "المحظورون فقط"}
        </button>
        <button
          onClick={loadUsers}
          disabled={loading}
          style={{
            padding: "10px 20px",
            background: "#4CAF50",
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
        إجمالي المستخدمين: <span style={{ color: "#fff", fontWeight: "bold" }}>{total}</span>
        {" | "}
        الصفحة: <span style={{ color: "#fff", fontWeight: "bold" }}>{page + 1}</span> من{" "}
        <span style={{ color: "#fff", fontWeight: "bold" }}>{Math.ceil(total / limit)}</span>
      </div>

      {/* Users Table */}
      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
          جاري التحميل...
        </div>
      ) : users.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
          لا يوجد مستخدمون
        </div>
      ) : (
        <div style={{
          background: "#1a1a1a",
          borderRadius: 12,
          border: "1px solid #333",
          overflow: "hidden"
        }}>
          {users.map((user, idx) => (
            <div key={user.user_id} style={{
              padding: 15,
              borderBottom: idx < users.length - 1 ? "1px solid #333" : "none",
              display: "flex",
              alignItems: "center",
              gap: 15,
              flexWrap: "wrap"
            }}>
              <div style={{
                width: 50,
                height: 50,
                borderRadius: "50%",
                background: user.is_blocked ? "#f44336" : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
                fontWeight: "bold",
                color: "#fff"
              }}>
                {(user.first_name || user.username || "U")[0].toUpperCase()}
              </div>
              
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={{ fontSize: 14, color: "#fff", marginBottom: 4, display: "flex", alignItems: "center", gap: 8 }}>
                  {user.first_name || user.username || `User ${user.user_id}`}
                  {user.is_blocked === 1 && (
                    <span style={{
                      padding: "2px 8px",
                      background: "#f44336",
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: "bold"
                    }}>
                      محظور
                    </span>
                  )}
                  {user.is_premium === 1 && (
                    <span style={{
                      padding: "2px 8px",
                      background: "#FFD700",
                      color: "#000",
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: "bold"
                    }}>
                      مميز
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: "#999" }}>
                  ID: {user.user_id} | @{user.username || "لا يوجد"}
                </div>
                <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
                  آخر نشاط: {new Date(user.last_active).toLocaleString("ar-DZ")}
                </div>
              </div>

              <div style={{ display: "flex", gap: 8 }}>
                {user.is_blocked === 1 ? (
                  <button
                    onClick={() => handleUnblock(user.user_id)}
                    style={{
                      padding: "8px 12px",
                      background: "#4CAF50",
                      border: "none",
                      borderRadius: 6,
                      color: "#fff",
                      cursor: "pointer",
                      fontSize: 12,
                      display: "flex",
                      alignItems: "center",
                      gap: 5
                    }}
                  >
                    <Unlock size={14} />
                    إلغاء الحظر
                  </button>
                ) : (
                  <button
                    onClick={() => handleBlock(user.user_id)}
                    style={{
                      padding: "8px 12px",
                      background: "#f44336",
                      border: "none",
                      borderRadius: 6,
                      color: "#fff",
                      cursor: "pointer",
                      fontSize: 12,
                      display: "flex",
                      alignItems: "center",
                      gap: 5
                    }}
                  >
                    <Ban size={14} />
                    حظر
                  </button>
                )}
                <button
                  onClick={() => handleDelete(user.user_id)}
                  style={{
                    padding: "8px 12px",
                    background: "#333",
                    border: "none",
                    borderRadius: 6,
                    color: "#fff",
                    cursor: "pointer",
                    fontSize: 12,
                    display: "flex",
                    alignItems: "center",
                    gap: 5
                  }}
                >
                  <Trash2 size={14} />
                  حذف
                </button>
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
