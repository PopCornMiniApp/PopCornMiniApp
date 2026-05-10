import React, { useState, useEffect } from 'react'
import { Search, X } from 'lucide-react'
import { api } from '../utils/api'
import { debounce } from '../utils/helpers'
import ContentCard from '../components/ContentCard'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  useEffect(() => {
    if (query.trim().length >= 2) {
      debouncedSearch(query)
    } else {
      setResults([])
      setSearched(false)
    }
  }, [query])

  const searchContent = async (searchQuery) => {
    setLoading(true)
    setSearched(true)
    try {
      const data = await api.search(searchQuery)
      setResults(data.items || [])
    } catch (error) {
      console.error('Search failed:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const debouncedSearch = debounce(searchContent, 500)

  const handleClear = () => {
    setQuery('')
    setResults([])
    setSearched(false)
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
        <h1 style={{
          fontSize: '24px',
          fontWeight: 700,
          marginBottom: 'var(--spacing-md)',
        }}>
          بحث
        </h1>

        {/* Search Input */}
        <div style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
        }}>
          <Search
            size={20}
            style={{
              position: 'absolute',
              right: 'var(--spacing-md)',
              color: 'var(--text-secondary)',
            }}
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="ابحث عن أفلام ومسلسلات..."
            autoFocus
            style={{
              width: '100%',
              padding: 'var(--spacing-md)',
              paddingRight: '48px',
              paddingLeft: query ? '48px' : 'var(--spacing-md)',
              background: 'var(--bg-tertiary)',
              border: '2px solid transparent',
              borderRadius: 'var(--radius-md)',
              fontSize: '16px',
              outline: 'none',
              transition: 'border-color var(--transition-base)',
            }}
            onFocus={(e) => e.target.style.borderColor = 'var(--accent-primary)'}
            onBlur={(e) => e.target.style.borderColor = 'transparent'}
          />
          {query && (
            <button
              onClick={handleClear}
              style={{
                position: 'absolute',
                left: 'var(--spacing-md)',
                padding: '4px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--bg-secondary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <X size={16} />
            </button>
          )}
        </div>
      </header>

      {/* Results */}
      <div style={{ padding: 'var(--spacing-md)' }}>
        {loading ? (
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
                🔍
              </div>
              <p style={{ color: 'var(--text-secondary)' }}>جاري البحث...</p>
            </div>
          </div>
        ) : !searched ? (
          <div style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
            color: 'var(--text-secondary)',
          }}>
            <div style={{ fontSize: '64px', marginBottom: 'var(--spacing-md)' }}>
              🔍
            </div>
            <h2 style={{
              fontSize: '20px',
              fontWeight: 600,
              marginBottom: '8px',
              color: 'var(--text-primary)',
            }}>
              ابحث عن محتواك المفضل
            </h2>
            <p style={{ fontSize: '14px' }}>
              ابدأ بكتابة اسم الفيلم أو المسلسل
            </p>
          </div>
        ) : results.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
          }}>
            <p style={{ fontSize: '48px', marginBottom: '16px' }}>😕</p>
            <h2 style={{
              fontSize: '20px',
              fontWeight: 600,
              marginBottom: '8px',
            }}>
              لا توجد نتائج
            </h2>
            <p style={{
              color: 'var(--text-secondary)',
              fontSize: '14px',
            }}>
              جرب البحث بكلمات مختلفة
            </p>
          </div>
        ) : (
          <>
            <div style={{
              marginBottom: 'var(--spacing-md)',
              color: 'var(--text-secondary)',
              fontSize: '14px',
            }}>
              {results.length} نتيجة
            </div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
              gap: 'var(--spacing-md)',
            }}>
              {results.map((item) => (
                <ContentCard key={item.id} item={item} showType />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// Made with Bob
