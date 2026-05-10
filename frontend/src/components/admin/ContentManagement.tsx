import { useState, useEffect } from "react";
import { Film, Tv, Search, Trash2, RefreshCw, Play } from "lucide-react";

interface ContentManagementProps {
  adminApi: any;
}

interface ContentItem {
  id: string;
  tmdb_id: number;
  title: string;
  title_ar: string;
  poster_path: string;
  release_date?: string;
  first_air_date?: string;
  rating: number;
  has_file: boolean;
  file_id?: string;
  total_seasons?: number;
}

export default function ContentManagement({ adminApi }: ContentManagementProps) {
  const [contentType, setContentType] = useState<"movie" | "series">("movie");
  const [items, setItems] = useState<ContentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [scanning, setScanning] = useState(false);
  const limit = 20;

  useEffect(() => {
    loadContent();
  }, [page, contentType]);

  const loadContent = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getContent({
        content_type: contentType,
        limit,
        offset: page * limit,
        search: search || undefined
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error("Failed to load content:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(0);
    loadContent();
  };

  const handleDelete = async (id: string, title: string) => {
    if (!confirm(`⚠️ هل أنت متأكد من حذف "${title}"؟ هذا الإجراء لا يمكن التراجع عنه!`)) return;
    try {
      await adminApi.deleteContent(contentType, id);
      loadContent();
    } catch (error) {
      alert("فشل حذف المحتوى");
    }
  };

  const handleFullScan = async () => {
    if (!confirm("هل تريد بدء مسح شامل للمجموعة؟ قد يستغرق هذا عدة دقائق.")) return;
    try {
      setScanning(true);
      const result = await adminApi.triggerFullScan();
      alert(`✅ اكتمل المسح!\n\nمواضيع: ${result.scan.topics_scanned}\nجديد: ${result.scan.registered}\nملفات: ${result.scan.files_attached}\nأخطاء: ${result.scan.errors}`);
      loadContent();
    } catch (error) {
      alert("فشل المسح الشامل");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
        {contentType === "movie" ? <Film size={24} color="#2196F3" /> : <Tv size={24} color="#9C27B0" />}
        <h2 style={{ margin: 0, fontSize: 20, color: "#fff" }}>إدارة المحتوى</h2>
      </div>

      {/* Type Selector */}
      <div style={{ marginBottom: 20, display: "flex", gap: 10 }}>
        <button
          onClick={() => { setContentType("movie"); setPage(0); }}
          style={{
            padding: "10px 20px",
            background: contentType === "movie" ? "#2196F3" : "#333",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 5,
            fontWeight: contentType === "movie" ? "bold" : "normal"
          }}
        >
          <Film size={16} />
          الأفلام
        </button>
        <button
          onClick={() => { setContentType("series"); setPage(0); }}
          style={{
            padding: "10px 20px",
            background: contentType === "series" ? "#9C27B0" : "#333",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 5,
            fontWeight: contentType === "series" ? "bold" : "normal"
          }}
        >
          <Tv size={16} />
          المسلسلات
        </button>
      </div>

      {/* Search and Actions */}
      <div style={{ marginBottom: 20, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 200, display: "flex", gap: 10 }}>
          <input
            type="text"
            placeholder="البحث عن محتوى..."
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
          onClick={loadContent}
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
        <button
          onClick={handleFullScan}
          disabled={scanning}
          style={{
            padding: "10px 20px",
            background: "#FF9800",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            cursor: scanning ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: 5,
            opacity: scanning ? 0.6 : 1
          }}
        >
          <Play size={16} />
          {scanning ? "جاري المسح..." : "مسح شامل"}
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
        إجمالي {contentType === "movie" ? "الأفلام" : "المسلسلات"}: <span style={{ color: "#fff", fontWeight: "bold" }}>{total}</span>
        {" | "}
        الصفحة: <span style={{ color: "#fff", fontWeight: "bold" }}>{page + 1}</span> من{" "}
        <span style={{ color: "#fff", fontWeight: "bold" }}>{Math.ceil(total / limit)}</span>
      </div>

      {/* Content Grid */}
      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
          جاري التحميل...
        </div>
      ) : items.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
          لا يوجد محتوى
        </div>
      ) : (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
          gap: 15
        }}>
          {items.map((item) => (
            <div key={item.id} style={{
              background: "#1a1a1a",
              borderRadius: 12,
              border: "1px solid #333",
              overflow: "hidden",
              position: "relative"
            }}>
              {/* Poster */}
              <div style={{
                width: "100%",
                paddingTop: "150%",
                background: item.poster_path
                  ? `url(https://image.tmdb.org/t/p/w300${item.poster_path})`
                  : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                backgroundSize: "cover",
                backgroundPosition: "center",
                position: "relative"
              }}>
                {/* Status Badge */}
                <div style={{
                  position: "absolute",
                  top: 8,
                  right: 8,
                  padding: "4px 8px",
                  background: item.has_file ? "#4CAF50" : "#f44336",
                  borderRadius: 4,
                  fontSize: 10,
                  fontWeight: "bold",
                  color: "#fff"
                }}>
                  {item.has_file ? "متوفر" : "غير متوفر"}
                </div>
                
                {/* Rating */}
                {item.rating > 0 && (
                  <div style={{
                    position: "absolute",
                    bottom: 8,
                    left: 8,
                    padding: "4px 8px",
                    background: "rgba(0,0,0,0.8)",
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: "bold",
                    color: "#FFD700"
                  }}>
                    ⭐ {item.rating.toFixed(1)}
                  </div>
                )}
              </div>

              {/* Info */}
              <div style={{ padding: 10 }}>
                <div style={{
                  fontSize: 12,
                  color: "#fff",
                  marginBottom: 4,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontWeight: "bold"
                }}>
                  {item.title_ar || item.title}
                </div>
                <div style={{
                  fontSize: 10,
                  color: "#999",
                  marginBottom: 8,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap"
                }}>
                  {item.title}
                </div>
                <div style={{ fontSize: 10, color: "#666", marginBottom: 8 }}>
                  {contentType === "movie" 
                    ? item.release_date?.split("-")[0] || "N/A"
                    : `${item.total_seasons || 0} مواسم`
                  }
                </div>
                
                {/* Delete Button */}
                <button
                  onClick={() => handleDelete(item.id, item.title_ar || item.title)}
                  style={{
                    width: "100%",
                    padding: "8px",
                    background: "#f44336",
                    border: "none",
                    borderRadius: 6,
                    color: "#fff",
                    cursor: "pointer",
                    fontSize: 11,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 5
                  }}
                >
                  <Trash2 size={12} />
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
