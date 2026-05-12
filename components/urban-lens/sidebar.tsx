'use client'

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { CRIME_TYPES, type QueryFilters, type HistoryItem } from '@/lib/types'
import { validateLsoaCode, validateReferenceMonth } from '@/hooks/use-urban-lens'
import { FilterIcon, HistoryIcon, ClockIcon, TrashIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SidebarProps {
  filters: QueryFilters
  onFiltersChange: (filters: QueryFilters) => void
  topK: number
  onTopKChange: (value: number) => void
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
  history,
  onHistorySelect,
  onClearHistory,
  disabled = false,
}: SidebarProps) {
  const lsoaError =
    filters.lsoa_code && !validateLsoaCode(filters.lsoa_code)
      ? 'Formato: E01001234'
      : null

  const monthError =
    filters.reference_month && !validateReferenceMonth(filters.reference_month)
      ? 'Formato: YYYY-MM'
      : null

  return (
    <aside className="w-72 border-r bg-sidebar flex flex-col h-full">
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Filtros */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <FilterIcon className="size-4 text-muted-foreground" />
              <h2 className="font-semibold text-sm">Filtros</h2>
            </div>

            <div className="space-y-4">
              {/* Tipo de crime */}
              <div className="space-y-2">
                <Label htmlFor="crime-type" className="text-xs">
                  Tipo de crime
                </Label>
                <Select
                  value={filters.crime_type || 'Todos'}
                  onValueChange={(value) =>
                    onFiltersChange({
                      ...filters,
                      crime_type: value === 'Todos' ? null : value,
                    })
                  }
                  disabled={disabled}
                >
                  <SelectTrigger id="crime-type" className="w-full">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent>
                    {CRIME_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Código LSOA */}
              <div className="space-y-2">
                <Label htmlFor="lsoa-code" className="text-xs">
                  Código LSOA
                </Label>
                <Input
                  id="lsoa-code"
                  placeholder="Ex: E01001234"
                  value={filters.lsoa_code || ''}
                  onChange={(e) =>
                    onFiltersChange({
                      ...filters,
                      lsoa_code: e.target.value || null,
                    })
                  }
                  disabled={disabled}
                  aria-invalid={!!lsoaError}
                  className={cn(lsoaError && 'border-destructive')}
                />
                {lsoaError && (
                  <p className="text-xs text-destructive">{lsoaError}</p>
                )}
              </div>

              {/* Mês de referência */}
              <div className="space-y-2">
                <Label htmlFor="reference-month" className="text-xs">
                  Mês de referência
                </Label>
                <Input
                  id="reference-month"
                  placeholder="Ex: 2024-01"
                  value={filters.reference_month || ''}
                  onChange={(e) =>
                    onFiltersChange({
                      ...filters,
                      reference_month: e.target.value || null,
                    })
                  }
                  disabled={disabled}
                  aria-invalid={!!monthError}
                  className={cn(monthError && 'border-destructive')}
                />
                {monthError && (
                  <p className="text-xs text-destructive">{monthError}</p>
                )}
              </div>

              {/* Top-K */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Top-k resultados</Label>
                  <span className="text-xs font-mono text-muted-foreground">
                    {topK}
                  </span>
                </div>
                <Slider
                  value={[topK]}
                  onValueChange={(values) => onTopKChange(values[0])}
                  min={1}
                  max={20}
                  step={1}
                  disabled={disabled}
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>1</span>
                  <span>20</span>
                </div>
              </div>
            </div>
          </section>

          {/* Histórico */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <HistoryIcon className="size-4 text-muted-foreground" />
                <h2 className="font-semibold text-sm">Histórico</h2>
              </div>
              {history.length > 0 && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={onClearHistory}
                  className="size-6"
                  title="Limpar histórico"
                >
                  <TrashIcon className="size-3" />
                </Button>
              )}
            </div>

            {history.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">
                Nenhuma consulta recente
              </p>
            ) : (
              <div className="space-y-1">
                {history.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onHistorySelect(item)}
                    disabled={disabled}
                    className="w-full text-left p-2 rounded-md hover:bg-sidebar-accent transition-colors group disabled:opacity-50"
                  >
                    <p className="text-sm truncate group-hover:text-sidebar-accent-foreground">
                      {item.query}
                    </p>
                    <div className="flex items-center gap-1 mt-1">
                      <ClockIcon className="size-3 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">
                        {formatTime(item.timestamp)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>
      </ScrollArea>
    </aside>
  )
}

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
