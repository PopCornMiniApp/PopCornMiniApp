import React, { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowRight, Play, Pause, Volume2, VolumeX, Maximize, Minimize } from 'lucide-react'
import { decodeContentUrl } from '../utils/urlEncoder'
import { api, storage } from '../utils/api'
import { hapticFeedback } from '../utils/helpers'

export default function WatchPage() {
  const { encodedId } = useParams()
  const navigate = useNavigate()
  const videoRef = useRef(null)
  const containerRef = useRef(null)
  
  const [content, setContent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [showControls, setShowControls] = useState(true)
  const [buffering, setBuffering] = useState(false)

  useEffect(() => {
    loadContent()
    
    // Hide controls after 3 seconds of inactivity
    let timeout
    const handleActivity = () => {
      setShowControls(true)
      clearTimeout(timeout)
      timeout = setTimeout(() => {
        if (playing) setShowControls(false)
      }, 3000)
    }

    document.addEventListener('mousemove', handleActivity)
    document.addEventListener('touchstart', handleActivity)

    return () => {
      document.removeEventListener('mousemove', handleActivity)
      document.removeEventListener('touchstart', handleActivity)
      clearTimeout(timeout)
    }
  }, [encodedId, playing])

  const loadContent = async () => {
    try {
      const decoded = decodeContentUrl(encodedId)
      if (!decoded) {
        navigate('/')
        return
      }

      const data = decoded.type === 'movie'
        ? await api.getMovie(decoded.id)
        : await api.getSeriesDetail(decoded.id)

      setContent(data)
      
      // Add to history
      storage.addToHistory(data)
      
      // Load saved progress
      const progress = storage.getProgress(data.id)
      if (progress && videoRef.current) {
        videoRef.current.currentTime = progress.currentTime
      }
    } catch (error) {
      console.error('Failed to load content:', error)
      navigate('/')
    } finally {
      setLoading(false)
    }
  }

  const togglePlay = () => {
    if (!videoRef.current) return
    
    hapticFeedback('light')
    if (playing) {
      videoRef.current.pause()
    } else {
      videoRef.current.play()
    }
    setPlaying(!playing)
  }

  const toggleMute = () => {
    if (!videoRef.current) return
    
    hapticFeedback('light')
    videoRef.current.muted = !muted
    setMuted(!muted)
  }

  const toggleFullscreen = async () => {
    if (!containerRef.current) return
    
    hapticFeedback('medium')
    try {
      if (!fullscreen) {
        if (containerRef.current.requestFullscreen) {
          await containerRef.current.requestFullscreen()
        } else if (containerRef.current.webkitRequestFullscreen) {
          await containerRef.current.webkitRequestFullscreen()
        }
        setFullscreen(true)
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen()
        } else if (document.webkitExitFullscreen) {
          await document.webkitExitFullscreen()
        }
        setFullscreen(false)
      }
    } catch (error) {
      console.error('Fullscreen error:', error)
    }
  }

  const handleTimeUpdate = () => {
    if (!videoRef.current) return
    
    const current = videoRef.current.currentTime
    const total = videoRef.current.duration
    
    setCurrentTime(current)
    setDuration(total)
    
    // Save progress every 5 seconds
    if (content && Math.floor(current) % 5 === 0) {
      storage.saveProgress(content.id, current, total)
    }
  }

  const handleSeek = (e) => {
    if (!videoRef.current) return
    
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = x / rect.width
    const time = percentage * duration
    
    videoRef.current.currentTime = time
    setCurrentTime(time)
  }

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00'
    
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    
    if (h > 0) {
      return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    }
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'black',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontSize: '48px',
            marginBottom: '16px',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}>
            🍿
          </div>
          <p style={{ color: 'white' }}>جاري التحميل...</p>
        </div>
      </div>
    )
  }

  if (!content) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'black',
        padding: 'var(--spacing-md)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: '48px', marginBottom: '16px' }}>😕</p>
          <p style={{ color: 'white', marginBottom: 'var(--spacing-md)' }}>
            المحتوى غير موجود
          </p>
          <button
            onClick={() => navigate('/')}
            style={{
              padding: 'var(--spacing-sm) var(--spacing-md)',
              background: 'var(--accent-primary)',
              borderRadius: 'var(--radius-md)',
              color: 'white',
            }}
          >
            العودة للرئيسية
          </button>
        </div>
      </div>
    )
  }

  const streamUrl = api.getStreamUrl(content.id)

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100vh',
        background: 'black',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Video Player */}
      <div style={{
        position: 'relative',
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <video
          ref={videoRef}
          src={streamUrl}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
          }}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={() => setDuration(videoRef.current?.duration || 0)}
          onWaiting={() => setBuffering(true)}
          onCanPlay={() => setBuffering(false)}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onClick={togglePlay}
        />

        {/* Buffering Indicator */}
        {buffering && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(0,0,0,0.5)',
          }}>
            <div style={{
              fontSize: '48px',
              animation: 'pulse 1.5s ease-in-out infinite',
            }}>
              ⏳
            </div>
          </div>
        )}

        {/* Controls Overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: showControls
              ? 'linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, transparent 20%, transparent 80%, rgba(0,0,0,0.7) 100%)'
              : 'transparent',
            transition: 'background 0.3s ease',
            pointerEvents: showControls ? 'auto' : 'none',
          }}
        >
          {/* Top Bar */}
          {showControls && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              padding: 'var(--spacing-md)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-md)',
            }}>
              <button
                onClick={() => navigate(-1)}
                style={{
                  padding: 'var(--spacing-sm)',
                  borderRadius: 'var(--radius-full)',
                  background: 'rgba(0,0,0,0.5)',
                  backdropFilter: 'blur(8px)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <ArrowRight size={20} color="white" />
              </button>
              <div style={{ flex: 1 }}>
                <h1 style={{
                  fontSize: '16px',
                  fontWeight: 600,
                  color: 'white',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {content.title_ar || content.title}
                </h1>
              </div>
            </div>
          )}

          {/* Center Play Button */}
          {!playing && showControls && (
            <div style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <button
                onClick={togglePlay}
                style={{
                  padding: '20px',
                  borderRadius: 'var(--radius-full)',
                  background: 'rgba(255,255,255,0.2)',
                  backdropFilter: 'blur(8px)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Play size={48} fill="white" color="white" />
              </button>
            </div>
          )}

          {/* Bottom Controls */}
          {showControls && (
            <div style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              padding: 'var(--spacing-md)',
            }}>
              {/* Progress Bar */}
              <div
                onClick={handleSeek}
                style={{
                  width: '100%',
                  height: '4px',
                  background: 'rgba(255,255,255,0.3)',
                  borderRadius: '2px',
                  marginBottom: 'var(--spacing-sm)',
                  cursor: 'pointer',
                  position: 'relative',
                }}
              >
                <div style={{
                  width: `${(currentTime / duration) * 100}%`,
                  height: '100%',
                  background: 'var(--accent-primary)',
                  borderRadius: '2px',
                }} />
              </div>

              {/* Control Buttons */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-md)',
              }}>
                <button onClick={togglePlay} style={{ padding: '8px' }}>
                  {playing ? (
                    <Pause size={24} color="white" />
                  ) : (
                    <Play size={24} fill="white" color="white" />
                  )}
                </button>

                <button onClick={toggleMute} style={{ padding: '8px' }}>
                  {muted ? (
                    <VolumeX size={24} color="white" />
                  ) : (
                    <Volume2 size={24} color="white" />
                  )}
                </button>

                <span style={{
                  fontSize: '14px',
                  color: 'white',
                  fontWeight: 500,
                }}>
                  {formatTime(currentTime)} / {formatTime(duration)}
                </span>

                <div style={{ flex: 1 }} />

                <button onClick={toggleFullscreen} style={{ padding: '8px' }}>
                  {fullscreen ? (
                    <Minimize size={24} color="white" />
                  ) : (
                    <Maximize size={24} color="white" />
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Made with Bob
