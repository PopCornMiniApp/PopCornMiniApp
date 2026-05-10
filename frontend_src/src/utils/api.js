/**
 * API Utilities
 * Handles all API calls to the backend
 */

const API_BASE = '/api';

/**
 * Make API request
 * @param {string} endpoint - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<any>} Response data
 */
const apiRequest = async (endpoint, options = {}) => {
  try {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Request failed:', error);
    throw error;
  }
};

/**
 * Build query string from params
 */
const buildQueryString = (params) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      query.append(key, value);
    }
  });
  return query.toString();
};

// ============================================================================
// Content APIs
// ============================================================================

export const api = {
  // Featured content
  getFeatured: () => apiRequest('/featured'),

  // Movies
  getMovies: (params = {}) => {
    const query = buildQueryString(params);
    return apiRequest(`/movies${query ? `?${query}` : ''}`);
  },

  getMovie: (id) => apiRequest(`/movies/${id}`),

  // Series
  getSeries: (params = {}) => {
    const query = buildQueryString(params);
    return apiRequest(`/series${query ? `?${query}` : ''}`);
  },

  getSeriesDetail: (id) => apiRequest(`/series/${id}`),

  getEpisodes: (seriesId, season) => {
    const query = season ? `?season=${season}` : '';
    return apiRequest(`/series/${seriesId}/episodes${query}`);
  },

  // Search
  search: (query) => apiRequest(`/search?q=${encodeURIComponent(query)}`),

  // Genres
  getGenres: () => apiRequest('/genres'),

  // Stats
  getStats: () => apiRequest('/stats'),

  // Trending
  getTrending: (params = {}) => {
    const query = buildQueryString(params);
    return apiRequest(`/trending${query ? `?${query}` : ''}`);
  },

  // Popular
  getPopular: (params = {}) => {
    const query = buildQueryString(params);
    return apiRequest(`/popular${query ? `?${query}` : ''}`);
  },

  // Latest
  getLatest: (params = {}) => {
    const query = buildQueryString(params);
    return apiRequest(`/latest${query ? `?${query}` : ''}`);
  },

  // Stream
  getStreamUrl: (movieId) => `/api/stream/${movieId}`,
  
  // Qualities
  getAvailableQualities: (contentId) => apiRequest(`/content/${contentId}/qualities`),

  // Cast and Reviews
  getMovieCast: (movieId) => apiRequest(`/movies/${movieId}/cast`),
  getMovieReviews: (movieId) => apiRequest(`/movies/${movieId}/reviews`),
  getSeriesCast: (seriesId) => apiRequest(`/series/${seriesId}/cast`),
  getSeriesReviews: (seriesId) => apiRequest(`/series/${seriesId}/reviews`),

  // Reviews System (New - 1-10 scale)
  getReviews: (contentType, contentId, params = {}) => {
    const query = buildQueryString(params);
    return apiRequest(`/reviews/${contentType}/${contentId}${query ? `?${query}` : ''}`);
  },

  addReview: async (contentType, contentId, rating, comment = null) => {
    // Get Telegram WebApp init data
    const initData = window.Telegram?.WebApp?.initData || '';
    
    const query = buildQueryString({ content_type: contentType, content_id: contentId });
    
    return apiRequest(`/reviews?${query}`, {
      method: 'POST',
      headers: {
        'X-Telegram-Init-Data': initData,
      },
      body: JSON.stringify({ rating, comment }),
    });
  },

  updateReview: async (reviewId, rating, comment = null) => {
    const initData = window.Telegram?.WebApp?.initData || '';
    
    return apiRequest(`/reviews/${reviewId}`, {
      method: 'PUT',
      headers: {
        'X-Telegram-Init-Data': initData,
      },
      body: JSON.stringify({ rating, comment }),
    });
  },

  deleteReview: async (reviewId) => {
    const initData = window.Telegram?.WebApp?.initData || '';
    
    return apiRequest(`/reviews/${reviewId}`, {
      method: 'DELETE',
      headers: {
        'X-Telegram-Init-Data': initData,
      },
    });
  },

  getUserReviews: (userId, params = {}) => {
    const query = buildQueryString(params);
    return apiRequest(`/reviews/user/${userId}${query ? `?${query}` : ''}`);
  },
};

// ============================================================================
// Local Storage APIs (for favorites, history, etc.)
// ============================================================================

export const storage = {
  // Favorites
  getFavorites: () => {
    try {
      return JSON.parse(localStorage.getItem('favorites') || '[]');
    } catch {
      return [];
    }
  },

  addFavorite: (item) => {
    const favorites = storage.getFavorites();
    if (!favorites.find(f => f.id === item.id)) {
      favorites.unshift(item);
      localStorage.setItem('favorites', JSON.stringify(favorites));
    }
  },

  removeFavorite: (id) => {
    const favorites = storage.getFavorites();
    const filtered = favorites.filter(f => f.id !== id);
    localStorage.setItem('favorites', JSON.stringify(filtered));
  },

  isFavorite: (id) => {
    const favorites = storage.getFavorites();
    return favorites.some(f => f.id === id);
  },

  // Watch History
  getHistory: () => {
    try {
      return JSON.parse(localStorage.getItem('history') || '[]');
    } catch {
      return [];
    }
  },

  addToHistory: (item) => {
    const history = storage.getHistory();
    // Remove if exists
    const filtered = history.filter(h => h.id !== item.id);
    // Add to beginning
    filtered.unshift({
      ...item,
      watchedAt: new Date().toISOString(),
    });
    // Keep only last 50
    const limited = filtered.slice(0, 50);
    localStorage.setItem('history', JSON.stringify(limited));
  },

  clearHistory: () => {
    localStorage.setItem('history', '[]');
  },

  // Watch Progress
  getProgress: (id) => {
    try {
      const progress = JSON.parse(localStorage.getItem('progress') || '{}');
      return progress[id] || null;
    } catch {
      return null;
    }
  },

  saveProgress: (id, currentTime, duration) => {
    try {
      const progress = JSON.parse(localStorage.getItem('progress') || '{}');
      progress[id] = {
        currentTime,
        duration,
        percentage: (currentTime / duration) * 100,
        updatedAt: new Date().toISOString(),
      };
      localStorage.setItem('progress', JSON.stringify(progress));
    } catch (error) {
      console.error('Failed to save progress:', error);
    }
  },

  // Language Preference
  getLanguage: () => {
    return localStorage.getItem('language') || 'ar';
  },

  setLanguage: (lang) => {
    localStorage.setItem('language', lang);
  },

  // Theme (if needed in future)
  getTheme: () => {
    return localStorage.getItem('theme') || 'dark';
  },

  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
  },

  // Comments (local only for now)
  getComments: (contentId) => {
    try {
      const comments = JSON.parse(localStorage.getItem('comments') || '{}');
      return comments[contentId] || [];
    } catch {
      return [];
    }
  },

  addComment: (contentId, comment) => {
    try {
      const comments = JSON.parse(localStorage.getItem('comments') || '{}');
      if (!comments[contentId]) {
        comments[contentId] = [];
      }
      comments[contentId].unshift({
        id: Date.now().toString(),
        text: comment,
        createdAt: new Date().toISOString(),
        user: 'أنت', // "You" in Arabic
      });
      localStorage.setItem('comments', JSON.stringify(comments));
    } catch (error) {
      console.error('Failed to add comment:', error);
    }
  },

  // Ratings (local only for now)
  getRating: (contentId) => {
    try {
      const ratings = JSON.parse(localStorage.getItem('ratings') || '{}');
      return ratings[contentId] || null;
    } catch {
      return null;
    }
  },

  setRating: (contentId, rating) => {
    try {
      const ratings = JSON.parse(localStorage.getItem('ratings') || '{}');
      ratings[contentId] = {
        value: rating,
        createdAt: new Date().toISOString(),
      };
      localStorage.setItem('ratings', JSON.stringify(ratings));
    } catch (error) {
      console.error('Failed to save rating:', error);
    }
  },
};

export default api;

// Made with Bob
