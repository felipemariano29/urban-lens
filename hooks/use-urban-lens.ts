'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import useSWR from 'swr'
import type {
  AppState,
  QueryFilters,
  QueryResult,
  ChatQueryResponse,
  HealthResponse,
  HistoryItem,
} from '@/lib/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1'

// 15s timeout para busca semântica
const SEARCH_TIMEOUT_MS = 15_000

const fetcher = async (url: string) => {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`)
  return res.json()
}

// Hook para health check
export function useHealthCheck() {
  const { data, error, isLoading, mutate } = useSWR<HealthResponse>(
    `${API_BASE_URL}/health`,
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

  return { status, dependencies, isLoading, error, refresh: mutate }
}

// Monta o body da requisição omitindo filtros nulos
function buildRequestBody(
  query: string,
  filters: QueryFilters,
  topK: number,
  extra?: Record<string, unknown>
): Record<string, unknown> {
  const hasFilters = Object.values(filters).some((v) => v !== null)
  const body: Record<string, unknown> = { query, top_k: topK, ...extra }
  if (hasFilters) {
    body.filters = {
      ...(filters.crime_type ? { crime_type: filters.crime_type } : {}),
      ...(filters.lsoa_code ? { lsoa_code: filters.lsoa_code } : {}),
      ...(filters.reference_month ? { reference_month: filters.reference_month } : {}),
    }
  }
  return body
}

// Hook para busca semântica (POST /api/v1/query)
export function useQuery() {
  const [state, setState] = useState<AppState>('idle')
  const [results, setResults] = useState<QueryResult[]>([])
  const [error, setError] = useState<{ code: number; message: string } | null>(null)
  const [latency, setLatency] = useState<number | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const executeQuery = useCallback(
    async (query: string, filters: QueryFilters, topK: number) => {
      if (abortControllerRef.current) abortControllerRef.current.abort()
      abortControllerRef.current = new AbortController()

      let timedOut = false
      const timeoutId = setTimeout(() => {
        timedOut = true
        abortControllerRef.current?.abort()
      }, SEARCH_TIMEOUT_MS)

      setState('loading')
      setError(null)
      setResults([])
      setLatency(null)

      const startTime = performance.now()

      try {
        const body = buildRequestBody(query, filters, topK)

        const response = await fetch(`${API_BASE_URL}/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          signal: abortControllerRef.current.signal,
        })

        clearTimeout(timeoutId)
        setLatency(Math.round(performance.now() - startTime))

        if (!response.ok) {
          setError({ code: response.status, message: getErrorMessage(response.status) })
          setState('error')
          return
        }

        const data = await response.json()

        if (data.results && data.results.length > 0) {
          const sorted = [...data.results].sort(
            (a: QueryResult, b: QueryResult) => b.score - a.score
          )
          setResults(sorted)
          setState('results')
        } else {
          setResults([])
          setState('empty')
        }
      } catch (err) {
        clearTimeout(timeoutId)
        if (err instanceof Error && err.name === 'AbortError') {
          if (timedOut) {
            setLatency(Math.round(performance.now() - startTime))
            setError({ code: 504, message: 'Tempo limite de 15s excedido. Tente novamente.' })
            setState('error')
          }
          return
        }
        setLatency(Math.round(performance.now() - startTime))
        setError({ code: 500, message: 'Erro interno. Tente novamente em instantes.' })
        setState('error')
      }
    },
    []
  )

  const reset = useCallback(() => {
    if (abortControllerRef.current) abortControllerRef.current.abort()
    setState('idle')
    setResults([])
    setError(null)
    setLatency(null)
  }, [])

  useEffect(() => {
    return () => { abortControllerRef.current?.abort() }
  }, [])

  return { state, results, error, latency, executeQuery, reset }
}

// Hook para chat RAG (POST /api/v1/chat/query)
export function useChat() {
  const [state, setState] = useState<AppState>('idle')
  const [chatResponse, setChatResponse] = useState<ChatQueryResponse | null>(null)
  const [error, setError] = useState<{ code: number; message: string } | null>(null)
  const [latency, setLatency] = useState<number | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const executeChat = useCallback(
    async (query: string, filters: QueryFilters, topK: number) => {
      if (abortControllerRef.current) abortControllerRef.current.abort()
      abortControllerRef.current = new AbortController()

      // O proxy server já tem timeout de 60s; aqui usamos 65s como fallback no cliente
      let timedOut = false
      const timeoutId = setTimeout(() => {
        timedOut = true
        abortControllerRef.current?.abort()
      }, 65_000)

      setState('loading')
      setError(null)
      setChatResponse(null)
      setLatency(null)

      const startTime = performance.now()

      try {
        const body = buildRequestBody(query, filters, topK)

        const response = await fetch(`${API_BASE_URL}/chat/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          signal: abortControllerRef.current.signal,
        })

        clearTimeout(timeoutId)
        setLatency(Math.round(performance.now() - startTime))

        if (!response.ok) {
          setError({ code: response.status, message: getErrorMessage(response.status) })
          setState('error')
          return
        }

        const data: ChatQueryResponse = await response.json()
        setChatResponse(data)
        // Estado 'results' para ambos: answered e insufficient_evidence
        // O componente ChatArea diferencia via answer.status
        setState('results')
      } catch (err) {
        clearTimeout(timeoutId)
        if (err instanceof Error && err.name === 'AbortError') {
          if (timedOut) {
            setLatency(Math.round(performance.now() - startTime))
            setError({
              code: 504,
              message: 'O modelo demorou mais de 60s para responder. Tente uma pergunta mais simples.',
            })
            setState('error')
          }
          return
        }
        setLatency(Math.round(performance.now() - startTime))
        setError({ code: 500, message: 'Erro interno. Tente novamente em instantes.' })
        setState('error')
      }
    },
    []
  )

  const reset = useCallback(() => {
    if (abortControllerRef.current) abortControllerRef.current.abort()
    setState('idle')
    setChatResponse(null)
    setError(null)
    setLatency(null)
  }, [])

  useEffect(() => {
    return () => { abortControllerRef.current?.abort() }
  }, [])

  return { state, chatResponse, error, latency, executeChat, reset }
}

// Hook para histórico da sessão
export function useHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([])

  const addToHistory = useCallback((query: string, filters: QueryFilters) => {
    setHistory((prev: HistoryItem[]) => {
      const newItem: HistoryItem = {
        id: crypto.randomUUID(),
        query,
        filters,
        timestamp: new Date(),
      }
      return [newItem, ...prev].slice(0, 10)
    })
  }, [])

  const clearHistory = useCallback(() => setHistory([]), [])

  return { history, addToHistory, clearHistory }
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
    case 504:
      return 'Tempo limite excedido. O backend não respondeu a tempo.'
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
