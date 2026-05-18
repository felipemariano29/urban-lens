'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { useApiKey } from '@/contexts/api-key-context'
import {
  useAccessProfile,
  useAvailableModels,
  useHistory,
  useQuery,
  useUsageStats,
  validateLsoaCode,
  validateReferenceMonth,
} from '@/hooks/use-urban-lens'
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
const FALLBACK_CHAT_MODEL = 'llama3'

export function UrbanLens() {
  const { apiKey } = useApiKey()

  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<QueryFilters>(DEFAULT_FILTERS)
  const [topK, setTopK] = useState(DEFAULT_TOP_K)
  const [selectedModel, setSelectedModel] = useState(FALLBACK_CHAT_MODEL)

  const { state, response, error, latency, executeQuery, restoreResult, reset } = useQuery(apiKey)
  const { history, addToHistory, clearHistory } = useHistory()
  const { models, defaultChatModel, isLoading: isLoadingModels, needsApiKey } = useAvailableModels(apiKey)
  const { profile } = useAccessProfile(apiKey)
  const { usage } = useUsageStats(apiKey)
  const allowedModels = profile?.allowed_models ?? []
  const visibleModels = useMemo(
    () => (allowedModels.length > 0 ? models.filter((model) => allowedModels.includes(model.name)) : models),
    [allowedModels, models]
  )

  useEffect(() => {
    if (visibleModels.length === 0) {
      if (selectedModel !== defaultChatModel) setSelectedModel(defaultChatModel)
      return
    }

    const hasSelectedModel = visibleModels.some((model) => model.name === selectedModel)
    if (!hasSelectedModel) {
      setSelectedModel(visibleModels[0]?.name || defaultChatModel)
    }
  }, [defaultChatModel, selectedModel, visibleModels])

  useEffect(() => {
    const planMaxTopK = profile?.plan_max_top_k
    if (planMaxTopK && topK > planMaxTopK) {
      setTopK(planMaxTopK)
    }
  }, [profile?.plan_max_top_k, topK])

  const isLsoaValid = !filters.lsoa_code || validateLsoaCode(filters.lsoa_code)
  const isMonthValid = !filters.reference_month || validateReferenceMonth(filters.reference_month)
  const canSubmit = query.trim().length > 0 && isLsoaValid && isMonthValid && state !== 'loading'

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return

    addToHistory(query, filters, topK, selectedModel, null, null)

    const result = await executeQuery(query, filters, topK, selectedModel)
    if (!result) return

    addToHistory(query, filters, topK, selectedModel, result.response, result.latency)
  }, [addToHistory, canSubmit, executeQuery, filters, query, selectedModel, topK])

  const handleHistorySelect = useCallback(
    (item: HistoryItem) => {
      setQuery(item.query)
      setFilters(item.filters)
      setTopK(item.topK)
      setSelectedModel(item.model)

      if (item.response) {
        restoreResult(item.response, item.latency)
        return
      }

      void executeQuery(item.query, item.filters, item.topK, item.model)
    },
    [executeQuery, restoreResult]
  )

  const isDisabled = state === 'loading'

  return (
    <div className="flex min-h-screen flex-col bg-[radial-gradient(circle_at_top_left,_rgba(100,211,255,0.18),_transparent_30%),linear-gradient(180deg,#f4f7f8_0%,#eef3f6_52%,#f8fafb_100%)]">
      <TopBar />

      <div className="flex flex-1 flex-col lg:flex-row">
        <Sidebar
          filters={filters}
          onFiltersChange={setFilters}
          topK={topK}
          onTopKChange={setTopK}
          availableModels={visibleModels}
          selectedModel={selectedModel}
          onSelectedModelChange={setSelectedModel}
          isLoadingModels={isLoadingModels}
          needsApiKey={needsApiKey}
          profile={profile}
          usage={usage}
          history={history}
          onHistorySelect={handleHistorySelect}
          onClearHistory={clearHistory}
          disabled={isDisabled}
        />

        <main className="min-w-0 flex-1">
          <div className="mx-auto flex h-full max-w-[1520px] flex-col gap-6 px-4 py-5 lg:px-8 lg:py-6">
            <QueryInput
              value={query}
              onChange={setQuery}
              onSubmit={handleSubmit}
              disabled={isDisabled}
              autoFocus={state === 'idle'}
            />

            <div className="min-h-0 flex-1">
              <ResultsArea
                state={state}
                response={response}
                error={error}
                latency={latency}
                onReset={reset}
                onRetry={() => {
                  if (query.trim()) {
                    void executeQuery(query, filters, topK, selectedModel)
                    return
                  }
                  reset()
                }}
              />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
