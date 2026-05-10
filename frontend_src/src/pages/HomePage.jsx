import React, { useEffect, useState } from 'react'
import { api } from '../utils/api'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, TrendingUp, Clock, Tv, Grid3x3 } from 'lucide-react'
import ContentCard from '../components/ContentCard'
import HeroSection from '../components/HeroSection'

export default function HomePage() {
  const [featured, setFeatured] = useState([])
  const [latest, setLatest] = useState([])
  const [popular, setPopular] = useState([])
  const [series, setSeries] = useState([])
  const [genres, setGenres] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      // Load all data in parallel
      const [featuredData, latestData, popularData, seriesData, genresData] = await Promise.all([
        api.getFeatured().catch(() => null),
        api.getMovies({ limit: 10 }).catch(() => null),
        api.getMovies({ sort: 'rating', limit: 10 }).catch(() => null),
        api.getSeries({ limit: 10 }).catch(() => null),
        api.getGenres().catch(() => null),
      ])

      setFeatured(featuredData?.items || [])
      setLatest(latestData?.items || [])
      setPopular(popularData?.items || [])
      setSeries(seriesData?.items || [])
      setGenres(genresData?.genres || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }


  const Section = ({ title, items, icon: Icon, viewAllPath }) => {
    if (!items || items.length === 0) return null

    return (
      <section style={{ marginBottom: 'var(--spacing-xl)' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--spacing-md)',
          padding: '0 var(--spacing-md)',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            {Icon && <Icon size={20} color="var(--accent-primary)" />}
            <h2 style={{ fontSize: '20px', fontWeight: 600 }}>{title}</h2>
          </div>
          {viewAllPath && (
            <button
              onClick={() => navigate(viewAllPath)}
              style={{
                color: 'var(--accent-primary)',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>عرض الكل</span>
              <ChevronLeft size={16} />
            </button>
          )}
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
          gap: 'var(--spacing-md)',
          padding: '0 var(--spacing-md)',
        }}>
          {items.slice(0, 10).map((item) => (
            <ContentCard key={item.id} item={item} />
          ))}
        </div>
      </section>
    )
  }

  const GenresSection = () => {
    if (!genres || genres.length === 0) return null

    return (
      <section style={{ marginBottom: 'var(--spacing-xl)', padding: '0 var(--spacing-md)' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: 'var(--spacing-md)',
        }}>
          <Grid3x3 size={20} color="var(--accent-primary)" />
          <h2 style={{ fontSize: '20px', fontWeight: 600 }}>التصنيفات</h2>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
          gap: 'var(--spacing-sm)',
        }}>
          {genres.slice(0, 12).map((genre) => (
            <button
              key={genre}
              onClick={() => navigate(`/browse?genre=${encodeURIComponent(genre)}`)}
              style={{
                padding: 'var(--spacing-md)',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-md)',
                fontSize: '14px',
                fontWeight: 500,
                textAlign: 'center',
                transition: 'all var(--transition-base)',
                border: '1px solid var(--bg-tertiary)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--bg-tertiary)'
                e.currentTarget.style.borderColor = 'var(--accent-primary)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--bg-secondary)'
                e.currentTarget.style.borderColor = 'var(--bg-tertiary)'
              }}
            >
              {genre}
            </button>
          ))}
        </div>
      </section>
    )
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        paddingBottom: '80px',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontSize: '48px',
            marginBottom: '16px',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}>
            🍿
          </div>
          <p style={{ color: 'var(--text-secondary)' }}>جاري التحميل...</p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ paddingBottom: '80px' }}>
      {/* Hero Section */}
      <HeroSection items={featured} />

      {/* Latest Movies */}
      <Section
        title="أحدث الإضافات"
        items={latest}
        icon={Clock}
        viewAllPath="/browse?sort=latest"
      />

      {/* Popular Movies */}
      <Section
        title="الأكثر مشاهدة"
        items={popular}
        icon={TrendingUp}
        viewAllPath="/browse?sort=popular"
      />

      {/* Series */}
      <Section
        title="المسلسلات"
        items={series}
        icon={Tv}
        viewAllPath="/browse?type=series"
      />

      {/* Genres */}
      <GenresSection />
    </div>
  )
}

// Made with Bob
