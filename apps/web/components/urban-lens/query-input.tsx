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
    <section className="rounded-[28px] border border-black/5 bg-white/90 p-5 shadow-[0_18px_80px_rgba(12,26,41,0.08)] backdrop-blur md:p-6">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 rounded-full bg-[#dff7ff] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[#0e5973]">
            <RadarIcon className="size-3.5" />
            Investigative prompt
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-[#122333]">Construa uma consulta analitica</h2>
          <p className="max-w-3xl text-sm text-slate-600">
            Envie uma pergunta investigativa em linguagem natural. O motor vai recuperar contexto, citar evidencias e
            responder dentro da politica de acesso ativa.
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
            'min-h-[148px] resize-none rounded-2xl border-slate-200 bg-[#f7fafb] px-4 py-3 text-base leading-7 text-slate-900 placeholder:text-slate-500',
            disabled && 'opacity-60'
          )}
        />

        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Prompts sugeridos</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => onChange(suggestion)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 transition hover:border-[#64d3ff] hover:text-[#0e5973]"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          <Button onClick={onSubmit} disabled={!canSubmit} className="h-11 gap-2 rounded-full px-6">
            Executar analise
            <ArrowRightIcon className="size-4" />
          </Button>
        </div>
      </div>
    </section>
  )
}
