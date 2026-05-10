import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Filter, SlidersHorizontal, ChevronDown } from 'lucide-react'
import { api } from '../utils/api'
import ContentCard from '../components/ContentCard'

export default function BrowsePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [content, setContent] = useState([])
  const [genres, setGenres] = useState([])
  const [loading, setLoading] = useState(true)
  const [showFilters, setShowFilters] = useState(false)
  
  // Filter states
  const [selectedGenre, setSelectedGenre] = useState(searchParams.get('genre') || '')
  const [selectedType, setSelectedType] = useState(searchParams.get('type') || 'all')
  const [selectedSort, setSelectedSort] = useState(searchParams.get('sort') || 'latest')
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  useEffect(() => {
    loadGenres()
  }, [])

  useEffect(() => {
    loadContent()
  }, [selectedGenre, selectedType, selectedSort, page])

  const loadGenres = async () => {
    try {
      const data = await api.getGenres()
      setGenres(data.genres || [])
    } catch (error) {
      console.error('Failed to load genres:', error)
    }
  }

  const loadContent = async () => {
    setLoading(true)
    try {
      const params = {
        limit: 20,
        offset: (page - 1) * 20,
      }

      if (selectedGenre) params.genre = selectedGenre
      if (selectedSort === 'rating') params.sort = 'rating'
      if (selectedSort === 'latest') params.sort = 'date'

      let data
      if (selectedType === 'series') {
        data = await api.getSeries(params)
      } else if (selectedType === 'movies') {
        data = await api.getMovies(params)
      } else {
        // Load both movies and series
        const [moviesData, seriesData] = await Promise.all([
          api.getMovies(params).catch(() => ({ items: [] })),
          api.getSeries(params).catch(() => ({ items: [] })),
        ])
        data = {
          items: [...(moviesData.items || []), ...(seriesData.items || [])],
        }
      }

      if (page === 1) {
        setContent(data.items || [])
      } else {
        setContent(prev => [...prev, ...(data.items || [])])
      }

      setHasMore((data.items || []).length === 20)
    } catch (error) {
      console.error('Failed to load content:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleGenreChange = (genre) => {
    setSelectedGenre(genre)
    setPage(1)
    setSearchParams({ genre, type: selectedType, sort: selectedSort })
  }

  const handleTypeChange = (type) => {
    setSelectedType(type)
    setPage(1)
    setSearchParams({ genre: selectedGenre, type, sort: selectedSort })
  }

  const handleSortChange = (sort) => {
    setSelectedSort(sort)
    setPage(1)
    setSearchParams({ genre: selectedGenre, type: selectedType, sort })
  }

  const loadMore = () => {
    if (!loading && hasMore) {
      setPage(prev => prev + 1)
    }
  }

  return (
    <div style={{ paddingBottom: '80px' }}>
      {/* Header */}
      <header style={{
        padding: 'var(--spacing-lg) var(--spacing-md)',
        background: 'var(--bg-secondary)',
        position: 'sticky',
        top: 0,
        zIndex: 'var(--z-sticky)',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--spacing-md)',
        }}>
          <h1 style={{ fontSize: '24px', fontWeight: 700 }}>تصفح</h1>
          <button
            onClick={() => setShowFilters(!showFilters)}
            style={{
              padding: 'var(--spacing-sm) var(--spacing-md)',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '14px',
            }}
          >
            <SlidersHorizontal size={16} />
            <span>فلاتر</span>
          </button>
        </div>

        {/* Filters */}
        {showFilters && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--spacing-md)',
            padding: 'var(--spacing-md)',
            background: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-md)',
          }}>
            {/* Type Filter */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 600,
                marginBottom: '8px',
              }}>
                النوع
              </label>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '8px',
              }}>
                {['all', 'movies', 'series'].map((type) => (
                  <button
                    key={type}
                    onClick={() => handleTypeChange(type)}
                    style={{
                      padding: 'var(--spacing-sm)',
                      background: selectedType === type ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '14px',
                    }}
                  >
                    {type === 'all' ? 'الكل' : type === 'movies' ? 'أفلام' : 'مسلسلات'}
                  </button>
                ))}
              </div>
            </div>

            {/* Sort Filter */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 600,
                marginBottom: '8px',
              }}>
                الترتيب
              </label>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '8px',
              }}>
                {[
                  { value: 'latest', label: 'الأحدث' },
                  { value: 'rating', label: 'الأعلى تقييماً' },
                ].map((sort) => (
                  <button
                    key={sort.value}
                    onClick={() => handleSortChange(sort.value)}
                    style={{
                      padding: 'var(--spacing-sm)',
                      background: selectedSort === sort.value ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '14px',
                    }}
                  >
                    {sort.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Genre Filter */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: 600,
                marginBottom: '8px',
              }}>
                التصنيف
              </label>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '8px',
                maxHeight: '200px',
                overflowY: 'auto',
              }}>
                <button
                  onClick={() => handleGenreChange('')}
                  style={{
                    padding: 'var(--spacing-sm)',
                    background: !selectedGenre ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '14px',
                  }}
                >
                  الكل
                </button>
                {genres.map((genre) => (
                  <button
                    key={genre}
                    onClick={() => handleGenreChange(genre)}
                    style={{
                      padding: 'var(--spacing-sm)',
                      background: selectedGenre === genre ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '14px',
                    }}
                  >
                    {genre}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Content Grid */}
      <div style={{ padding: 'var(--spacing-md)' }}>
        {loading && page === 1 ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '400px',
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
        ) : content.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
          }}>
            <p style={{ fontSize: '48px', marginBottom: '16px' }}>😕</p>
            <p style={{ color: 'var(--text-secondary)' }}>لا توجد نتائج</p>
          </div>
        ) : (
          <>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
              gap: 'var(--spacing-md)',
            }}>
              {content.map((item) => (
                <ContentCard key={item.id} item={item} showType />
              ))}
            </div>

            {/* Load More Button */}
            {hasMore && (
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                marginTop: 'var(--spacing-xl)',
              }}>
                <button
                  onClick={loadMore}
                  disabled={loading}
                  style={{
                    padding: 'var(--spacing-md) var(--spacing-xl)',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '14px',
                    fontWeight: 600,
                    opacity: loading ? 0.5 : 1,
                  }}
                >
                  {loading ? 'جاري التحميل...' : 'تحميل المزيد'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// Made with Bob
