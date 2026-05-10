#!/usr/bin/env python3
"""
Script to create complete React frontend structure
"""
import os
import json

# Base directory
BASE_DIR = "frontend_src/src"

# Create directory structure
DIRS = [
    f"{BASE_DIR}/components",
    f"{BASE_DIR}/pages",
    f"{BASE_DIR}/hooks",
    f"{BASE_DIR}/store",
    f"{BASE_DIR}/utils",
    f"{BASE_DIR}/assets",
]

# File contents
FILES = {
    # Main App
    f"{BASE_DIR}/main.jsx": '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Initialize Telegram WebApp
if (window.Telegram?.WebApp) {
  window.Telegram.WebApp.ready()
  window.Telegram.WebApp.expand()
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
''',

    f"{BASE_DIR}/App.jsx": '''import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useStore } from './store/useStore'
import { expandTelegramApp } from './utils/helpers'

// Pages
import HomePage from './pages/HomePage'
import WatchPage from './pages/WatchPage'
import BrowsePage from './pages/BrowsePage'
import SearchPage from './pages/SearchPage'
import FavoritesPage from './pages/FavoritesPage'
import HistoryPage from './pages/HistoryPage'

// Components
import Navigation from './components/Navigation'
import LoadingScreen from './components/LoadingScreen'

function App() {
  const { isLoading, initialize } = useStore()

  useEffect(() => {
    initialize()
    expandTelegramApp()
  }, [initialize])

  if (isLoading) {
    return <LoadingScreen />
  }

  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/w/:encodedId" element={<WatchPage />} />
          <Route path="/browse" element={<BrowsePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/favorites" element={<FavoritesPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Navigation />
      </div>
    </BrowserRouter>
  )
}

export default App
''',

    # Store
    f"{BASE_DIR}/store/useStore.js": '''import { create } from 'zustand'
import { storage } from '../utils/api'

export const useStore = create((set, get) => ({
  // State
  isLoading: true,
  language: 'ar',
  favorites: [],
  history: [],
  
  // Actions
  initialize: async () => {
    const lang = storage.getLanguage()
    const favorites = storage.getFavorites()
    const history = storage.getHistory()
    
    set({ 
      language: lang,
      favorites,
      history,
      isLoading: false 
    })
  },
  
  setLanguage: (lang) => {
    storage.setLanguage(lang)
    set({ language: lang })
  },
  
  addFavorite: (item) => {
    storage.addFavorite(item)
    set({ favorites: storage.getFavorites() })
  },
  
  removeFavorite: (id) => {
    storage.removeFavorite(id)
    set({ favorites: storage.getFavorites() })
  },
  
  addToHistory: (item) => {
    storage.addToHistory(item)
    set({ history: storage.getHistory() })
  },
  
  clearHistory: () => {
    storage.clearHistory()
    set({ history: [] })
  },
}))
''',

    # Components - LoadingScreen
    f"{BASE_DIR}/components/LoadingScreen.jsx": '''import React from 'react'

export default function LoadingScreen() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: 'var(--bg-primary)',
    }}>
      <div style={{
        textAlign: 'center',
      }}>
        <div style={{
          fontSize: '48px',
          marginBottom: '16px',
          animation: 'pulse 1.5s ease-in-out infinite',
        }}>
          🍿
        </div>
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: '14px',
        }}>
          جاري التحميل...
        </p>
      </div>
    </div>
  )
}
''',

    # Components - Navigation
    f"{BASE_DIR}/components/Navigation.jsx": '''import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { House, Grid3x3, Search, Heart, Clock } from 'lucide-react'

export default function Navigation() {
  const location = useLocation()
  
  const navItems = [
    { path: '/', icon: House, label: 'الرئيسية' },
    { path: '/browse', icon: Grid3x3, label: 'تصفح' },
    { path: '/search', icon: Search, label: 'بحث' },
    { path: '/favorites', icon: Heart, label: 'المفضلة' },
    { path: '/history', icon: Clock, label: 'السجل' },
  ]
  
  return (
    <nav style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      background: 'var(--bg-secondary)',
      borderTop: '1px solid var(--bg-tertiary)',
      display: 'flex',
      justifyContent: 'space-around',
      padding: 'var(--spacing-sm) 0',
      paddingBottom: 'calc(var(--spacing-sm) + env(safe-area-inset-bottom))',
      zIndex: 'var(--z-fixed)',
    }}>
      {navItems.map(({ path, icon: Icon, label }) => {
        const isActive = location.pathname === path
        return (
          <Link
            key={path}
            to={path}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '4px',
              padding: 'var(--spacing-sm)',
              color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
              textDecoration: 'none',
              transition: 'all var(--transition-base)',
            }}
          >
            <Icon size={20} />
            <span style={{ fontSize: '10px', fontWeight: 500 }}>{label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
''',

    # Pages - HomePage (simplified for now)
    f"{BASE_DIR}/pages/HomePage.jsx": '''import React, { useEffect, useState } from 'react'
import { api } from '../utils/api'
import { encodeContentUrl } from '../utils/urlEncoder'
import { useNavigate } from 'react-router-dom'
import { getPosterUrl } from '../utils/helpers'

export default function HomePage() {
  const [featured, setFeatured] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const data = await api.getFeatured()
      setFeatured(data.movies || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleItemClick = (item) => {
    const url = encodeContentUrl('movie', item.id)
    navigate(url)
  }

  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>جاري التحميل...</div>
  }

  return (
    <div style={{ paddingBottom: '80px' }}>
      <header style={{
        padding: 'var(--spacing-lg) var(--spacing-md)',
        background: 'linear-gradient(to bottom, var(--bg-secondary), var(--bg-primary))',
      }}>
        <h1 style={{ fontSize: '28px', marginBottom: '8px' }}>🍿 PopCorn</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          أفلام ومسلسلات بجودة عالية
        </p>
      </header>

      <section style={{ padding: 'var(--spacing-md)' }}>
        <h2 style={{ fontSize: '20px', marginBottom: 'var(--spacing-md)' }}>
          مميز
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
          gap: 'var(--spacing-md)',
        }}>
          {featured.map((item) => (
            <div
              key={item.id}
              onClick={() => handleItemClick(item)}
              style={{
                cursor: 'pointer',
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
                transition: 'transform var(--transition-base)',
              }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              <img
                src={getPosterUrl(item.poster_path)}
                alt={item.title}
                style={{
                  width: '100%',
                  aspectRatio: '2/3',
                  objectFit: 'cover',
                  background: 'var(--bg-tertiary)',
                }}
              />
              <div style={{ padding: 'var(--spacing-sm)' }}>
                <h3 style={{
                  fontSize: '14px',
                  fontWeight: 600,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {item.title}
                </h3>
                {item.year && (
                  <p style={{
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    marginTop: '4px',
                  }}>
                    {item.year}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
''',

    # Pages - WatchPage (simplified)
    f"{BASE_DIR}/pages/WatchPage.jsx": '''import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { decodeContentUrl } from '../utils/urlEncoder'
import { api } from '../utils/api'
import { ArrowRight } from 'lucide-react'

export default function WatchPage() {
  const { encodedId } = useParams()
  const navigate = useNavigate()
  const [content, setContent] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadContent()
  }, [encodedId])

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
    } catch (error) {
      console.error('Failed to load content:', error)
      navigate('/')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>جاري التحميل...</div>
  }

  if (!content) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>المحتوى غير موجود</div>
  }

  return (
    <div style={{ paddingBottom: '80px' }}>
      <header style={{
        padding: 'var(--spacing-md)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-md)',
        background: 'var(--bg-secondary)',
      }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: 'var(--spacing-sm)',
            borderRadius: 'var(--radius-full)',
            background: 'var(--bg-tertiary)',
          }}
        >
          <ArrowRight size={20} />
        </button>
        <h1 style={{ fontSize: '18px', fontWeight: 600 }}>
          {content.title || content.name}
        </h1>
      </header>

      <div style={{ padding: 'var(--spacing-md)' }}>
        <div style={{
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--spacing-lg)',
        }}>
          <h2 style={{ fontSize: '24px', marginBottom: 'var(--spacing-md)' }}>
            {content.title || content.name}
          </h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            {content.overview || 'لا يوجد وصف متاح'}
          </p>
        </div>
      </div>
    </div>
  )
}
''',

    # Other pages (simplified placeholders)
    f"{BASE_DIR}/pages/BrowsePage.jsx": '''import React from 'react'

export default function BrowsePage() {
  return (
    <div style={{ padding: 'var(--spacing-md)', paddingBottom: '80px' }}>
      <h1 style={{ fontSize: '24px', marginBottom: 'var(--spacing-lg)' }}>تصفح</h1>
      <p style={{ color: 'var(--text-secondary)' }}>قريباً...</p>
    </div>
  )
}
''',

    f"{BASE_DIR}/pages/SearchPage.jsx": '''import React from 'react'

export default function SearchPage() {
  return (
    <div style={{ padding: 'var(--spacing-md)', paddingBottom: '80px' }}>
      <h1 style={{ fontSize: '24px', marginBottom: 'var(--spacing-lg)' }}>بحث</h1>
      <p style={{ color: 'var(--text-secondary)' }}>قريباً...</p>
    </div>
  )
}
''',

    f"{BASE_DIR}/pages/FavoritesPage.jsx": '''import React from 'react'
import { useStore } from '../store/useStore'

export default function FavoritesPage() {
  const { favorites } = useStore()

  return (
    <div style={{ padding: 'var(--spacing-md)', paddingBottom: '80px' }}>
      <h1 style={{ fontSize: '24px', marginBottom: 'var(--spacing-lg)' }}>المفضلة</h1>
      {favorites.length === 0 ? (
        <p style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '40px' }}>
          لا توجد عناصر في المفضلة
        </p>
      ) : (
        <div>
          {favorites.map((item) => (
            <div key={item.id} style={{ marginBottom: 'var(--spacing-md)' }}>
              {item.title}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
''',

    f"{BASE_DIR}/pages/HistoryPage.jsx": '''import React from 'react'
import { useStore } from '../store/useStore'

export default function HistoryPage() {
  const { history, clearHistory } = useStore()

  return (
    <div style={{ padding: 'var(--spacing-md)', paddingBottom: '80px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
        <h1 style={{ fontSize: '24px' }}>سجل المشاهدة</h1>
        {history.length > 0 && (
          <button
            onClick={clearHistory}
            style={{
              padding: 'var(--spacing-sm) var(--spacing-md)',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-md)',
              fontSize: '14px',
            }}
          >
            مسح الكل
          </button>
        )}
      </div>
      {history.length === 0 ? (
        <p style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '40px' }}>
          لا يوجد سجل مشاهدة
        </p>
      ) : (
        <div>
          {history.map((item) => (
            <div key={item.id} style={{ marginBottom: 'var(--spacing-md)' }}>
              {item.title}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
''',
}

def create_structure():
    """Create the frontend structure"""
    print("Creating frontend structure...")
    
    # Create directories
    for dir_path in DIRS:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✓ Created directory: {dir_path}")
    
    # Create files
    for file_path, content in FILES.items():
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Created file: {file_path}")
    
    print("\n✅ Frontend structure created successfully!")
    print("\nNext steps:")
    print("1. cd frontend_src")
    print("2. npm install")
    print("3. npm run dev (for development)")
    print("4. npm run build (to build for production)")

if __name__ == "__main__":
    create_structure()

# Made with Bob
