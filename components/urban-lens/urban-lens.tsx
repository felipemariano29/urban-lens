'use client'

import { useCallback, useState } from 'react'

import { useHistory, useQuery, validateLsoaCode, validateReferenceMonth } from '@/hooks/use-urban-lens'
import type { HistoryItem, QueryFilters } from '@/lib/types'

import { QueryInput } from './query-input'
import { ResultsArea } from './results-area'
import { Sidebar } from './sidebar'
import { TopBar } from './top-bar'

const DEFAULT_FILTERS: QueryFilters = {
  crime_type: null,
  lsoa_code: null,
  reference_month: null,
}

const DEFAULT_TOP_K = 5

export function UrbanLens() {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<QueryFilters>(DEFAULT_FILTERS)
  const [topK, setTopK] = useState(DEFAULT_TOP_K)

  const { state, response, error, latency, executeQuery, restoreResult, reset } = useQuery()
  const { history, addToHistory, clearHistory } = useHistory()

  const isLsoaValid = !filters.lsoa_code || validateLsoaCode(filters.lsoa_code)
  const isMonthValid =
    !filters.reference_month || validateReferenceMonth(filters.reference_month)
  const canSubmit =
    query.trim().length > 0 &&
    isLsoaValid &&
    isMonthValid &&
    state !== 'loading'

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return

    addToHistory(query, filters, topK, null, null)

    const result = await executeQuery(query, filters, topK)
    if (!result) return

    addToHistory(query, filters, topK, result.response, result.latency)
  }, [canSubmit, query, filters, topK, addToHistory, executeQuery])

  const handleReset = useCallback(() => {
    reset()
  }, [reset])

  const handleRetry = useCallback(() => {
    if (query.trim()) {
      void executeQuery(query, filters, topK)
      return
    }

    reset()
  }, [query, filters, topK, executeQuery, reset])

  const handleHistorySelect = useCallback(
    (item: HistoryItem) => {
      setQuery(item.query)
      setFilters(item.filters)
      setTopK(item.topK)

      if (item.response) {
        restoreResult(item.response, item.latency)
        return
      }

      void executeQuery(item.query, item.filters, item.topK)
    },
    [executeQuery, restoreResult]
  )

  const isDisabled = state === 'loading'

  return (
    <div className="flex h-screen flex-col bg-background">
      <TopBar />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        <Sidebar
          filters={filters}
          onFiltersChange={setFilters}
          topK={topK}
          onTopKChange={setTopK}
          history={history}
          onHistorySelect={handleHistorySelect}
          onClearHistory={clearHistory}
          disabled={isDisabled}
        />

        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <div className="border-b bg-card p-6">
            <QueryInput
              value={query}
              onChange={setQuery}
              onSubmit={handleSubmit}
              disabled={isDisabled}
              autoFocus={state === 'idle'}
            />
          </div>

          <div className="flex-1 min-h-0 overflow-hidden p-6">
            <ResultsArea
              state={state}
              response={response}
              error={error}
              latency={latency}
              onReset={handleReset}
              onRetry={handleRetry}
            />
          </div>
        </main>
      </div>
    </div>
  )
}
