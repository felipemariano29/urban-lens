'use client'

import { useState, useCallback } from 'react'
import { TopBar } from './top-bar'
import { Sidebar } from './sidebar'
import { QueryInput } from './query-input'
import { ResultsArea } from './results-area'
import { useQuery, useHistory, validateLsoaCode, validateReferenceMonth } from '@/hooks/use-urban-lens'
import type { QueryFilters, HistoryItem } from '@/lib/types'

const DEFAULT_FILTERS: QueryFilters = {
  crime_type: null,
  lsoa_code: null,
  reference_month: null,
}

const DEFAULT_TOP_K = 5

export function UrbanLens() {
  // Estado do formulário
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<QueryFilters>(DEFAULT_FILTERS)
  const [topK, setTopK] = useState(DEFAULT_TOP_K)

  // Hooks
  const { state, results, error, latency, executeQuery, reset } = useQuery()
  const { history, addToHistory, clearHistory } = useHistory()

  // Validação
  const isLsoaValid = !filters.lsoa_code || validateLsoaCode(filters.lsoa_code)
  const isMonthValid =
    !filters.reference_month || validateReferenceMonth(filters.reference_month)
  const canSubmit =
    query.trim().length > 0 &&
    isLsoaValid &&
    isMonthValid &&
    state !== 'loading'

  // Handlers
  const handleSubmit = useCallback(() => {
    if (!canSubmit) return

    // Adicionar ao histórico
    addToHistory(query, filters)

    // Executar query
    executeQuery(query, filters, topK)
  }, [canSubmit, query, filters, topK, addToHistory, executeQuery])

  const handleReset = useCallback(() => {
    reset()
    // Mantém query e filtros
  }, [reset])

  const handleRetry = useCallback(() => {
    if (query.trim()) {
      executeQuery(query, filters, topK)
    } else {
      reset()
    }
  }, [query, filters, topK, executeQuery, reset])

  const handleHistorySelect = useCallback(
    (item: HistoryItem) => {
      setQuery(item.query)
      setFilters(item.filters)
    },
    []
  )

  const isDisabled = state === 'loading'

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Barra Superior */}
      <TopBar />

      {/* Conteúdo Principal */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
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

        {/* Área Principal */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Campo de Pergunta */}
          <div className="p-6 border-b bg-card">
            <QueryInput
              value={query}
              onChange={setQuery}
              onSubmit={handleSubmit}
              disabled={isDisabled}
              autoFocus={state === 'idle'}
            />
          </div>

          {/* Área de Resultados */}
          <div className="flex-1 overflow-hidden p-6">
            <ResultsArea
              state={state}
              results={results}
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
