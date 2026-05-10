import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { House, Grid3x3, Search, Heart, Clock, Bell } from 'lucide-react'
import { hapticFeedback } from '../utils/helpers'

export default function Navigation() {
  const location = useLocation()
  const [notificationCount, setNotificationCount] = useState(0)
  const [activeTab, setActiveTab] = useState(location.pathname)
  
  useEffect(() => {
    setActiveTab(location.pathname)
  }, [location.pathname])

  // Simulate notifications (you can connect this to real data)
  useEffect(() => {
    // Check for new content or updates
    const checkNotifications = () => {
      const lastVisit = localStorage.getItem('lastVisit')
      const now = Date.now()
      if (!lastVisit || now - parseInt(lastVisit) > 86400000) { // 24 hours
        setNotificationCount(Math.floor(Math.random() * 5) + 1)
      }
    }
    checkNotifications()
  }, [])
  
  const navItems = [
    { path: '/', icon: House, label: 'الرئيسية' },
    { path: '/browse', icon: Grid3x3, label: 'تصفح' },
    { path: '/search', icon: Search, label: 'بحث' },
    { path: '/favorites', icon: Heart, label: 'المفضلة' },
    { path: '/history', icon: Clock, label: 'السجل' },
  ]

  const handleNavClick = (path) => {
    hapticFeedback('light')
    setActiveTab(path)
    if (path === '/') {
      localStorage.setItem('lastVisit', Date.now().toString())
      setNotificationCount(0)
    }
  }
  
  return (
    <>
      <nav style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: 'rgba(26, 26, 26, 0.95)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        display: 'flex',
        justifyContent: 'space-around',
        padding: 'var(--spacing-sm) 0',
        paddingBottom: 'calc(var(--spacing-sm) + env(safe-area-inset-bottom))',
        zIndex: 'var(--z-fixed)',
        boxShadow: '0 -4px 24px rgba(0, 0, 0, 0.4)',
      }}>
        {/* Active Indicator Background */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: `${navItems.findIndex(item => item.path === activeTab) * (100 / navItems.length)}%`,
          width: `${100 / navItems.length}%`,
          height: '3px',
          background: 'var(--accent-primary)',
          transition: 'left 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
          boxShadow: '0 0 12px var(--accent-primary)',
        }} />

        {navItems.map(({ path, icon: Icon, label }, index) => {
          const isActive = location.pathname === path
          const showNotification = path === '/' && notificationCount > 0
          
          return (
            <Link
              key={path}
              to={path}
              onClick={() => handleNavClick(path)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '4px',
                padding: 'var(--spacing-sm)',
                color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                textDecoration: 'none',
                transition: 'all var(--transition-base)',
                position: 'relative',
                flex: 1,
                transform: isActive ? 'translateY(-2px)' : 'translateY(0)',
              }}
            >
              {/* Icon Container with Animation */}
              <div style={{
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                {/* Glow Effect for Active Tab */}
                {isActive && (
                  <div style={{
                    position: 'absolute',
                    inset: '-8px',
                    background: 'radial-gradient(circle, rgba(245, 158, 11, 0.2) 0%, transparent 70%)',
                    borderRadius: '50%',
                    animation: 'pulse 2s ease-in-out infinite',
                  }} />
                )}

                <Icon
                  size={22}
                  strokeWidth={isActive ? 2.5 : 2}
                  style={{
                    transition: 'all var(--transition-base)',
                    filter: isActive ? 'drop-shadow(0 0 8px var(--accent-primary))' : 'none',
                  }}
                />

                {/* Notification Badge */}
                {showNotification && (
                  <div style={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-8px',
                    background: '#ef4444',
                    color: 'white',
                    fontSize: '10px',
                    fontWeight: 700,
                    padding: '2px 5px',
                    borderRadius: 'var(--radius-full)',
                    minWidth: '18px',
                    height: '18px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 2px 8px rgba(239, 68, 68, 0.5)',
                    animation: 'bounce 1s ease-in-out infinite',
                  }}>
                    {notificationCount}
                  </div>
                )}
              </div>

              {/* Label */}
              <span style={{
                fontSize: '10px',
                fontWeight: isActive ? 700 : 500,
                transition: 'all var(--transition-base)',
                opacity: isActive ? 1 : 0.8,
              }}>
                {label}
              </span>

              {/* Active Dot Indicator */}
              {isActive && (
                <div style={{
                  position: 'absolute',
                  bottom: '2px',
                  width: '4px',
                  height: '4px',
                  background: 'var(--accent-primary)',
                  borderRadius: '50%',
                  animation: 'scaleIn 0.3s ease-out',
                }} />
              )}
            </Link>
          )
        })}
      </nav>

      {/* CSS Animations */}
      <style>{`
        @keyframes bounce {
          0%, 100% {
            transform: translateY(0) scale(1);
          }
          50% {
            transform: translateY(-4px) scale(1.1);
          }
        }

        @keyframes scaleIn {
          from {
            transform: scale(0);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        /* Touch feedback for mobile */
        @media (hover: none) and (pointer: coarse) {
          nav a:active {
            transform: scale(0.95) !important;
          }
        }
      `}</style>
    </>
  )
}

// Made with Bob
