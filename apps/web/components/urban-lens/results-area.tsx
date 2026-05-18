'use client'

import { useEffect, useState } from 'react'
import {
  AlertTriangleIcon,
  ArrowUpRightIcon,
  CircleDashedIcon,
  FileSearchIcon,
  LayoutTemplateIcon,
  RefreshCcwIcon,
  ShieldAlertIcon,
  SparklesIcon,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Spinner } from '@/components/ui/spinner'
import { ResultCard } from './result-card'
import type { AppState, ChatQueryResponse } from '@/lib/types'
import {
  extractCrimeTypesFromAnswer,
  formatProfilePt,
  normalizeAnswerText,
  summarizeEvidence,
} from '@/lib/presentation'

interface ResultsAreaProps {
  state: AppState
  response: ChatQueryResponse | null
  error: { code: number; message: string } | null
  latency: number | null
  onReset: () => void
  onRetry: () => void
}

const INITIAL_DISPLAY_COUNT = 5

export function ResultsArea({ state, response, error, latency, onReset, onRetry }: ResultsAreaProps) {
  const [displayCount, setDisplayCount] = useState(INITIAL_DISPLAY_COUNT)

  useEffect(() => {
    setDisplayCount(INITIAL_DISPLAY_COUNT)
  }, [response?.answer.text])

  if (state === 'idle') return <IdleState />
  if (state === 'loading') return <LoadingState />
  if (state === 'error') return <ErrorState error={error} onRetry={onRetry} />
  if (!response) return <EmptyState onReset={onReset} />

  const displayedEvidences = response.evidences.slice(0, displayCount)
  const hasMore = displayCount < response.evidences.length
  const isFallback = response.answer.status === 'insufficient_evidence'
  const summary = summarizeEvidence(response)
  const crimeTypes = extractCrimeTypesFromAnswer(response.answer.text)

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <Card className="border-black/5 bg-white/90 py-5 shadow-[0_14px_50px_rgba(12,26,41,0.06)]">
          <CardHeader className="pb-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={isFallback ? 'outline' : 'secondary'}>
                    {isFallback ? 'evidencia insuficiente' : 'analise respondida'}
                  </Badge>
                  <Badge variant="outline">{response.answer.model}</Badge>
                  <Badge variant="outline">perfil {formatProfilePt(response.profile)}</Badge>
                </div>
                <CardTitle className="text-xl tracking-tight text-[#112231]">
                  Sintese investigativa governada
                </CardTitle>
                <p className="text-sm text-slate-600">
                  Resposta gerada com citacao de evidencias e trilha de execucao do pipeline RAG.
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={onReset} className="gap-2 rounded-full">
                <RefreshCcwIcon className="size-4" />
                Nova consulta
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-0">
            <InsightGrid
              totalEvidence={response.evidences.length}
              totalContext={response.context.length}
              latency={latency}
              timings={response.timings_ms}
            />
            <AnswerSummaryCard response={response} />
            <AnswerBody text={response.answer.text} />
            {crimeTypes.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Crime types cited</p>
                <div className="flex flex-wrap gap-2">
                  {crimeTypes.slice(0, 8).map((crimeType) => (
                    <Badge key={crimeType} variant="outline" className="bg-[#f8fafc]">
                      {crimeType}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-black/5 bg-[#122333] py-5 text-white shadow-[0_14px_50px_rgba(12,26,41,0.08)]">
          <CardHeader className="pb-4">
            <div className="flex items-center gap-2">
              <LayoutTemplateIcon className="size-5 text-[#64d3ff]" />
              <CardTitle className="text-lg">Operational frame</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-0 text-sm text-slate-200">
            <StatRow label="Periodo(s)" value={summary.months.length > 0 ? summary.months.join(', ') : 'nao identificado'} />
            <StatRow
              label="Areas"
              value={summary.lsoaCodes.length > 0 ? summary.lsoaCodes.slice(0, 3).join(', ') : 'nao identificado'}
            />
            <StatRow
              label="Chunk types"
              value={summary.chunkTypes.length > 0 ? summary.chunkTypes.slice(0, 3).join(', ') : 'nao identificado'}
            />
            {response.fallback_reason && (
              <div className="rounded-2xl border border-amber-400/20 bg-amber-400/10 p-3 text-amber-100">
                <div className="mb-1 flex items-center gap-2 font-medium">
                  <ShieldAlertIcon className="size-4" />
                  Fallback governado
                </div>
                <p className="text-sm">{response.fallback_reason}</p>
              </div>
            )}
            <div className="rounded-2xl border border-white/10 bg-white/6 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Pipeline timings</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <TimingPill label="Embedding" value={response.timings_ms.embedding_ms} />
                <TimingPill label="Retrieval" value={response.timings_ms.retrieval_ms} />
                <TimingPill label="Generation" value={response.timings_ms.generation_ms} />
                <TimingPill label="End-to-end" value={response.timings_ms.total_ms} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="min-h-0 flex-1 border-black/5 bg-white/90 py-5 shadow-[0_14px_50px_rgba(12,26,41,0.06)]">
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <FileSearchIcon className="size-5 text-[#0e5973]" />
                <CardTitle className="text-lg text-[#112231]">Evidence ledger</CardTitle>
              </div>
              <p className="text-sm text-slate-600">
                Evidencias efetivamente citadas para sustentar a resposta retornada ao operador.
              </p>
            </div>
            <Badge variant="outline">{response.evidences.length} evidencia(s)</Badge>
          </div>
        </CardHeader>
        <CardContent className="min-h-0 pt-0">
          <ScrollArea className="h-[420px] pr-3">
            <div className="space-y-4">
              {displayedEvidences.map((evidence, index) => (
                <ResultCard key={evidence.id} evidence={evidence} rank={index + 1} />
              ))}

              {response.evidences.length === 0 && (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                  Nenhuma evidencia autorizada foi retornada para esta consulta.
                </div>
              )}

              {hasMore && (
                <div className="flex justify-center pt-2">
                  <Button variant="ghost" onClick={() => setDisplayCount((prev) => Math.min(prev + 5, response.evidences.length))}>
                    Mostrar mais evidencias
                  </Button>
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}

function InsightGrid({
  totalEvidence,
  totalContext,
  latency,
  timings,
}: {
  totalEvidence: number
  totalContext: number
  latency: number | null
  timings: ChatQueryResponse['timings_ms']
}) {
  const items = [
    { label: 'Evidencias', value: String(totalEvidence) },
    { label: 'Chunks recuperados', value: String(totalContext) },
    { label: 'Pipeline', value: `${timings.total_ms} ms` },
    { label: 'Roundtrip', value: latency ? `${latency} ms` : 'n/a' },
  ]

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="rounded-2xl border border-slate-200 bg-[#f8fafc] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{item.label}</p>
          <p className="mt-2 text-lg font-semibold text-[#112231]">{item.value}</p>
        </div>
      ))}
    </div>
  )
}

function AnswerSummaryCard({ response }: { response: ChatQueryResponse }) {
  const summary = summarizeEvidence(response)

  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <SummaryCard
        title="Coverage window"
        value={summary.months.length > 0 ? summary.months.join(', ') : 'Nao identificado'}
      />
      <SummaryCard
        title="Evidence footprint"
        value={summary.chunkTypes.length > 0 ? summary.chunkTypes.slice(0, 2).join(' | ') : 'Nao identificado'}
      />
      <SummaryCard
        title="Spatial footprint"
        value={summary.lsoaCodes.length > 0 ? summary.lsoaCodes.slice(0, 3).join(', ') : 'Nao identificado'}
      />
    </div>
  )
}

function SummaryCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-[#f8fafc] px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{title}</p>
      <p className="mt-2 text-sm font-medium text-[#112231]">{value}</p>
    </div>
  )
}

function AnswerBody({ text }: { text: string }) {
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
      if (lastBlock?.type === 'list') lastBlock.items.push(content)
      else blocks.push({ type: 'list', items: [content] })
      continue
    }

    blocks.push({ type: 'paragraph', items: [content] })
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <SparklesIcon className="size-4 text-[#0e5973]" />
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Generated narrative</p>
      </div>
      <div className="space-y-3">
        {blocks.map((block, index) =>
          block.type === 'list' ? (
            <ul key={index} className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-slate-700">
              {block.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p key={index} className="text-sm leading-7 text-slate-700 whitespace-pre-wrap">
              {block.items[0]}
            </p>
          )
        )}
      </div>
    </div>
  )
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-xl border border-white/10 bg-white/6 px-3 py-2.5">
      <span className="text-xs uppercase tracking-[0.18em] text-slate-400">{label}</span>
      <span className="text-right text-sm font-medium text-white">{value}</span>
    </div>
  )
}

function TimingPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/15 px-3 py-2">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-400">{label}</p>
      <p className="mt-1 text-sm font-medium text-white">{value} ms</p>
    </div>
  )
}

function IdleState() {
  return (
    <div className="flex h-full flex-col items-center justify-center rounded-[32px] border border-dashed border-slate-300 bg-white/70 px-6 py-10 text-center">
      <div className="mb-5 rounded-full bg-[#dff7ff] p-4 text-[#0e5973]">
        <CircleDashedIcon className="size-8" />
      </div>
      <h3 className="text-2xl font-semibold tracking-tight text-[#112231]">Workspace pronto para analise</h3>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
        Use o prompt principal para investigar tendencias, pedir comparacoes ou interrogar o proprio stack sobre
        vetorizacao, MLflow e as camadas bronze, silver e gold.
      </p>
      <div className="mt-6 grid gap-3 text-left md:grid-cols-3">
        {[
          'Quais regioes tiveram aumento de burglary no periodo selecionado?',
          'Compare duas areas e cite as evidencias mais fortes.',
          'Explique como os documentos e runs do MLflow foram indexados.',
        ].map((example) => (
          <div key={example} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
            <div className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              <ArrowUpRightIcon className="size-3.5" />
              prompt
            </div>
            {example}
          </div>
        ))}
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex h-full flex-col items-center justify-center rounded-[32px] border border-slate-200 bg-white/80 text-center">
      <div className="mb-4 flex items-center gap-3 text-[#112231]">
        <Spinner className="size-5" />
        <span className="text-lg font-semibold">Executando pipeline de analise</span>
      </div>
      <p className="max-w-lg text-sm text-slate-600">
        Recuperando contexto no corpus vetorial, aplicando politicas de acesso e gerando a narrativa governada.
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
    <div className="flex h-full flex-col items-center justify-center rounded-[32px] border border-rose-200 bg-rose-50 px-6 text-center">
      <AlertTriangleIcon className="mb-4 size-10 text-rose-500" />
      <h3 className="text-xl font-semibold text-rose-950">Nao foi possivel concluir a analise</h3>
      <p className="mt-3 max-w-lg text-sm text-rose-900/80">{error?.message || 'Ocorreu um erro inesperado.'}</p>
      <Button variant="outline" onClick={onRetry} className="mt-5 gap-2">
        <RefreshCcwIcon className="size-4" />
        Tentar novamente
      </Button>
    </div>
  )
}

function EmptyState({ onReset }: { onReset: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center rounded-[32px] border border-slate-200 bg-white/80 px-6 text-center">
      <FileSearchIcon className="mb-4 size-10 text-slate-400" />
      <h3 className="text-xl font-semibold text-[#112231]">Nenhuma evidencia relevante encontrada</h3>
      <p className="mt-3 max-w-lg text-sm text-slate-600">
        Amplie o periodo, alivie os filtros ou reformule a pergunta para explorar outra janela de evidencia.
      </p>
      <Button variant="outline" onClick={onReset} className="mt-5">
        Nova pergunta
      </Button>
    </div>
  )
}
