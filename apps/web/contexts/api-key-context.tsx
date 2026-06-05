'use client'

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

interface SessionStateResponse {
  authenticated: boolean
  masked_key: string | null
}

interface ApiKeyContextType {
  apiKey: string | null
  maskedApiKey: string | null
  setApiKey: (key: string) => Promise<void>
  clearApiKey: () => Promise<void>
  isAuthenticated: boolean
  isLoading: boolean
}

const ApiKeyContext = createContext<ApiKeyContextType | null>(null)

export function ApiKeyProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState<string | null>(null)
  const [maskedApiKey, setMaskedApiKey] = useState<string | null>(null)
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    let isMounted = true

    fetch('/api/v1/access/session', { cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Nao foi possivel carregar a sessao atual.')
        }
        return (await response.json()) as SessionStateResponse
      })
      .then((session) => {
        if (!isMounted) return
        setApiKeyState(session.authenticated ? 'governed-session' : null)
        setMaskedApiKey(session.masked_key)
      })
      .catch(() => {
        if (!isMounted) return
        setApiKeyState(null)
        setMaskedApiKey(null)
      })
      .finally(() => {
        if (isMounted) {
          setIsHydrated(true)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  const setApiKey = useCallback(async (key: string) => {
    const response = await fetch('/api/v1/access/session', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ apiKey: key }),
    })

    if (!response.ok) {
      let message = 'Nao foi possivel validar a API key informada.'

      try {
        const body = (await response.json()) as { message?: string }
        if (body.message) {
          message = body.message
        }
      } catch {}

      throw new Error(message)
    }

    const session = (await response.json()) as SessionStateResponse
    setApiKeyState(session.authenticated ? 'governed-session' : null)
    setMaskedApiKey(session.masked_key)
  }, [])

  const clearApiKey = useCallback(async () => {
    await fetch('/api/v1/access/session', {
      method: 'DELETE',
    })
    setApiKeyState(null)
    setMaskedApiKey(null)
  }, [])

  if (!isHydrated) {
    return null
  }

  return (
    <ApiKeyContext.Provider
      value={{
        apiKey,
        maskedApiKey,
        setApiKey,
        clearApiKey,
        isAuthenticated: !!apiKey,
        isLoading: !isHydrated,
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
