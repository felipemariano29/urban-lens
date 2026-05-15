'use client'

import { useState, useCallback } from 'react'
import { TopBar } from './top-bar'
import { Sidebar } from './sidebar'
import { QueryInput } from './query-input'
import { ResultsArea } from './results-area'
import { ChatArea } from './chat-area'
import { useQuery, useChat, useHistory, validateLsoaCode, validateReferenceMonth } from '@/hooks/use-urban-lens'
import type { QueryFilters, HistoryItem, QueryMode } from '@/lib/types'

const DEFAULT_FILTERS: QueryFilters = {
  crime_type: null,
  lsoa_code: null,
  reference_month: null,
}

const DEFAULT_TOP_K = 5

export function UrbanLens() {
  const [mode, setMode] = useState<QueryMode>('search')
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<QueryFilters>(DEFAULT_FILTERS)
  const [topK, setTopK] = useState(DEFAULT_TOP_K)

  const search = useQuery()
  const chat = useChat()
  const { history, addToHistory, clearHistory } = useHistory()

  const active = mode === 'search' ? search : chat

  const isLsoaValid = !filters.lsoa_code || validateLsoaCode(filters.lsoa_code)
  const isMonthValid = !filters.reference_month || validateReferenceMonth(filters.reference_month)
  const canSubmit =
    query.trim().length > 0 && isLsoaValid && isMonthValid && active.state !== 'loading'

  const handleSubmit = useCallback(() => {
    if (!canSubmit) return
    addToHistory(query, filters)
    if (mode === 'search') {
      search.executeQuery(query, filters, topK)
    } else {
      chat.executeChat(query, filters, topK)
    }
  }, [canSubmit, mode, query, filters, topK, addToHistory, search, chat])

  const handleReset = useCallback(() => {
    active.reset()
  }, [active])

  const handleRetry = useCallback(() => {
    if (!query.trim()) {
      active.reset()
      return
    }
    if (mode === 'search') {
      search.executeQuery(query, filters, topK)
    } else {
      chat.executeChat(query, filters, topK)
    }
  }, [mode, query, filters, topK, search, chat, active])

  const handleHistorySelect = useCallback((item: HistoryItem) => {
    setQuery(item.query)
    setFilters(item.filters)
  }, [])

  const handleModeChange = useCallback((newMode: QueryMode) => {
    setMode(newMode)
    // Reset do modo anterior para não exibir resultado obsoleto
    if (newMode === 'search') {
      chat.reset()
    } else {
      search.reset()
    }
  }, [search, chat])

  const isDisabled = active.state === 'loading'

  return (
    <div className="flex flex-col h-screen bg-background">
      <TopBar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          mode={mode}
          onModeChange={handleModeChange}
          filters={filters}
          onFiltersChange={setFilters}
          topK={topK}
          onTopKChange={setTopK}
          history={history}
          onHistorySelect={handleHistorySelect}
          onClearHistory={clearHistory}
          disabled={isDisabled}
        />

        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="p-6 border-b bg-card">
            <QueryInput
              value={query}
              onChange={setQuery}
              onSubmit={handleSubmit}
              disabled={isDisabled}
              autoFocus={active.state === 'idle'}
            />
          </div>

          <div className="flex-1 overflow-hidden p-6">
            {mode === 'chat' && chat.state === 'results' && chat.chatResponse ? (
              <ChatArea
                response={chat.chatResponse}
                latency={chat.latency}
                onReset={handleReset}
              />
            ) : (
              <ResultsArea
                state={active.state}
                results={mode === 'search' ? search.results : []}
                error={active.error}
                latency={active.latency}
                onReset={handleReset}
                onRetry={handleRetry}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
