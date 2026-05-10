import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useStore } from './store/useStore'
import { expandTelegramApp } from './utils/helpers'

// Pages
import HomePage from './pages/HomePage'
import MovieDetailPage from './pages/MovieDetailPage'
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
          <Route path="/w/:encodedId" element={<MovieDetailPage />} />
          <Route path="/watch/:encodedId" element={<WatchPage />} />
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
