'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import useSWR from 'swr'
import type {
  AppState,
  QueryFilters,
  QueryResult,
  HealthResponse,
  HistoryItem,
} from '@/lib/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1'

// Fetcher para SWR
const fetcher = async (url: string) => {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`)
  }
  return res.json()
}

// Hook para health check
export function useHealthCheck() {
  const { data, error, isLoading, mutate } = useSWR<HealthResponse>(
    `${API_BASE_URL}/health`,
    fetcher,
    {
      refreshInterval: 60000, // Poll a cada 60 segundos
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

// Hook principal para queries
export function useQuery() {
  const [state, setState] = useState<AppState>('idle')
  const [results, setResults] = useState<QueryResult[]>([])
  const [error, setError] = useState<{ code: number; message: string } | null>(null)
  const [latency, setLatency] = useState<number | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const executeQuery = useCallback(
    async (query: string, filters: QueryFilters, topK: number) => {
      // Cancelar requisição anterior se existir
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      abortControllerRef.current = new AbortController()

      setState('loading')
      setError(null)
      setResults([])
      setLatency(null)

      const startTime = performance.now()

      try {
        // Montar body - omitir filters se todos forem null
        const hasFilters = Object.values(filters).some((v) => v !== null)
        const body: Record<string, unknown> = {
          query,
          top_k: topK,
        }

        if (hasFilters) {
          body.filters = {
            crime_type: filters.crime_type || undefined,
            lsoa_code: filters.lsoa_code || undefined,
            reference_month: filters.reference_month || undefined,
          }
        }

        const response = await fetch(`${API_BASE_URL}/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
          signal: abortControllerRef.current.signal,
        })

        const endTime = performance.now()
        setLatency(Math.round(endTime - startTime))

        if (!response.ok) {
          const errorMessage = getErrorMessage(response.status)
          setError({ code: response.status, message: errorMessage })
          setState('error')
          return
        }

        const data = await response.json()

        if (data.results && data.results.length > 0) {
          // Ordenar por score decrescente
          const sortedResults = [...data.results].sort(
            (a: QueryResult, b: QueryResult) => b.score - a.score
          )
          setResults(sortedResults)
          setState('results')
        } else {
          setResults([])
          setState('empty')
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return
        }

        const endTime = performance.now()
        setLatency(Math.round(endTime - startTime))

        setError({
          code: 500,
          message: 'Erro interno. Tente novamente em instantes.',
        })
        setState('error')
      }
    },
    []
  )

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setState('idle')
    setResults([])
    setError(null)
    setLatency(null)
  }, [])

  // Cleanup ao desmontar
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return {
    state,
    results,
    error,
    latency,
    executeQuery,
    reset,
  }
}

// Hook para histórico da sessão
export function useHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([])

  const addToHistory = useCallback((query: string, filters: QueryFilters) => {
    setHistory((prev) => {
      const newItem: HistoryItem = {
        id: crypto.randomUUID(),
        query,
        filters,
        timestamp: new Date(),
      }

      // Manter apenas as últimas 10 perguntas
      const updated = [newItem, ...prev].slice(0, 10)
      return updated
    })
  }, [])

  const clearHistory = useCallback(() => {
    setHistory([])
  }, [])

  return {
    history,
    addToHistory,
    clearHistory,
  }
}

// Helper para mensagens de erro
function getErrorMessage(code: number): string {
  switch (code) {
    case 401:
      return 'Sessão expirada. Atualize a página para continuar.'
    case 403:
      return 'Você não tem permissão para realizar esta consulta.'
    case 422:
      return 'Consulta inválida. Verifique os filtros e tente novamente.'
    case 502:
      return 'Serviço de busca indisponível. Verifique se o Milvus e o Ollama estão rodando.'
    default:
      return 'Erro interno. Tente novamente em instantes.'
  }
}

// Validadores
export function validateLsoaCode(code: string): boolean {
  if (!code) return true
  return /^E\d{8}$/.test(code)
}

export function validateReferenceMonth(month: string): boolean {
  if (!month) return true
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(month)
}
