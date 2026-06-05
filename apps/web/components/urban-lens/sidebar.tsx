'use client'

import {
  BotIcon,
  Clock3Icon,
  HistoryIcon,
  ShieldCheckIcon,
  SlidersHorizontalIcon,
  TrashIcon,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { validateLsoaCode, validateReferenceMonth } from '@/hooks/use-urban-lens'
import { CRIME_TYPE_OPTIONS } from '@/lib/types'
import type {
  CurrentUserResponse,
  HistoryItem,
  OllamaModelInfo,
  QueryFilters,
  UsageStatsResponse,
} from '@/lib/types'
import { cn } from '@/lib/utils'

interface SidebarProps {
  filters: QueryFilters
  onFiltersChange: (filters: QueryFilters) => void
  topK: number
  onTopKChange: (value: number) => void
  availableModels: OllamaModelInfo[]
  selectedModel: string
  onSelectedModelChange: (value: string) => void
  isLoadingModels?: boolean
  needsApiKey?: boolean
  profile: CurrentUserResponse | null
  usage: UsageStatsResponse | null
  history: HistoryItem[]
  onHistorySelect: (item: HistoryItem) => void
  onClearHistory: () => void
  disabled?: boolean
}

export function Sidebar({
  filters,
  onFiltersChange,
  topK,
  onTopKChange,
  availableModels,
  selectedModel,
  onSelectedModelChange,
  isLoadingModels = false,
  needsApiKey = false,
  profile,
  usage,
  history,
  onHistorySelect,
  onClearHistory,
  disabled = false,
}: SidebarProps) {
  const planMaxTopK = profile?.plan_max_top_k ?? 20
  const lsoaError = filters.lsoa_code && !validateLsoaCode(filters.lsoa_code) ? 'Formato esperado: E01001234' : null
  const monthError =
    filters.reference_month && !validateReferenceMonth(filters.reference_month) ? 'Formato esperado: YYYY-MM' : null

  return (
    <aside className="min-h-0 border-r border-white/8 bg-[#0f141b] text-white lg:w-[340px] lg:min-w-[340px]">
      <div className="flex h-full min-h-0 flex-col">
        <div className="space-y-5 overflow-y-auto px-4 py-4">
          <section className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="mb-3 flex items-center gap-2">
              <ShieldCheckIcon className="size-4 text-[#64d3ff]" />
              <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-200">Credencial</h2>
            </div>
            <div className="grid gap-3 text-sm">
              <Metric label="Tipo" value={profile ? profile.auth_type.replaceAll('_', ' ') : 'sessao obrigatoria'} />
              <Metric label="Perfil" value={profile?.role || 'n/d'} />
              <Metric label="Plano" value={profile?.plan_code || 'n/a'} />
              <Metric
                label="Hoje"
                value={
                  usage?.requests_per_day_limit
                    ? `${usage.requests_last_day}/${usage.requests_per_day_limit}`
                    : 'indisponivel'
                }
              />
              <Metric
                label="Tokens/dia"
                value={usage ? `${usage.tokens_last_day.toLocaleString('pt-BR')} usados` : '0'}
              />
            </div>
          </section>

          <section className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="mb-4 flex items-center gap-2">
              <BotIcon className="size-4 text-[#f59e0b]" />
              <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-200">Modelo de resposta</h2>
            </div>
            <div className="space-y-2">
              <Label htmlFor="chat-model" className="text-xs text-slate-300">
                Modelo Ollama
              </Label>
              <Select
                value={selectedModel}
                onValueChange={onSelectedModelChange}
                disabled={disabled || isLoadingModels || availableModels.length === 0 || needsApiKey}
              >
                <SelectTrigger id="chat-model" className="border-white/10 bg-[#0f171f] text-white">
                  <SelectValue placeholder="Selecione um modelo" />
                </SelectTrigger>
                <SelectContent>
                  {availableModels.map((model) => (
                    <SelectItem key={model.name} value={model.name}>
                      {model.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-slate-400">
                {needsApiKey
                  ? 'Conecte uma chave para carregar os modelos.'
                  : isLoadingModels
                    ? 'Sincronizando catalogo local.'
                    : availableModels.length > 0
                      ? 'Selecione o modelo usado na geracao da resposta.'
                      : 'Nenhum modelo disponivel foi retornado pelo backend.'}
              </p>
            </div>
          </section>

          <section className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="mb-4 flex items-center gap-2">
              <SlidersHorizontalIcon className="size-4 text-[#64d3ff]" />
              <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-200">Filtros de busca</h2>
            </div>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="crime-type" className="text-xs text-slate-300">
                  Categoria
                </Label>
                <Select
                  value={filters.crime_type || '__all__'}
                  onValueChange={(value) =>
                    onFiltersChange({
                      ...filters,
                      crime_type: value === '__all__' ? null : value,
                    })
                  }
                  disabled={disabled}
                >
                  <SelectTrigger id="crime-type" className="border-white/10 bg-[#0f171f] text-white">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent>
                    {CRIME_TYPE_OPTIONS.map((option) => (
                      <SelectItem key={option.value || '__all__'} value={option.value || '__all__'}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="lsoa-code" className="text-xs text-slate-300">
                  Codigo LSOA
                </Label>
                <Input
                  id="lsoa-code"
                  placeholder="E01001234"
                  value={filters.lsoa_code || ''}
                  onChange={(event) =>
                    onFiltersChange({
                      ...filters,
                      lsoa_code: event.target.value || null,
                    })
                  }
                  disabled={disabled}
                  aria-invalid={!!lsoaError}
                  className={cn(
                    'border-white/10 bg-[#0f171f] text-white placeholder:text-slate-500',
                    lsoaError && 'border-rose-500'
                  )}
                />
                {lsoaError ? <p className="text-xs text-rose-300">{lsoaError}</p> : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="reference-month" className="text-xs text-slate-300">
                  Mes de referencia
                </Label>
                <Input
                  id="reference-month"
                  placeholder="2024-01"
                  value={filters.reference_month || ''}
                  onChange={(event) =>
                    onFiltersChange({
                      ...filters,
                      reference_month: event.target.value || null,
                    })
                  }
                  disabled={disabled}
                  aria-invalid={!!monthError}
                  className={cn(
                    'border-white/10 bg-[#0f171f] text-white placeholder:text-slate-500',
                    monthError && 'border-rose-500'
                  )}
                />
                {monthError ? <p className="text-xs text-rose-300">{monthError}</p> : null}
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-xs text-slate-300">Top-k</Label>
                  <span className="rounded-full border border-white/10 bg-black/20 px-2 py-0.5 font-mono text-xs text-slate-200">
                    {topK}
                  </span>
                </div>
                <Slider
                  value={[topK]}
                  onValueChange={(values) => onTopKChange(values[0])}
                  min={1}
                  max={planMaxTopK}
                  step={1}
                  disabled={disabled}
                  className="px-1"
                />
                <div className="flex justify-between text-xs text-slate-400">
                  <span>precisao</span>
                  <span>limite {planMaxTopK}</span>
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HistoryIcon className="size-4 text-[#f59e0b]" />
                <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-200">Historico recente</h2>
              </div>
              {history.length > 0 ? (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={onClearHistory}
                  className="size-7 text-slate-300 hover:bg-white/8 hover:text-white"
                  title="Limpar historico"
                >
                  <TrashIcon className="size-3.5" />
                </Button>
              ) : null}
            </div>

            {history.length === 0 ? (
              <p className="text-sm text-slate-400">As consultas recentes aparecerao aqui.</p>
            ) : (
              <div className="space-y-2">
                {history.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onHistorySelect(item)}
                    disabled={disabled}
                    className="group flex w-full flex-col rounded-xl border border-white/8 bg-black/15 p-3 text-left transition hover:border-[#64d3ff]/40 hover:bg-white/8 disabled:opacity-50"
                  >
                    <p className="truncate text-sm font-medium text-slate-100 group-hover:text-white">{item.query}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span className="inline-flex items-center gap-1">
                        <Clock3Icon className="size-3" />
                        {formatTime(item.timestamp)}
                      </span>
                      <span>{item.model}</span>
                      <span>top-k {item.topK}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </aside>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-white/6 bg-black/15 px-3 py-2.5">
      <span className="text-xs uppercase tracking-[0.18em] text-slate-400">{label}</span>
      <span className="text-sm font-medium text-slate-100">{value}</span>
    </div>
  )
}

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
