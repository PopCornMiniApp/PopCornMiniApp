/**
 * Helper Utilities
 * Common helper functions used throughout the app
 */

/**
 * Format duration in minutes to readable format
 * @param {number} minutes - Duration in minutes
 * @returns {string} Formatted duration (e.g., "2h 30m")
 */
export const formatDuration = (minutes) => {
  if (!minutes || minutes <= 0) return '';
  
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  
  if (hours === 0) return `${mins}د`;
  if (mins === 0) return `${hours}س`;
  return `${hours}س ${mins}د`;
};

/**
 * Format file size
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size
 */
export const formatFileSize = (bytes) => {
  if (!bytes || bytes <= 0) return '';
  
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(0)} MB`;
};

/**
 * Format date to Arabic
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date
 */
export const formatDate = (date) => {
  if (!date) return '';
  
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  
  return d.toLocaleDateString('ar-DZ', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

/**
 * Format relative time (e.g., "منذ ساعتين")
 * @param {string|Date} date - Date to format
 * @returns {string} Relative time
 */
export const formatRelativeTime = (date) => {
  if (!date) return '';
  
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffMins < 1) return 'الآن';
  if (diffMins < 60) return `منذ ${diffMins} دقيقة`;
  if (diffHours < 24) return `منذ ${diffHours} ساعة`;
  if (diffDays < 7) return `منذ ${diffDays} يوم`;
  
  return formatDate(date);
};

/**
 * Format rating (e.g., 8.5 -> "8.5/10")
 * @param {number} rating - Rating value
 * @returns {string} Formatted rating
 */
export const formatRating = (rating) => {
  if (!rating || rating <= 0) return 'غير مقيّم';
  return `${rating.toFixed(1)}/10`;
};

/**
 * Get rating color based on value
 * @param {number} rating - Rating value
 * @returns {string} Color class or hex
 */
export const getRatingColor = (rating) => {
  if (!rating) return '#707070';
  if (rating >= 8) return '#10b981'; // Green
  if (rating >= 6) return '#f59e0b'; // Orange
  return '#ef4444'; // Red
};

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export const truncateText = (text, maxLength = 100) => {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength).trim() + '...';
};

/**
 * Get poster URL with fallback
 * @param {string} path - Poster path
 * @param {string} size - Image size (w500, w780, original)
 * @returns {string} Full poster URL
 */
export const getPosterUrl = (path, size = 'w500') => {
  if (!path) return '/placeholder-poster.jpg';
  if (path.startsWith('http')) return path;
  return `https://image.tmdb.org/t/p/${size}${path}`;
};

/**
 * Get backdrop URL with fallback
 * @param {string} path - Backdrop path
 * @param {string} size - Image size (w780, w1280, original)
 * @returns {string} Full backdrop URL
 */
export const getBackdropUrl = (path, size = 'w1280') => {
  if (!path) return '/placeholder-backdrop.jpg';
  if (path.startsWith('http')) return path;
  return `https://image.tmdb.org/t/p/${size}${path}`;
};

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} Debounced function
 */
export const debounce = (func, wait = 300) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Throttle function
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in ms
 * @returns {Function} Throttled function
 */
export const throttle = (func, limit = 300) => {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

/**
 * Check if device is mobile
 * @returns {boolean} True if mobile
 */
export const isMobile = () => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
};

/**
 * Check if running in Telegram WebApp
 * @returns {boolean} True if in Telegram
 */
export const isTelegramWebApp = () => {
  return window.Telegram?.WebApp?.initData !== undefined;
};

/**
 * Get Telegram user data
 * @returns {object|null} User data or null
 */
export const getTelegramUser = () => {
  if (!isTelegramWebApp()) return null;
  
  try {
    const webApp = window.Telegram.WebApp;
    return webApp.initDataUnsafe?.user || null;
  } catch {
    return null;
  }
};

/**
 * Expand Telegram WebApp
 */
export const expandTelegramApp = () => {
  if (isTelegramWebApp()) {
    try {
      window.Telegram.WebApp.expand();
    } catch (error) {
      console.error('Failed to expand Telegram app:', error);
    }
  }
};

/**
 * Set Telegram back button
 * @param {Function} callback - Callback when back button clicked
 */
export const setTelegramBackButton = (callback) => {
  if (isTelegramWebApp()) {
    try {
      const webApp = window.Telegram.WebApp;
      webApp.BackButton.show();
      webApp.BackButton.onClick(callback);
    } catch (error) {
      console.error('Failed to set back button:', error);
    }
  }
};

/**
 * Hide Telegram back button
 */
export const hideTelegramBackButton = () => {
  if (isTelegramWebApp()) {
    try {
      window.Telegram.WebApp.BackButton.hide();
    } catch (error) {
      console.error('Failed to hide back button:', error);
    }
  }
};

/**
 * Show Telegram alert
 * @param {string} message - Alert message
 */
export const showTelegramAlert = (message) => {
  if (isTelegramWebApp()) {
    try {
      window.Telegram.WebApp.showAlert(message);
    } catch (error) {
      console.error('Failed to show alert:', error);
      alert(message);
    }
  } else {
    alert(message);
  }
};

/**
 * Haptic feedback
 * @param {string} type - Feedback type (light, medium, heavy, error, success, warning)
 */
export const hapticFeedback = (type = 'light') => {
  if (isTelegramWebApp()) {
    try {
      const webApp = window.Telegram.WebApp;
      if (type === 'error' || type === 'success' || type === 'warning') {
        webApp.HapticFeedback.notificationOccurred(type);
      } else {
        webApp.HapticFeedback.impactOccurred(type);
      }
    } catch (error) {
      console.error('Haptic feedback failed:', error);
    }
  }
};

/**
 * Copy to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
export const copyToClipboard = async (text) => {
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(text);
      return true;
    } else {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      return true;
    }
  } catch (error) {
    console.error('Failed to copy:', error);
    return false;
  }
};

/**
 * Share content
 * @param {object} data - Share data {title, text, url}
 * @returns {Promise<boolean>} Success status
 */
export const shareContent = async (data) => {
  try {
    if (navigator.share) {
      await navigator.share(data);
      return true;
    } else {
      // Fallback: copy URL to clipboard
      await copyToClipboard(data.url || data.text);
      showTelegramAlert('تم نسخ الرابط');
      return true;
    }
  } catch (error) {
    console.error('Failed to share:', error);
    return false;
  }
};

/**
 * Generate random ID
 * @returns {string} Random ID
 */
export const generateId = () => {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
};

/**
 * Sleep/delay function
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise} Promise that resolves after delay
 */
export const sleep = (ms) => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Clamp number between min and max
 * @param {number} value - Value to clamp
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @returns {number} Clamped value
 */
export const clamp = (value, min, max) => {
  return Math.min(Math.max(value, min), max);
};

// Made with Bob
