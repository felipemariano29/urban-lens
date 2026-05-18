'use client'

import { useEffect, useRef } from 'react'
import { ArrowRightIcon, RadarIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

interface QueryInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  disabled?: boolean
  autoFocus?: boolean
}

const SUGGESTIONS = [
  'Quais evidencias sustentam aumento de burglary em Westminster em 2024-01?',
  'Compare os registros de violencia entre duas areas no mesmo periodo.',
  'Explique a forma de vetorizacao e o papel das camadas bronze, silver e gold.',
]

export function QueryInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  autoFocus = false,
}: QueryInputProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus()
    }
  }, [autoFocus])

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && value.trim()) {
      event.preventDefault()
      onSubmit()
    }
  }

  const canSubmit = value.trim().length > 0 && !disabled

  return (
    <section className="rounded-[24px] border border-white/8 bg-[#121821]/92 p-5 shadow-[0_18px_80px_rgba(0,0,0,0.32)] backdrop-blur md:p-6">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
            <RadarIcon className="size-3.5" />
            Nova consulta
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-white">Consulta analitica</h2>
          <p className="max-w-3xl text-sm text-slate-400">
            Envie uma pergunta em linguagem natural. O pipeline recupera contexto, aplica a politica de acesso e
            retorna resposta com evidencias.
          </p>
        </div>
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <Kbd>Ctrl</Kbd>
          <span>+</span>
          <Kbd>Enter</Kbd>
          <span>para executar</span>
        </div>
      </div>

      <div className="grid gap-4">
        <Textarea
          ref={inputRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={5}
          placeholder="Exemplo: compare burglary e vehicle crime em Westminster em 2024-01 e cite as evidencias mais relevantes."
          className={cn(
            'min-h-[136px] resize-none rounded-2xl border-white/10 bg-[#0b1016] px-4 py-3 text-base leading-7 text-white placeholder:text-slate-500',
            disabled && 'opacity-60'
          )}
        />

        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Sugestoes</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => onChange(suggestion)}
                  className="rounded-full border border-white/10 bg-white/4 px-3 py-1.5 text-sm text-slate-300 transition hover:border-[#64d3ff]/40 hover:text-white"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          <Button onClick={onSubmit} disabled={!canSubmit} className="h-11 gap-2 rounded-full px-6">
            Consultar
            <ArrowRightIcon className="size-4" />
          </Button>
        </div>
      </div>
    </section>
  )
}
