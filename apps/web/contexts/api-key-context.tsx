'use client'

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'

const API_KEY_STORAGE_KEY = 'urban-lens:api-key'

interface ApiKeyContextType {
  apiKey: string | null
  setApiKey: (key: string | null) => void
  clearApiKey: () => void
  isAuthenticated: boolean
}

const ApiKeyContext = createContext<ApiKeyContextType | null>(null)

export function ApiKeyProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState<string | null>(null)
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(API_KEY_STORAGE_KEY)
    if (stored) {
      setApiKeyState(stored)
    }
    setIsHydrated(true)
  }, [])

  const setApiKey = useCallback((key: string | null) => {
    setApiKeyState(key)
    if (key) {
      localStorage.setItem(API_KEY_STORAGE_KEY, key)
    } else {
      localStorage.removeItem(API_KEY_STORAGE_KEY)
    }
  }, [])

  const clearApiKey = useCallback(() => {
    setApiKeyState(null)
    localStorage.removeItem(API_KEY_STORAGE_KEY)
  }, [])

  if (!isHydrated) {
    return null
  }

  return (
    <ApiKeyContext.Provider
      value={{
        apiKey,
        setApiKey,
        clearApiKey,
        isAuthenticated: !!apiKey,
      }}
    >
      {children}
    </ApiKeyContext.Provider>
  )
}

export function useApiKey() {
  const context = useContext(ApiKeyContext)
  if (!context) {
    throw new Error('useApiKey must be used within an ApiKeyProvider')
  }
  return context
}
