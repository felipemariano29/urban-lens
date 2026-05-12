'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ResultCard } from './result-card'
import type { AppState, QueryResult } from '@/lib/types'
import { 
  SearchIcon, 
  AlertTriangleIcon, 
  RotateCcwIcon,
  DiamondIcon,
  PlusCircleIcon 
} from 'lucide-react'

interface ResultsAreaProps {
  state: AppState
  results: QueryResult[]
  error: { code: number; message: string } | null
  latency: number | null
  onReset: () => void
  onRetry: () => void
}

const INITIAL_DISPLAY_COUNT = 5

export function ResultsArea({
  state,
  results,
  error,
  latency,
  onReset,
  onRetry,
}: ResultsAreaProps) {
  const [displayCount, setDisplayCount] = useState(INITIAL_DISPLAY_COUNT)

  const showMore = () => {
    setDisplayCount((prev) => Math.min(prev + 5, results.length))
  }

  // Estado: idle
  if (state === 'idle') {
    return <IdleState />
  }

  // Estado: loading
  if (state === 'loading') {
    return <LoadingState />
  }

  // Estado: error
  if (state === 'error') {
    return <ErrorState error={error} onRetry={onRetry} />
  }

  // Estado: empty
  if (state === 'empty') {
    return <EmptyState onReset={onReset} />
  }

  // Estado: results
  const displayedResults = results.slice(0, displayCount)
  const hasMore = displayCount < results.length

  return (
    <div className="flex flex-col h-full">
      {/* Header com estatísticas */}
      <div className="flex items-center justify-between pb-4 border-b mb-4">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold text-lg">Resultados Encontrados</h2>
          <span className="text-sm text-muted-foreground">
            {results.length} {results.length === 1 ? 'chunk' : 'chunks'}
            {latency && ` · ${latency}ms`}
          </span>
        </div>
        <Button variant="outline" size="sm" onClick={onReset}>
          <PlusCircleIcon className="size-4" />
          Nova pergunta
        </Button>
      </div>

      {/* Lista de resultados */}
      <ScrollArea className="flex-1 -mx-2 px-2">
        <div className="space-y-4 pb-4">
          {displayedResults.map((result, index) => (
            <ResultCard key={result.id} result={result} rank={index + 1} />
          ))}

          {hasMore && (
            <div className="flex justify-center pt-2">
              <Button variant="ghost" onClick={showMore}>
                + Ver mais resultados ({results.length - displayCount} restantes)
              </Button>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

function IdleState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="mb-6">
        <DiamondIcon className="size-12 text-muted-foreground/50 mx-auto" />
      </div>
      <h3 className="text-lg font-medium mb-2">
        Faça uma pergunta para começar
      </h3>
      <p className="text-muted-foreground text-sm mb-6 max-w-md">
        Use linguagem natural para consultar os dados de segurança urbana.
      </p>
      <div className="space-y-2 text-sm text-muted-foreground">
        <p className="font-medium text-foreground/80">Exemplos:</p>
        <ul className="space-y-1.5">
          <li className="flex items-center gap-2">
            <SearchIcon className="size-3" />
            {`"Burglaries in Westminster in January 2024"`}
          </li>
          <li className="flex items-center gap-2">
            <SearchIcon className="size-3" />
            {`"Crime trends in LSOA E01001234 in 2023"`}
          </li>
          <li className="flex items-center gap-2">
            <SearchIcon className="size-3" />
            {`"Most common crime types in 2024"`}
          </li>
        </ul>
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <div className="flex items-center gap-3 mb-3">
        <Spinner className="size-5" />
        <span className="font-medium">Processando consulta...</span>
      </div>
      <p className="text-muted-foreground text-sm">
        Buscando nos dados de segurança urbana
      </p>
    </div>
  )
}

function ErrorState({
  error,
  onRetry,
}: {
  error: { code: number; message: string } | null
  onRetry: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="mb-6">
        <AlertTriangleIcon className="size-12 text-amber-500 mx-auto" />
      </div>
      <h3 className="text-lg font-medium mb-2">Erro ao processar a consulta</h3>
      <p className="text-muted-foreground text-sm mb-6 max-w-md">
        {error?.message || 'Ocorreu um erro inesperado.'}
      </p>
      <Button variant="outline" onClick={onRetry}>
        <RotateCcwIcon className="size-4" />
        Tentar novamente
      </Button>
    </div>
  )
}

function EmptyState({ onReset }: { onReset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="mb-6">
        <DiamondIcon className="size-12 text-muted-foreground/30 mx-auto" strokeWidth={1} />
      </div>
      <h3 className="text-lg font-medium mb-2">
        Nenhum dado relevante encontrado
      </h3>
      <div className="text-muted-foreground text-sm mb-6 max-w-md space-y-3">
        <p>Tente:</p>
        <ul className="text-left space-y-1.5 list-disc list-inside">
          <li>Reformular a pergunta</li>
          <li>Usar termos em inglês (ex: {`"Burglary"`})</li>
          <li>Remover ou ampliar os filtros</li>
          <li>Aumentar o top-k no painel de filtros</li>
        </ul>
      </div>
      <Button variant="outline" onClick={onReset}>
        Nova pergunta
      </Button>
    </div>
  )
}
