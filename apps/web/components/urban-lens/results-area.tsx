'use client'

import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ResultCard } from './result-card'
import type { AppState, ChatQueryResponse } from '@/lib/types'
import {
  extractCrimeTypesFromAnswer,
  formatProfilePt,
  normalizeAnswerText,
  summarizeEvidence,
} from '@/lib/presentation'
import {
  SearchIcon,
  AlertTriangleIcon,
  RotateCcwIcon,
  DiamondIcon,
  PlusCircleIcon,
  ShieldAlertIcon,
  FileSearchIcon,
} from 'lucide-react'

interface ResultsAreaProps {
  state: AppState
  response: ChatQueryResponse | null
  error: { code: number; message: string } | null
  latency: number | null
  onReset: () => void
  onRetry: () => void
}

const INITIAL_DISPLAY_COUNT = 5

export function ResultsArea({
  state,
  response,
  error,
  latency,
  onReset,
  onRetry,
}: ResultsAreaProps) {
  const [displayCount, setDisplayCount] = useState(INITIAL_DISPLAY_COUNT)

  useEffect(() => {
    setDisplayCount(INITIAL_DISPLAY_COUNT)
  }, [response?.answer.text])

  const showMore = () => {
    if (!response) return
    setDisplayCount((prev) => Math.min(prev + 5, response.evidences.length))
  }

  if (state === 'idle') {
    return <IdleState />
  }

  if (state === 'loading') {
    return <LoadingState />
  }

  if (state === 'error') {
    return <ErrorState error={error} onRetry={onRetry} />
  }

  if (!response) {
    return <EmptyState onReset={onReset} />
  }

  const displayedEvidences = response.evidences.slice(0, displayCount)
  const hasMore = displayCount < response.evidences.length
  const isFallback = response.answer.status === 'insufficient_evidence'
  const evidenceSummary = summarizeEvidence(response)
  const answerCrimeTypes = extractCrimeTypesFromAnswer(response.answer.text)
  const pipelineTimings = response.timings_ms

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between pb-4 border-b mb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-lg">Resposta RAG</h2>
            <Badge variant={isFallback ? 'outline' : 'secondary'}>
              {isFallback ? 'evidencia insuficiente' : 'respondida'}
            </Badge>
          </div>
          <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
            <span>{response.evidences.length} evidencia(s)</span>
            <span>{response.context.length} chunk(s) recuperado(s)</span>
            <span>perfil {formatProfilePt(response.profile)}</span>
            <span>modelo {response.answer.model}</span>
            <span>pipeline {pipelineTimings.total_ms}ms</span>
            {latency && <span>roundtrip {latency}ms</span>}
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={onReset}>
          <PlusCircleIcon className="size-4" />
          Nova pergunta
        </Button>
      </div>

      <ScrollArea className="flex-1 min-h-0 -mx-2 px-2">
        <div className="space-y-4 pb-4">
          <Card className="py-4">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                {isFallback ? (
                  <ShieldAlertIcon className="size-5 text-amber-600" />
                ) : (
                  <FileSearchIcon className="size-5 text-primary" />
                )}
                <CardTitle className="text-base">Resposta gerada</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-0 space-y-3">
              <AnswerSummary response={response} />
              <TimingSummary timings={pipelineTimings} />
              <FormattedAnswer text={response.answer.text} />
              {answerCrimeTypes.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Tipos de crime citados
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {answerCrimeTypes.slice(0, 6).map((crimeType) => (
                      <Badge key={crimeType} variant="outline" className="bg-primary/5">
                        {crimeType}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {response.fallback_reason && (
                <p className="text-xs text-muted-foreground">
                  Motivo tecnico: {response.fallback_reason}
                </p>
              )}
            </CardContent>
          </Card>

          {displayedEvidences.map((evidence, index) => (
            <ResultCard key={evidence.id} evidence={evidence} rank={index + 1} />
          ))}

          {response.evidences.length === 0 && (
            <Card className="py-4">
              <CardContent className="pt-0">
                <p className="text-sm text-muted-foreground">
                  Nenhuma evidencia autorizada foi retornada pela API para esta consulta.
                </p>
              </CardContent>
            </Card>
          )}

          {hasMore && (
            <div className="flex justify-center pt-2">
              <Button variant="ghost" onClick={showMore}>
                + Ver mais evidencias ({response.evidences.length - displayCount} restantes)
              </Button>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

function AnswerSummary({ response }: { response: ChatQueryResponse }) {
  const summary = summarizeEvidence(response)

  return (
    <div className="grid gap-2 rounded-lg border bg-muted/30 p-3 text-sm md:grid-cols-3">
      <SummaryBlock
        label="Periodo"
        value={summary.months.length > 0 ? summary.months.join(', ') : 'Nao identificado'}
      />
      <SummaryBlock
        label="Escopo das evidencias"
        value={summary.chunkTypes.length > 0 ? summary.chunkTypes.slice(0, 2).join(' | ') : 'Nao identificado'}
      />
      <SummaryBlock
        label="Areas citadas"
        value={summary.lsoaCodes.length > 0 ? summary.lsoaCodes.slice(0, 3).join(', ') : 'Nao identificado'}
      />
    </div>
  )
}

function TimingSummary({ timings }: { timings: ChatQueryResponse['timings_ms'] }) {
  return (
    <div className="grid gap-2 rounded-lg border bg-muted/30 p-3 text-sm md:grid-cols-4">
      <SummaryBlock label="Pipeline" value={`${timings.total_ms} ms`} />
      <SummaryBlock label="Embedding" value={`${timings.embedding_ms} ms`} />
      <SummaryBlock label="Retrieval" value={`${timings.retrieval_ms} ms`} />
      <SummaryBlock label="Geracao" value={`${timings.generation_ms} ms`} />
    </div>
  )
}

function SummaryBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="text-sm font-medium text-foreground/90">{value}</p>
    </div>
  )
}

function FormattedAnswer({ text }: { text: string }) {
  const normalized = normalizeAnswerText(text)
  const lines = normalized
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  const blocks: Array<{ type: 'paragraph' | 'list'; items: string[] }> = []

  for (const line of lines) {
    const isListItem = /^[-*]\s+/.test(line)
    const content = line.replace(/^[-*]\s+/, '')
    const lastBlock = blocks[blocks.length - 1]

    if (isListItem) {
      if (lastBlock?.type === 'list') {
        lastBlock.items.push(content)
      } else {
        blocks.push({ type: 'list', items: [content] })
      }
      continue
    }

    blocks.push({ type: 'paragraph', items: [content] })
  }

  return (
    <div className="space-y-3">
      {blocks.map((block, index) =>
        block.type === 'list' ? (
          <ul key={index} className="list-disc space-y-1 pl-5 text-sm leading-7 text-foreground/90">
            {block.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : (
          <p key={index} className="text-sm leading-7 text-foreground/90 whitespace-pre-wrap">
            {block.items[0]}
          </p>
        )
      )}
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
        Faca uma pergunta para comecar
      </h3>
      <p className="text-muted-foreground text-sm mb-6 max-w-md">
        Use linguagem natural para consultar os dados de seguranca urbana.
      </p>
      <div className="space-y-2 text-sm text-muted-foreground">
        <p className="font-medium text-foreground/80">Exemplos:</p>
        <ul className="space-y-1.5">
          <li className="flex items-center gap-2">
            <SearchIcon className="size-3" />
            {'"Quais evidencias sustentam burglary em Westminster em 2024-01?"'}
          </li>
          <li className="flex items-center gap-2">
            <SearchIcon className="size-3" />
            {'"Qual foi o tipo de crime dominante na area E01001234?"'}
          </li>
          <li className="flex items-center gap-2">
            <SearchIcon className="size-3" />
            {'"Resuma o panorama de criminalidade de 2024-01"'}
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
        <span className="font-medium">Consultando a API RAG...</span>
      </div>
      <p className="text-muted-foreground text-sm">
        Recuperando evidencias e gerando resposta baseada no contexto
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
          <li>Informar regiao, mes ou tipo de crime</li>
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
