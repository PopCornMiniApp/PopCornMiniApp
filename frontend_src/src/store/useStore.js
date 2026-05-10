import { create } from 'zustand'
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
