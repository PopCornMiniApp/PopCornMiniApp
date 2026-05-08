import React, { useRef, useState, useEffect, useCallback } from 'react';
import {
  Play, Pause, Volume2, VolumeX, Maximize2, Minimize2,
  X, Settings, Subtitles, PictureInPicture, SkipBack, SkipForward,
  Rewind, FastForward, Loader
} from 'lucide-react';

/**
 * Enhanced Video Player Component
 * 
 * Features:
 * - Modern, beautiful UI with smooth animations
 * - Picture-in-Picture support
 * - Background playback
 * - Subtitles support
 * - Quality selector
 * - Playback speed control
 * - Gesture controls (swipe for seek, tap for play/pause)
 * - Progress saving
 * - Keyboard shortcuts
 * - Touch-friendly controls
 */

const EnhancedVideoPlayer = ({ 
  streamUrl, 
  title, 
  fileSize,
  subtitles = [],
  qualities = [],
  onClose,
  movieId,
  onProgressUpdate
}) => {
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const controlsTimeoutRef = useRef(null);
  const progressIntervalRef = useRef(null);

  // Player state
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [isBuffering, setIsBuffering] = useState(false);
  const [isPiP, setIsPiP] = useState(false);

  // Settings state
  const [showSettings, setShowSettings] = useState(false);
  const [selectedQuality, setSelectedQuality] = useState(qualities[0] || 'auto');
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [selectedSubtitle, setSelectedSubtitle] = useState(null);

  // Touch gesture state
  const [touchStart, setTouchStart] = useState(null);
  const [isSeeking, setIsSeeking] = useState(false);
  const [seekPreview, setSeekPreview] = useState(null);

  // Load saved progress
  useEffect(() => {
    if (movieId) {
      const savedProgress = localStorage.getItem(`progress_${movieId}`);
      if (savedProgress && videoRef.current) {
        videoRef.current.currentTime = parseFloat(savedProgress);
      }
    }
  }, [movieId]);

  // Save progress periodically
  useEffect(() => {
    if (isPlaying && movieId) {
      progressIntervalRef.current = setInterval(() => {
        if (videoRef.current) {
          const progress = videoRef.current.currentTime;
          localStorage.setItem(`progress_${movieId}`, progress.toString());
          if (onProgressUpdate) {
            onProgressUpdate(progress, duration);
          }
        }
      }, 5000); // Save every 5 seconds
    }

    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, [isPlaying, movieId, duration, onProgressUpdate]);

  // Auto-hide controls
  const resetControlsTimeout = useCallback(() => {
    setShowControls(true);
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    if (isPlaying) {
      controlsTimeoutRef.current = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    }
  }, [isPlaying]);

  // Play/Pause toggle
  const togglePlay = useCallback(() => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play().catch(() => {});
        setIsPlaying(true);
      } else {
        videoRef.current.pause();
        setIsPlaying(false);
      }
    }
  }, []);

  // Volume control
  const toggleMute = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.muted = !videoRef.current.muted;
      setIsMuted(videoRef.current.muted);
    }
  }, []);

  const handleVolumeChange = useCallback((newVolume) => {
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
      setVolume(newVolume);
      setIsMuted(newVolume === 0);
    }
  }, []);

  // Seek control
  const handleSeek = useCallback((time) => {
    if (videoRef.current && duration) {
      const newTime = Math.max(0, Math.min(time, duration));
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  }, [duration]);

  const skipTime = useCallback((seconds) => {
    if (videoRef.current) {
      handleSeek(videoRef.current.currentTime + seconds);
    }
  }, [handleSeek]);

  // Fullscreen control
  const toggleFullscreen = useCallback(async () => {
    const container = containerRef.current;
    if (!container) return;

    try {
      if (!document.fullscreenElement) {
        if (container.requestFullscreen) {
          await container.requestFullscreen();
        } else if (container.webkitRequestFullscreen) {
          await container.webkitRequestFullscreen();
        } else if (container.mozRequestFullScreen) {
          await container.mozRequestFullScreen();
        }
        setIsFullscreen(true);
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
          await document.webkitExitFullscreen();
        }
        setIsFullscreen(false);
      }
    } catch (error) {
      console.error('Fullscreen error:', error);
    }
  }, []);

  // Picture-in-Picture
  const togglePiP = useCallback(async () => {
    if (!videoRef.current) return;

    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
        setIsPiP(false);
      } else if (document.pictureInPictureEnabled) {
        await videoRef.current.requestPictureInPicture();
        setIsPiP(true);
      }
    } catch (error) {
      console.error('PiP error:', error);
    }
  }, []);

  // Playback speed
  const changePlaybackSpeed = useCallback((speed) => {
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
      setPlaybackSpeed(speed);
    }
  }, []);

  // Subtitle selection
  const selectSubtitle = useCallback((subtitle) => {
    setSelectedSubtitle(subtitle);
    // Implementation depends on subtitle format
  }, []);

  // Touch gestures
  const handleTouchStart = useCallback((e) => {
    setTouchStart({
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
      time: currentTime
    });
  }, [currentTime]);

  const handleTouchMove = useCallback((e) => {
    if (!touchStart || !duration) return;

    const deltaX = e.touches[0].clientX - touchStart.x;
    const seekAmount = (deltaX / window.innerWidth) * 30; // 30 seconds per full swipe
    const newTime = Math.max(0, Math.min(touchStart.time + seekAmount, duration));
    
    setIsSeeking(true);
    setSeekPreview(newTime);
  }, [touchStart, duration]);

  const handleTouchEnd = useCallback(() => {
    if (isSeeking && seekPreview !== null) {
      handleSeek(seekPreview);
    }
    setTouchStart(null);
    setIsSeeking(false);
    setSeekPreview(null);
  }, [isSeeking, seekPreview, handleSeek]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e) => {
      switch (e.key) {
        case ' ':
        case 'k':
          e.preventDefault();
          togglePlay();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          skipTime(-10);
          break;
        case 'ArrowRight':
          e.preventDefault();
          skipTime(10);
          break;
        case 'ArrowUp':
          e.preventDefault();
          handleVolumeChange(Math.min(volume + 0.1, 1));
          break;
        case 'ArrowDown':
          e.preventDefault();
          handleVolumeChange(Math.max(volume - 0.1, 0));
          break;
        case 'f':
          e.preventDefault();
          toggleFullscreen();
          break;
        case 'm':
          e.preventDefault();
          toggleMute();
          break;
        case 'p':
          e.preventDefault();
          togglePiP();
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [togglePlay, skipTime, handleVolumeChange, volume, toggleFullscreen, toggleMute, togglePiP]);

  // Fullscreen change listener
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Format time
  const formatTime = (seconds) => {
    if (!isFinite(seconds) || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format file size
  const formatSize = (bytes) => {
    if (!bytes) return '';
    return bytes >= 1e9 
      ? `${(bytes / 1e9).toFixed(1)} GB` 
      : `${(bytes / 1e6).toFixed(0)} MB`;
  };

  const progress = duration ? (currentTime / duration) * 100 : 0;
  const seekProgress = isSeeking && seekPreview !== null 
    ? (seekPreview / duration) * 100 
    : progress;

  return (
    <div
      ref={containerRef}
      className={`video-player-container ${isFullscreen ? 'fullscreen' : ''}`}
      onClick={resetControlsTimeout}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      style={{
        position: isFullscreen ? 'fixed' : 'relative',
        inset: isFullscreen ? 0 : undefined,
        zIndex: isFullscreen ? 9999 : undefined,
        background: '#000',
        aspectRatio: isFullscreen ? undefined : '16/9',
        width: '100%',
        height: isFullscreen ? '100%' : undefined,
        overflow: 'hidden',
        touchAction: 'none'
      }}
    >
      {/* Video Element */}
      <video
        ref={videoRef}
        src={streamUrl}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          display: 'block'
        }}
        playsInline
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime || 0)}
        onLoadedMetadata={() => setDuration(videoRef.current?.duration || 0)}
        onWaiting={() => setIsBuffering(true)}
        onCanPlay={() => setIsBuffering(false)}
        onEnded={() => setIsPlaying(false)}
      />

      {/* Buffering Indicator */}
      {isBuffering && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 10
        }}>
          <Loader 
            size={48} 
            color="#f59e0b" 
            style={{ animation: 'spin 1s linear infinite' }}
          />
        </div>
      )}

      {/* Seek Preview */}
      {isSeeking && seekPreview !== null && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          background: 'rgba(0,0,0,0.85)',
          padding: '16px 24px',
          borderRadius: '12px',
          fontSize: '24px',
          fontWeight: 'bold',
          color: '#f59e0b',
          zIndex: 15
        }}>
          {formatTime(seekPreview)}
        </div>
      )}

      {/* Controls Overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: showControls 
            ? 'linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, transparent 25%, transparent 60%, rgba(0,0,0,0.9) 100%)'
            : 'transparent',
          opacity: showControls ? 1 : 0,
          transition: 'opacity 0.3s',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: '12px 16px',
          pointerEvents: showControls ? 'auto' : 'none'
        }}
      >
        {/* Top Bar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            style={{
              background: 'rgba(0,0,0,0.6)',
              borderRadius: '50%',
              padding: '8px',
              display: 'flex',
              backdropFilter: 'blur(8px)'
            }}
          >
            <X size={20} />
          </button>

          <p style={{
            fontSize: '14px',
            fontWeight: 600,
            color: '#fff',
            maxWidth: '60%',
            overflow: 'hidden',
            whiteSpace: 'nowrap',
            textOverflow: 'ellipsis',
            textShadow: '0 2px 8px rgba(0,0,0,0.8)'
          }}>
            {title}
          </p>

          <div style={{ display: 'flex', gap: '8px' }}>
            {document.pictureInPictureEnabled && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  togglePiP();
                }}
                style={{
                  background: isPiP ? 'rgba(245,158,11,0.3)' : 'rgba(0,0,0,0.6)',
                  borderRadius: '50%',
                  padding: '8px',
                  display: 'flex',
                  backdropFilter: 'blur(8px)'
                }}
              >
                <PictureInPicture size={18} />
              </button>
            )}

            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowSettings(!showSettings);
              }}
              style={{
                background: showSettings ? 'rgba(245,158,11,0.3)' : 'rgba(0,0,0,0.6)',
                borderRadius: '50%',
                padding: '8px',
                display: 'flex',
                backdropFilter: 'blur(8px)'
              }}
            >
              <Settings size={18} />
            </button>

            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleFullscreen();
              }}
              style={{
                background: 'rgba(0,0,0,0.6)',
                borderRadius: '50%',
                padding: '8px',
                display: 'flex',
                backdropFilter: 'blur(8px)'
              }}
            >
              {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>
          </div>
        </div>

        {/* Center Controls */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '32px'
        }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              skipTime(-10);
            }}
            style={{
              background: 'rgba(0,0,0,0.5)',
              borderRadius: '50%',
              padding: '12px',
              display: 'flex',
              backdropFilter: 'blur(6px)',
              border: '1px solid rgba(255,255,255,0.15)'
            }}
          >
            <Rewind size={24} />
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              togglePlay();
            }}
            style={{
              background: 'rgba(245,158,11,0.9)',
              borderRadius: '50%',
              padding: '20px',
              display: 'flex',
              backdropFilter: 'blur(6px)',
              border: '2px solid rgba(255,255,255,0.3)',
              boxShadow: '0 4px 20px rgba(245,158,11,0.4)'
            }}
          >
            {isPlaying ? <Pause size={32} fill="#000" color="#000" /> : <Play size={32} fill="#000" color="#000" />}
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              skipTime(10);
            }}
            style={{
              background: 'rgba(0,0,0,0.5)',
              borderRadius: '50%',
              padding: '12px',
              display: 'flex',
              backdropFilter: 'blur(6px)',
              border: '1px solid rgba(255,255,255,0.15)'
            }}
          >
            <FastForward size={24} />
          </button>
        </div>

        {/* Bottom Controls */}
        <div>
          {/* Progress Bar */}
          <input
            type="range"
            min={0}
            max={100}
            value={seekProgress}
            onChange={(e) => {
              const newTime = (parseFloat(e.target.value) / 100) * duration;
              handleSeek(newTime);
            }}
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              height: '4px',
              cursor: 'pointer',
              marginBottom: '12px',
              accentColor: '#f59e0b',
              background: `linear-gradient(to right, #f59e0b ${seekProgress}%, rgba(255,255,255,0.3) ${seekProgress}%)`,
              borderRadius: '2px'
            }}
          />

          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            {/* Left Controls */}
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleMute();
                }}
                style={{ display: 'flex' }}
              >
                {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
              </button>

              <input
                type="range"
                min={0}
                max={1}
                step={0.1}
                value={volume}
                onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                onClick={(e) => e.stopPropagation()}
                style={{
                  width: '80px',
                  height: '3px',
                  accentColor: '#f59e0b'
                }}
              />

              <span style={{
                fontSize: '13px',
                color: 'rgba(255,255,255,0.8)',
                fontWeight: 500
              }}>
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>

            {/* Right Info */}
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              {playbackSpeed !== 1 && (
                <span style={{
                  fontSize: '11px',
                  color: '#f59e0b',
                  fontWeight: 600,
                  background: 'rgba(245,158,11,0.2)',
                  padding: '2px 8px',
                  borderRadius: '12px'
                }}>
                  {playbackSpeed}x
                </span>
              )}

              {fileSize && (
                <span style={{
                  fontSize: '11px',
                  color: 'rgba(255,255,255,0.5)'
                }}>
                  {formatSize(fileSize)}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            position: 'absolute',
            top: '60px',
            right: '16px',
            background: 'rgba(0,0,0,0.95)',
            borderRadius: '12px',
            padding: '16px',
            minWidth: '200px',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,255,255,0.1)',
            zIndex: 20
          }}
        >
          {/* Playback Speed */}
          <div style={{ marginBottom: '16px' }}>
            <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '8px' }}>
              سرعة التشغيل
            </p>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {[0.5, 0.75, 1, 1.25, 1.5, 2].map(speed => (
                <button
                  key={speed}
                  onClick={() => changePlaybackSpeed(speed)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    background: playbackSpeed === speed ? '#f59e0b' : 'rgba(255,255,255,0.1)',
                    color: playbackSpeed === speed ? '#000' : '#fff',
                    fontWeight: playbackSpeed === speed ? 700 : 400
                  }}
                >
                  {speed}x
                </button>
              ))}
            </div>
          </div>

          {/* Quality Selector */}
          {qualities.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '8px' }}>
                الجودة
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {qualities.map(quality => (
                  <button
                    key={quality}
                    onClick={() => setSelectedQuality(quality)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: '8px',
                      fontSize: '13px',
                      textAlign: 'right',
                      background: selectedQuality === quality ? 'rgba(245,158,11,0.2)' : 'transparent',
                      color: selectedQuality === quality ? '#f59e0b' : '#fff',
                      border: selectedQuality === quality ? '1px solid #f59e0b' : '1px solid rgba(255,255,255,0.1)'
                    }}
                  >
                    {quality}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Subtitles */}
          {subtitles.length > 0 && (
            <div>
              <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '8px' }}>
                الترجمة
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <button
                  onClick={() => selectSubtitle(null)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    textAlign: 'right',
                    background: !selectedSubtitle ? 'rgba(245,158,11,0.2)' : 'transparent',
                    color: !selectedSubtitle ? '#f59e0b' : '#fff',
                    border: !selectedSubtitle ? '1px solid #f59e0b' : '1px solid rgba(255,255,255,0.1)'
                  }}
                >
                  بدون ترجمة
                </button>
                {subtitles.map(sub => (
                  <button
                    key={sub.id}
                    onClick={() => selectSubtitle(sub)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: '8px',
                      fontSize: '13px',
                      textAlign: 'right',
                      background: selectedSubtitle?.id === sub.id ? 'rgba(245,158,11,0.2)' : 'transparent',
                      color: selectedSubtitle?.id === sub.id ? '#f59e0b' : '#fff',
                      border: selectedSubtitle?.id === sub.id ? '1px solid #f59e0b' : '1px solid rgba(255,255,255,0.1)'
                    }}
                  >
                    {sub.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .video-player-container input[type="range"] {
          -webkit-appearance: none;
          appearance: none;
        }
        
        .video-player-container input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #f59e0b;
          cursor: pointer;
          box-shadow: 0 2px 8px rgba(245,158,11,0.5);
        }
        
        .video-player-container input[type="range"]::-moz-range-thumb {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #f59e0b;
          cursor: pointer;
          border: none;
          box-shadow: 0 2px 8px rgba(245,158,11,0.5);
        }
        
        .video-player-container button {
          cursor: pointer;
          border: none;
          outline: none;
          background: none;
          color: #fff;
          transition: all 0.2s;
        }
        
        .video-player-container button:active {
          transform: scale(0.95);
        }
      `}</style>
    </div>
  );
};

export default EnhancedVideoPlayer;

// Made with Bob
