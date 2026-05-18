'use client'

import { useRef, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { ArrowRightIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface QueryInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  disabled?: boolean
  autoFocus?: boolean
}

export function QueryInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  autoFocus = false,
}: QueryInputProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus()
    }
  }, [autoFocus])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && e.ctrlKey && value.trim()) {
      e.preventDefault()
      onSubmit()
    }
  }

  const canSubmit = value.trim().length > 0 && !disabled

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Input
            ref={inputRef}
            type="text"
            placeholder="Faça uma pergunta sobre os dados de segurança urbana..."
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className={cn(
              'pr-4 h-11 text-base',
              disabled && 'opacity-60'
            )}
          />
        </div>
        <Button
          onClick={onSubmit}
          disabled={!canSubmit}
          className="h-11 px-6"
        >
          Buscar
          <ArrowRightIcon className="size-4" />
        </Button>
      </div>
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <Kbd>Ctrl</Kbd>
        <span>+</span>
        <Kbd>Enter</Kbd>
        <span>para buscar</span>
      </div>
    </div>
  )
}
