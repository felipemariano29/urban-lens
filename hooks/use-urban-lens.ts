'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import useSWR from 'swr'

import { buildBackendApiUrl } from '@/lib/api/client'
import type {
  AvailableModelsResponse,
  AppState,
  ChatQueryResponse,
  QueryFilters,
  HealthResponse,
  HistoryItem,
} from '@/lib/types'

const HISTORY_STORAGE_KEY = 'urban-lens:query-history'
const HISTORY_LIMIT = 10
const API_KEY_STORAGE_KEY = 'urban-lens:api-key'

// Helper to get stored API key
function getStoredApiKey(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(API_KEY_STORAGE_KEY)
}

// Fetcher para SWR com API key
const createFetcher = (apiKey: string | null) => async (url: string) => {
  const headers: HeadersInit = {}
  if (apiKey) {
    headers['X-API-Key'] = apiKey
  }
  
  const res = await fetch(url, { headers })
  if (!res.ok) {
    const error = new Error(`HTTP error! status: ${res.status}`)
    ;(error as Error & { status: number }).status = res.status
    throw error
  }
  return res.json()
}

// Hook para health check
export function useHealthCheck(apiKey: string | null = null) {
  const effectiveKey = apiKey ?? getStoredApiKey()
  const fetcher = createFetcher(effectiveKey)
  
  const { data, error, isLoading, mutate } = useSWR<HealthResponse>(
    buildBackendApiUrl('/health'),
    fetcher,
    {
      refreshInterval: 60000,
      revalidateOnFocus: false,
      shouldRetryOnError: true,
      errorRetryCount: 3,
    }
  )

  const status = error ? 'error' : data?.status || 'unknown'
  const dependencies = data?.dependencies || null

  return {
    status,
    dependencies,
    isLoading,
    error,
    refresh: mutate,
  }
}

export function useAvailableModels(apiKey: string | null = null) {
  const effectiveKey = apiKey ?? getStoredApiKey()
  const fetcher = createFetcher(effectiveKey)
  
  const { data, error, isLoading, mutate } = useSWR<AvailableModelsResponse>(
    effectiveKey ? buildBackendApiUrl('/system/models') : null,
    fetcher,
    {
      revalidateOnFocus: false,
      shouldRetryOnError: true,
      errorRetryCount: 2,
    }
  )

  return {
    models: data?.models ?? [],
    defaultChatModel: data?.default_chat_model ?? 'llama3',
    defaultEmbeddingModel: data?.default_embedding_model ?? 'nomic-embed-text',
    isLoading,
    error,
    needsApiKey: !effectiveKey,
    refresh: mutate,
  }
}

// Hook principal para queries
export function useQuery(apiKey: string | null = null) {
  const [state, setState] = useState<AppState>('idle')
  const [response, setResponse] = useState<ChatQueryResponse | null>(null)
  const [error, setError] = useState<{ code: number; message: string } | null>(null)
  const [latency, setLatency] = useState<number | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const executeQuery = useCallback(
    async (query: string, filters: QueryFilters, topK: number, model: string) => {
      const effectiveKey = apiKey ?? getStoredApiKey()
      
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      abortControllerRef.current = new AbortController()

      setState('loading')
      setError(null)
      setResponse(null)
      setLatency(null)

      const startTime = performance.now()

      try {
        const hasFilters = Object.values(filters).some((value) => value !== null)
        const body: Record<string, unknown> = {
          query,
          top_k: topK,
          model,
        }

        if (hasFilters) {
          body.filters = {
            ...(filters.crime_type ? { crime_type: filters.crime_type } : {}),
            ...(filters.lsoa_code ? { lsoa_code: filters.lsoa_code } : {}),
            ...(filters.reference_month
              ? { reference_month: filters.reference_month }
              : {}),
          }
        }

        const headers: HeadersInit = {
          'Content-Type': 'application/json',
        }
        if (effectiveKey) {
          headers['X-API-Key'] = effectiveKey
        }

        const apiResponse = await fetch(buildBackendApiUrl('/chat/query'), {
          method: 'POST',
          headers,
          body: JSON.stringify(body),
          signal: abortControllerRef.current.signal,
        })

        const endTime = performance.now()
        setLatency(Math.round(endTime - startTime))

        if (!apiResponse.ok) {
          setError({
            code: apiResponse.status,
            message: getErrorMessage(apiResponse.status),
          })
          setState('error')
          return null
        }

        const data: ChatQueryResponse = await apiResponse.json()
        setResponse(data)
        setState('results')
        return {
          response: data,
          latency: Math.round(endTime - startTime),
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return null
        }

        const endTime = performance.now()
        setLatency(Math.round(endTime - startTime))

        setError({
          code: 500,
          message: 'Erro interno. Tente novamente em instantes.',
        })
        setState('error')
        return null
      }
    },
    [apiKey]
  )

  const restoreResult = useCallback(
    (storedResponse: ChatQueryResponse, storedLatency: number | null = null) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      setResponse(storedResponse)
      setLatency(storedLatency)
      setError(null)
      setState('results')
    },
    []
  )

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setState('idle')
    setResponse(null)
    setError(null)
    setLatency(null)
  }, [])

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return {
    state,
    response,
    error,
    latency,
    executeQuery,
    restoreResult,
    reset,
  }
}

// Hook para historico persistido no navegador
export function useHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([])
  const hasLoadedHistoryRef = useRef(false)

  useEffect(() => {
    try {
      const rawHistory = window.localStorage.getItem(HISTORY_STORAGE_KEY)
      if (!rawHistory) {
        hasLoadedHistoryRef.current = true
        return
      }

      const parsedHistory = JSON.parse(rawHistory)
      if (!Array.isArray(parsedHistory)) {
        hasLoadedHistoryRef.current = true
        return
      }

      const normalizedHistory = parsedHistory
        .filter(
          (
            item
          ): item is Omit<HistoryItem, 'timestamp' | 'model'> & {
            timestamp: string
            model?: string
          } => {
          return (
            typeof item === 'object' &&
            item !== null &&
            typeof item.id === 'string' &&
            typeof item.query === 'string' &&
            typeof item.timestamp === 'string' &&
            typeof item.filters === 'object' &&
            item.filters !== null
          )
        })
        .map((item) => ({
          ...item,
          topK: typeof item.topK === 'number' ? item.topK : 5,
          model: typeof item.model === 'string' ? item.model : 'llama3',
          latency: typeof item.latency === 'number' ? item.latency : null,
          response:
            typeof item.response === 'object' && item.response !== null
              ? item.response
              : null,
          timestamp: new Date(item.timestamp),
        }))
        .filter((item) => !Number.isNaN(item.timestamp.getTime()))
        .slice(0, HISTORY_LIMIT)

      setHistory(normalizedHistory)
    } catch {
      window.localStorage.removeItem(HISTORY_STORAGE_KEY)
    } finally {
      hasLoadedHistoryRef.current = true
    }
  }, [])

  useEffect(() => {
    if (!hasLoadedHistoryRef.current) {
      return
    }

    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history))
  }, [history])

  const addToHistory = useCallback(
    (
      query: string,
      filters: QueryFilters,
      topK: number,
      model: string,
      response: ChatQueryResponse | null,
      latency: number | null
    ) => {
      setHistory((prev) => {
        const nextHistory = prev.filter(
          (item) =>
            !(
              item.query === query &&
              item.topK === topK &&
              item.model === model &&
              JSON.stringify(item.filters) === JSON.stringify(filters)
            )
        )

        const newItem: HistoryItem = {
          id: crypto.randomUUID(),
          query,
          filters,
          topK,
          model,
          response,
          latency,
          timestamp: new Date(),
        }

        return [newItem, ...nextHistory].slice(0, HISTORY_LIMIT)
      })
    },
    []
  )

  const clearHistory = useCallback(() => {
    setHistory([])
  }, [])

  return {
    history,
    addToHistory,
    clearHistory,
  }
}

function getErrorMessage(code: number): string {
  switch (code) {
    case 401:
      return 'Sessao expirada. Atualize a pagina para continuar.'
    case 403:
      return 'Voce nao tem permissao para realizar esta consulta.'
    case 422:
      return 'Consulta invalida. Verifique os filtros e tente novamente.'
    case 502:
      return 'API RAG indisponivel. Verifique FastAPI, Milvus e Ollama.'
    default:
      return 'Erro interno. Tente novamente em instantes.'
  }
}

export function validateLsoaCode(code: string): boolean {
  if (!code) return true
  return /^E\d{8}$/.test(code)
}

export function validateReferenceMonth(month: string): boolean {
  if (!month) return true
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(month)
}
