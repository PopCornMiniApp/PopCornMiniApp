import React from 'react'
import { Clock, Trash2 } from 'lucide-react'
import { useStore } from '../store/useStore'
import { storage } from '../utils/api'
import ContentCard from '../components/ContentCard'
import { formatRelativeTime, hapticFeedback } from '../utils/helpers'

export default function HistoryPage() {
  const { history, clearHistory } = useStore()

  const handleClearAll = () => {
    hapticFeedback('medium')
    if (confirm('هل تريد مسح سجل المشاهدة بالكامل؟')) {
      clearHistory()
    }
  }

  const getProgress = (itemId) => {
    const progress = storage.getProgress(itemId)
    return progress ? progress.percentage : 0
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
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <Clock size={24} color="var(--accent-primary)" />
            <h1 style={{ fontSize: '24px', fontWeight: 700 }}>سجل المشاهدة</h1>
          </div>
          {history.length > 0 && (
            <button
              onClick={handleClearAll}
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: '#ef4444',
              }}
            >
              <Trash2 size={16} />
              <span>مسح الكل</span>
            </button>
          )}
        </div>
        {history.length > 0 && (
          <p style={{
            color: 'var(--text-secondary)',
            fontSize: '14px',
            marginTop: '8px',
          }}>
            {history.length} عنصر
          </p>
        )}
      </header>

      {/* Content */}
      <div style={{ padding: 'var(--spacing-md)' }}>
        {history.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
          }}>
            <div style={{
              fontSize: '64px',
              marginBottom: 'var(--spacing-md)',
              opacity: 0.5,
            }}>
              ⏰
            </div>
            <h2 style={{
              fontSize: '20px',
              fontWeight: 600,
              marginBottom: '8px',
            }}>
              لا يوجد سجل مشاهدة
            </h2>
            <p style={{
              color: 'var(--text-secondary)',
              fontSize: '14px',
            }}>
              ابدأ بمشاهدة الأفلام والمسلسلات
            </p>
          </div>
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--spacing-md)',
          }}>
            {history.map((item) => {
              const progress = getProgress(item.id)
              return (
                <div
                  key={item.id}
                  style={{
                    display: 'flex',
                    gap: 'var(--spacing-md)',
                    background: 'var(--bg-secondary)',
                    borderRadius: 'var(--radius-md)',
                    overflow: 'hidden',
                    position: 'relative',
                  }}
                >
                  {/* Poster */}
                  <div style={{
                    width: '100px',
                    flexShrink: 0,
                    position: 'relative',
                  }}>
                    <ContentCard item={item} />
                  </div>

                  {/* Info */}
                  <div style={{
                    flex: 1,
                    padding: 'var(--spacing-sm) var(--spacing-sm) var(--spacing-sm) 0',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}>
                    <div>
                      <h3 style={{
                        fontSize: '16px',
                        fontWeight: 600,
                        marginBottom: '4px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {item.title_ar || item.title}
                      </h3>
                      <p style={{
                        fontSize: '12px',
                        color: 'var(--text-secondary)',
                        marginBottom: '8px',
                      }}>
                        {item.watchedAt && formatRelativeTime(item.watchedAt)}
                      </p>
                    </div>

                    {/* Progress Bar */}
                    {progress > 0 && (
                      <div>
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: '4px',
                        }}>
                          <span style={{
                            fontSize: '12px',
                            color: 'var(--text-secondary)',
                          }}>
                            التقدم
                          </span>
                          <span style={{
                            fontSize: '12px',
                            fontWeight: 600,
                            color: 'var(--accent-primary)',
                          }}>
                            {Math.round(progress)}%
                          </span>
                        </div>
                        <div style={{
                          width: '100%',
                          height: '4px',
                          background: 'var(--bg-tertiary)',
                          borderRadius: '2px',
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            width: `${progress}%`,
                            height: '100%',
                            background: 'var(--accent-primary)',
                            borderRadius: '2px',
                            transition: 'width 0.3s ease',
                          }} />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// Made with Bob
