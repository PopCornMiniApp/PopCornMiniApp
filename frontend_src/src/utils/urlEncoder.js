/**
 * URL Encoding/Decoding System
 * Provides clean, non-revealing URLs for content
 */

// Simple Base64 encoding with URL-safe characters
const base64UrlEncode = (str) => {
  return btoa(str)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
};

const base64UrlDecode = (str) => {
  // Add padding back
  str = str.replace(/-/g, '+').replace(/_/g, '/');
  while (str.length % 4) {
    str += '=';
  }
  return atob(str);
};

/**
 * Encode content ID to clean URL
 * @param {string} type - 'movie' or 'series'
 * @param {string} id - Content ID
 * @returns {string} Encoded URL path
 */
export const encodeContentUrl = (type, id) => {
  const data = JSON.stringify({ t: type, i: id });
  const encoded = base64UrlEncode(data);
  return `/w/${encoded}`;
};

/**
 * Decode URL to get content info
 * @param {string} encodedId - Encoded ID from URL
 * @returns {object|null} {type, id} or null if invalid
 */
export const decodeContentUrl = (encodedId) => {
  try {
    const decoded = base64UrlDecode(encodedId);
    const data = JSON.parse(decoded);
    return { type: data.t, id: data.i };
  } catch (error) {
    console.error('Failed to decode URL:', error);
    return null;
  }
};

/**
 * Generate share URL
 * @param {string} type - Content type
 * @param {string} id - Content ID
 * @param {string} title - Content title
 * @returns {string} Shareable URL
 */
export const generateShareUrl = (type, id, title) => {
  const encodedPath = encodeContentUrl(type, id);
  const baseUrl = window.location.origin;
  return `${baseUrl}${encodedPath}`;
};

/**
 * Generate episode URL for series
 * @param {string} seriesId - Series ID
 * @param {number} season - Season number
 * @param {number} episode - Episode number
 * @returns {string} Encoded URL path
 */
export const encodeEpisodeUrl = (seriesId, season, episode) => {
  const data = JSON.stringify({ 
    t: 'series', 
    i: seriesId, 
    s: season, 
    e: episode 
  });
  const encoded = base64UrlEncode(data);
  return `/w/${encoded}`;
};

/**
 * Decode episode URL
 * @param {string} encodedId - Encoded ID from URL
 * @returns {object|null} {type, id, season, episode} or null
 */
export const decodeEpisodeUrl = (encodedId) => {
  try {
    const decoded = base64UrlDecode(encodedId);
    const data = JSON.parse(decoded);
    return { 
      type: data.t, 
      id: data.i, 
      season: data.s, 
      episode: data.e 
    };
  } catch (error) {
    console.error('Failed to decode episode URL:', error);
    return null;
  }
};

// Made with Bob
