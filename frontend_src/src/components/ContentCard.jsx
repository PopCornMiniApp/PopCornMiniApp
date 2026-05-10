import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Star, Play, Clock } from 'lucide-react'
import { encodeContentUrl } from '../utils/urlEncoder'
import { getPosterUrl, formatRating, getRatingColor } from '../utils/helpers'

export default function ContentCard({ item, showType = false, showProgress = false }) {
  const navigate = useNavigate()
  const [imageLoaded, setImageLoaded] = useState(false)
  const [isHovered, setIsHovered] = useState(false)

  // Guard clause - if item is null/undefined, return null
  if (!item) return null

  const handleClick = () => {
    const url = encodeContentUrl(item?.type || 'movie', item?.id)
    navigate(url)
  }

  // Get quality badge
  const getQualityBadge = () => {
    if (item?.quality) return item.quality
    if (item?.rating >= 8) return '4K'
    if (item?.rating >= 7) return 'HD'
    return 'SD'
  }

  return (
    <div
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        cursor: 'pointer',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        background: 'var(--bg-secondary)',
        transition: 'all var(--transition-base)',
        position: 'relative',
        transform: isHovered ? 'translateY(-8px) scale(1.03)' : 'translateY(0) scale(1)',
        boxShadow: isHovered
          ? '0 12px 24px rgba(0, 0, 0, 0.6), 0 0 0 2px var(--accent-primary)'
          : '0 2px 8px rgba(0, 0, 0, 0.3)',
      }}
    >
      {/* Poster */}
      <div style={{ position: 'relative', overflow: 'hidden' }}>
        {/* Skeleton Loader */}
        {!imageLoaded && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(90deg, var(--bg-tertiary) 0%, var(--bg-secondary) 50%, var(--bg-tertiary) 100%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.5s infinite',
          }} />
        )}

        <img
          src={getPosterUrl(item?.poster_path)}
          alt={item?.title || item?.title_ar || item?.name}
          onLoad={() => setImageLoaded(true)}
          style={{
            width: '100%',
            aspectRatio: '2/3',
            objectFit: 'cover',
            background: 'var(--bg-tertiary)',
            opacity: imageLoaded ? 1 : 0,
            transition: 'opacity 0.3s ease-in',
          }}
          loading="lazy"
        />
        
        {/* Quality Badge */}
        <div style={{
          position: 'absolute',
          top: '8px',
          left: '8px',
          background: 'rgba(0, 0, 0, 0.9)',
          backdropFilter: 'blur(10px)',
          padding: '4px 10px',
          borderRadius: 'var(--radius-sm)',
          fontSize: '11px',
          fontWeight: 700,
          color: 'var(--accent-primary)',
          border: '1px solid var(--accent-primary)',
          boxShadow: '0 2px 8px rgba(245, 158, 11, 0.3)',
        }}>
          {getQualityBadge()}
        </div>

        {/* Rating Badge */}
        {item?.rating && item.rating > 0 && (
          <div style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            background: 'rgba(0, 0, 0, 0.9)',
            backdropFilter: 'blur(10px)',
            padding: '4px 8px',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '12px',
            fontWeight: 700,
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.5)',
          }}>
            <Star
              size={12}
              fill={getRatingColor(item?.rating)}
              color={getRatingColor(item?.rating)}
              style={{
                animation: isHovered ? 'starRotate 0.5s ease-in-out' : 'none',
              }}
            />
            <span style={{ color: getRatingColor(item?.rating) }}>
              {item?.rating?.toFixed(1)}
            </span>
          </div>
        )}

        {/* Year Badge */}
        {item?.date && (
          <div style={{
            position: 'absolute',
            bottom: '8px',
            left: '8px',
            background: 'rgba(0, 0, 0, 0.9)',
            backdropFilter: 'blur(10px)',
            padding: '4px 8px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--text-secondary)',
          }}>
            {new Date(item?.date).getFullYear()}
          </div>
        )}

        {/* Play Overlay with Info */}
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(to top, rgba(0, 0, 0, 0.95) 0%, rgba(0, 0, 0, 0.7) 50%, transparent 100%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: isHovered ? 1 : 0,
          transition: 'opacity var(--transition-base)',
          padding: 'var(--spacing-md)',
        }}>
          <div style={{
            background: 'var(--accent-primary)',
            borderRadius: 'var(--radius-full)',
            padding: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 'var(--spacing-sm)',
            boxShadow: '0 4px 16px rgba(245, 158, 11, 0.5)',
            transform: isHovered ? 'scale(1)' : 'scale(0.8)',
            transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
          }}>
            <Play size={28} fill="white" color="white" />
          </div>

          {/* Additional Info on Hover */}
          {item?.genres && item.genres.length > 0 && (
            <div style={{
              fontSize: '11px',
              color: 'var(--text-secondary)',
              textAlign: 'center',
              maxWidth: '100%',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {item.genres.slice(0, 2).join(' • ')}
            </div>
          )}
        </div>

        {/* Progress Bar for Watched Content */}
        {showProgress && item?.progress && (
          <div style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: '4px',
            background: 'rgba(255, 255, 255, 0.2)',
          }}>
            <div style={{
              height: '100%',
              width: `${item?.progress}%`,
              background: 'var(--accent-primary)',
              transition: 'width 0.3s ease',
            }} />
          </div>
        )}
      </div>

      {/* Info */}
      <div style={{
        padding: 'var(--spacing-sm)',
        background: isHovered ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
        transition: 'background var(--transition-base)',
      }}>
        <h3 style={{
          fontSize: '14px',
          fontWeight: 600,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          marginBottom: '6px',
          color: isHovered ? 'var(--accent-primary)' : 'var(--text-primary)',
          transition: 'color var(--transition-base)',
        }}>
          {item?.title_ar || item?.title || item?.name}
        </h3>
        
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '12px',
          color: 'var(--text-secondary)',
        }}>
          {showType && item?.type && (
            <>
              <span style={{
                color: 'var(--accent-primary)',
                fontWeight: 600,
              }}>
                {item?.type === 'series' ? 'مسلسل' : 'فيلم'}
              </span>
              <span>•</span>
            </>
          )}
          {item?.runtime && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Clock size={12} />
                <span>{Math.floor(item?.runtime / 60)}س</span>
              </div>
              {item?.genres && item.genres.length > 0 && <span>•</span>}
            </>
          )}
          {item?.genres && item.genres.length > 0 && (
            <span style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
            }}>
              {item?.genres?.[0]}
            </span>
          )}
        </div>
      </div>

      {/* CSS Animations */}
      <style>{`
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }

        @keyframes starRotate {
          0%, 100% {
            transform: rotate(0deg);
          }
          50% {
            transform: rotate(180deg);
          }
        }
      `}</style>
    </div>
  )
}

// Made with Bob
