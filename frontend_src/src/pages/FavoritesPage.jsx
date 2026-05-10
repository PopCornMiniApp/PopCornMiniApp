import React from 'react'
import { Heart, Trash2 } from 'lucide-react'
import { useStore } from '../store/useStore'
import ContentCard from '../components/ContentCard'
import { hapticFeedback } from '../utils/helpers'

export default function FavoritesPage() {
  const { favorites, removeFavorite } = useStore()

  const handleRemove = (id, e) => {
    e.stopPropagation()
    hapticFeedback('light')
    if (confirm('هل تريد إزالة هذا العنصر من المفضلة؟')) {
      removeFavorite(id)
    }
  }

  return (
    <div style={{ paddingBottom: '80px' }}>
      {/* Header */}
      <header style={{
        padding: 'var(--spacing-lg) var(--spacing-md)',
        background: 'var(--bg-secondary)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <Heart size={24} color="var(--accent-primary)" fill="var(--accent-primary)" />
          <h1 style={{ fontSize: '24px', fontWeight: 700 }}>المفضلة</h1>
        </div>
        {favorites.length > 0 && (
          <p style={{
            color: 'var(--text-secondary)',
            fontSize: '14px',
            marginTop: '8px',
          }}>
            {favorites.length} عنصر
          </p>
        )}
      </header>

      {/* Content */}
      <div style={{ padding: 'var(--spacing-md)' }}>
        {favorites.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
          }}>
            <div style={{
              fontSize: '64px',
              marginBottom: 'var(--spacing-md)',
              opacity: 0.5,
            }}>
              💔
            </div>
            <h2 style={{
              fontSize: '20px',
              fontWeight: 600,
              marginBottom: '8px',
            }}>
              لا توجد عناصر في المفضلة
            </h2>
            <p style={{
              color: 'var(--text-secondary)',
              fontSize: '14px',
            }}>
              ابدأ بإضافة أفلامك ومسلسلاتك المفضلة
            </p>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
            gap: 'var(--spacing-md)',
          }}>
            {favorites.map((item) => (
              <div key={item.id} style={{ position: 'relative' }}>
                <ContentCard item={item} showType />
                <button
                  onClick={(e) => handleRemove(item.id, e)}
                  style={{
                    position: 'absolute',
                    top: '8px',
                    left: '8px',
                    padding: '6px',
                    background: 'rgba(0, 0, 0, 0.8)',
                    backdropFilter: 'blur(8px)',
                    borderRadius: 'var(--radius-full)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 10,
                  }}
                >
                  <Trash2 size={14} color="#ef4444" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Made with Bob
