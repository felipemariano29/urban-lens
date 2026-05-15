'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EvidenceCard } from './evidence-card'
import type { ChatQueryResponse } from '@/lib/types'
import {
  PlusCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CheckCircleIcon,
  AlertCircleIcon,
} from 'lucide-react'

interface ChatAreaProps {
  response: ChatQueryResponse
  latency: number | null
  onReset: () => void
}

export function ChatArea({ response, latency, onReset }: ChatAreaProps) {
  const [showContext, setShowContext] = useState(false)
  const { answer, evidences, context, fallback_reason } = response
  const isAnswered = answer.status === 'answered'

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          <h2 className="font-semibold text-lg">Resposta</h2>
          <Badge
            variant={isAnswered ? 'default' : 'secondary'}
            className="text-xs gap-1"
          >
            {isAnswered ? (
              <CheckCircleIcon className="size-3" />
            ) : (
              <AlertCircleIcon className="size-3" />
            )}
            {isAnswered ? 'respondido' : 'evidência insuficiente'}
          </Badge>
          {latency !== null && (
            <span className="text-sm text-muted-foreground">
              {latency}ms &middot; {answer.model}
            </span>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={onReset}>
          <PlusCircleIcon className="size-4" />
          Nova pergunta
        </Button>
      </div>

      <ScrollArea className="flex-1 -mx-2 px-2">
        <div className="space-y-6 pb-4">
          {/* Resposta gerada */}
          <div className="rounded-lg border bg-muted/30 p-4">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{answer.text}</p>
            {fallback_reason && (
              <p className="text-xs text-muted-foreground mt-3 border-t pt-3">
                <span className="font-medium">Motivo:</span> {fallback_reason}
              </p>
            )}
          </div>

          {/* Evidências */}
          {evidences.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <h3 className="text-sm font-semibold">Evidências</h3>
                <Badge variant="outline" className="text-xs font-mono">
                  {evidences.length}
                </Badge>
              </div>
              <div className="space-y-3">
                {evidences.map((ev) => (
                  <EvidenceCard key={ev.id} evidence={ev} />
                ))}
              </div>
            </section>
          )}

          {/* Contexto raw — colapsável */}
          {context.length > 0 && (
            <section>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowContext(!showContext)}
                className="text-xs text-muted-foreground h-7 px-2"
              >
                {showContext ? (
                  <ChevronUpIcon className="size-3 mr-1" />
                ) : (
                  <ChevronDownIcon className="size-3 mr-1" />
                )}
                {showContext ? 'Ocultar' : 'Ver'} chunks de contexto ({context.length})
              </Button>
              {showContext && (
                <div className="mt-2 space-y-2">
                  {context.map((chunk) => (
                    <div
                      key={chunk.id}
                      className="rounded border bg-muted/20 p-3 text-xs"
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-mono text-muted-foreground truncate mr-2">
                          {chunk.source || chunk.id}
                        </span>
                        <span className="font-mono shrink-0">
                          {chunk.score.toFixed(3)}
                        </span>
                      </div>
                      <p className="text-foreground/70 line-clamp-3 leading-relaxed">
                        {chunk.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
