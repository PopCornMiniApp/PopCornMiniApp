import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Sparkles, Star, Calendar, Clock, Play } from 'lucide-react'
import { getBackdropUrl, formatDuration, getRatingColor } from '../utils/helpers'
import { encodeContentUrl } from '../utils/urlEncoder'

export default function HeroSection({ items = [] }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isAutoPlaying, setIsAutoPlaying] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    if (!isAutoPlaying || items.length <= 1) return

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % items.length)
    }, 5000)

    return () => clearInterval(interval)
  }, [isAutoPlaying, items.length])

  if (!items || items.length === 0) return null

  const currentItem = items[currentIndex]

  const handlePrevious = () => {
    setIsAutoPlaying(false)
    setCurrentIndex((prev) => (prev - 1 + items.length) % items.length)
  }

  const handleNext = () => {
    setIsAutoPlaying(false)
    setCurrentIndex((prev) => (prev + 1) % items.length)
  }

  const handleWatch = () => {
    const url = encodeContentUrl(currentItem.type || 'movie', currentItem.id)
    navigate(url)
  }

  const handleDetails = () => {
    const url = encodeContentUrl(currentItem.type || 'movie', currentItem.id)
    navigate(url)
  }

  return (
    <div style={{
      position: 'relative',
      height: '600px',
      marginBottom: 'var(--spacing-xl)',
      overflow: 'hidden',
    }}>
      {/* Background Images with Parallax Effect */}
      {items.map((item, index) => (
        <div
          key={item.id}
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: `url(${getBackdropUrl(item.backdrop_path)})`,
            backgroundSize: 'contain',
            backgroundPosition: 'center top',
            backgroundRepeat: 'no-repeat',
            backgroundColor: 'var(--bg-primary)',
            opacity: index === currentIndex ? 1 : 0,
            transition: 'opacity 1s ease-in-out',
          }}
        >
          {/* Gradient Overlay */}
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(to bottom, rgba(13, 13, 13, 0.3) 0%, rgba(13, 13, 13, 0.7) 50%, var(--bg-primary) 100%)',
          }} />
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(to right, rgba(13, 13, 13, 0.9) 0%, transparent 50%)',
          }} />
        </div>
      ))}

      {/* Content */}
      <div style={{
        position: 'relative',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-end',
        padding: 'var(--spacing-xl) var(--spacing-md) 120px',
        maxWidth: '800px',
      }}>
        {/* Featured Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '12px',
          animation: 'fadeInUp 0.6s ease-out',
        }}>
          <div style={{
            background: 'var(--accent-primary)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-full)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '13px',
            fontWeight: 700,
            boxShadow: '0 4px 12px rgba(245, 158, 11, 0.4)',
          }}>
            <Sparkles size={14} />
            <span>مميز</span>
          </div>
          {currentItem.type && (
            <div style={{
              background: 'rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(10px)',
              padding: '6px 12px',
              borderRadius: 'var(--radius-full)',
              fontSize: '12px',
              fontWeight: 600,
              border: '1px solid rgba(255, 255, 255, 0.2)',
            }}>
              {currentItem.type === 'series' ? 'مسلسل' : 'فيلم'}
            </div>
          )}
        </div>

        {/* Title */}
        <h1 style={{
          fontSize: 'clamp(28px, 5vw, 48px)',
          fontWeight: 800,
          marginBottom: '12px',
          textShadow: '0 4px 12px rgba(0,0,0,0.9)',
          animation: 'fadeInUp 0.6s ease-out 0.1s backwards',
          lineHeight: 1.2,
        }}>
          {currentItem.title_ar || currentItem.title}
        </h1>

        {/* Meta Info */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '16px',
          marginBottom: '16px',
          animation: 'fadeInUp 0.6s ease-out 0.2s backwards',
        }}>
          {currentItem.rating && currentItem.rating > 0 && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '16px',
              fontWeight: 700,
            }}>
              <div style={{
                display: 'flex',
                gap: '2px',
              }}>
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    size={16}
                    fill={i < Math.round(currentItem.rating / 2) ? getRatingColor(currentItem.rating) : 'none'}
                    color={i < Math.round(currentItem.rating / 2) ? getRatingColor(currentItem.rating) : 'var(--text-tertiary)'}
                    style={{
                      animation: `starPop 0.3s ease-out ${i * 0.1}s backwards`,
                    }}
                  />
                ))}
              </div>
              <span style={{ color: getRatingColor(currentItem.rating) }}>
                {currentItem.rating.toFixed(1)}
              </span>
            </div>
          )}
          {currentItem.date && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '14px',
              color: 'var(--text-secondary)',
            }}>
              <Calendar size={16} />
              <span>{new Date(currentItem.date).getFullYear()}</span>
            </div>
          )}
          {currentItem.runtime && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '14px',
              color: 'var(--text-secondary)',
            }}>
              <Clock size={16} />
              <span>{formatDuration(currentItem.runtime)}</span>
            </div>
          )}
        </div>

        {/* Overview */}
        {currentItem.overview_ar && (
          <p style={{
            fontSize: '15px',
            color: 'var(--text-secondary)',
            marginBottom: 'var(--spacing-lg)',
            maxWidth: '600px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            textShadow: '0 2px 8px rgba(0,0,0,0.9)',
            lineHeight: 1.6,
            animation: 'fadeInUp 0.6s ease-out 0.3s backwards',
          }}>
            {currentItem.overview_ar}
          </p>
        )}

        {/* Action Buttons */}
        <div style={{
          display: 'flex',
          gap: 'var(--spacing-md)',
          animation: 'fadeInUp 0.6s ease-out 0.4s backwards',
        }}>
          <button
            onClick={handleWatch}
            style={{
              padding: '14px 32px',
              background: 'var(--accent-primary)',
              borderRadius: 'var(--radius-md)',
              fontSize: '16px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              boxShadow: '0 4px 16px rgba(245, 158, 11, 0.4)',
              transition: 'all var(--transition-base)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(245, 158, 11, 0.6)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 4px 16px rgba(245, 158, 11, 0.4)'
            }}
          >
            <Play size={20} fill="white" />
            <span>شاهد الآن</span>
          </button>

          <button
            onClick={handleDetails}
            style={{
              padding: '14px 32px',
              background: 'rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(10px)',
              borderRadius: 'var(--radius-md)',
              fontSize: '16px',
              fontWeight: 600,
              border: '2px solid rgba(255, 255, 255, 0.3)',
              transition: 'all var(--transition-base)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)'
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.5)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.3)'
            }}
          >
            المزيد من التفاصيل
          </button>
        </div>
      </div>

      {/* Navigation Arrows */}
      {items.length > 1 && (
        <>
          <button
            onClick={handleNext}
            style={{
              position: 'absolute',
              left: 'var(--spacing-md)',
              bottom: '60px',
              background: 'rgba(0, 0, 0, 0.7)',
              backdropFilter: 'blur(10px)',
              padding: '12px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all var(--transition-base)',
              border: '2px solid rgba(255, 255, 255, 0.2)',
              zIndex: 10,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(0, 0, 0, 0.9)'
              e.currentTarget.style.borderColor = 'var(--accent-primary)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(0, 0, 0, 0.7)'
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'
            }}
          >
            <ChevronLeft size={24} />
          </button>

          <button
            onClick={handlePrevious}
            style={{
              position: 'absolute',
              left: '70px',
              bottom: '60px',
              background: 'rgba(0, 0, 0, 0.7)',
              backdropFilter: 'blur(10px)',
              padding: '12px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all var(--transition-base)',
              border: '2px solid rgba(255, 255, 255, 0.2)',
              zIndex: 10,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(0, 0, 0, 0.9)'
              e.currentTarget.style.borderColor = 'var(--accent-primary)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(0, 0, 0, 0.7)'
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'
            }}
          >
            <ChevronRight size={24} />
          </button>
        </>
      )}

      {/* Indicators */}
      {items.length > 1 && (
        <div style={{
          position: 'absolute',
          bottom: 'var(--spacing-lg)',
          right: 'var(--spacing-md)',
          display: 'flex',
          gap: '8px',
        }}>
          {items.map((_, index) => (
            <button
              key={index}
              onClick={() => {
                setIsAutoPlaying(false)
                setCurrentIndex(index)
              }}
              style={{
                width: index === currentIndex ? '32px' : '8px',
                height: '8px',
                borderRadius: 'var(--radius-full)',
                background: index === currentIndex ? 'var(--accent-primary)' : 'rgba(255, 255, 255, 0.3)',
                transition: 'all var(--transition-base)',
                border: 'none',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                if (index !== currentIndex) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.5)'
                }
              }}
              onMouseLeave={(e) => {
                if (index !== currentIndex) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.3)'
                }
              }}
            />
          ))}
        </div>
      )}

      {/* CSS Animations */}
      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }


        @keyframes starPop {
          0% {
            transform: scale(0);
            opacity: 0;
          }
          50% {
            transform: scale(1.2);
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  )
}

// Made with Bob