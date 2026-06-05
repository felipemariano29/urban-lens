'use client'

import { useState } from 'react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { EvidenceCitation } from '@/lib/types'
import { formatEvidenceTitle, summarizeMetadata } from '@/lib/presentation'
import { cn } from '@/lib/utils'
import { ChevronUpIcon, ChevronDownIcon, QuoteIcon } from 'lucide-react'

interface ResultCardProps {
  evidence: EvidenceCitation
  rank: number
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
  if (score >= 0.6) return 'bg-amber-500/10 text-amber-300 border-amber-500/20'
  return 'bg-rose-500/10 text-rose-300 border-rose-500/20'
}

function getScoreLabel(score: number): string {
  if (score >= 0.8) return 'Evidencia forte'
  if (score >= 0.6) return 'Evidencia moderada'
  return 'Evidencia fraca'
}

function formatTimestamp(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

const TRUNCATE_LENGTH = 300

export function ResultCard({ evidence, rank }: ResultCardProps) {
  const [expanded, setExpanded] = useState(false)
  const { score, excerpt, metadata } = evidence

  const title = formatEvidenceTitle(evidence, rank)
  const metadataSummary = summarizeMetadata(metadata)
  const needsTruncation = excerpt.length > TRUNCATE_LENGTH
  const displayContent =
    needsTruncation && !expanded
      ? `${excerpt.slice(0, TRUNCATE_LENGTH)}...`
      : excerpt

  return (
    <Card className="border-white/8 bg-black/18 py-4 text-white shadow-[0_10px_35px_rgba(0,0,0,0.18)]">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="font-mono text-xs">
                {evidence.id}
              </Badge>
              <CardTitle className="text-base font-semibold leading-tight">
                {title}
              </CardTitle>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge
                variant="outline"
                className={cn('shrink-0 font-mono text-xs', getScoreColor(score))}
                title={getScoreLabel(score)}
              >
                {score.toFixed(2)}
                {rank === 1 && score >= 0.8 && (
                  <ChevronUpIcon className="size-3 ml-0.5" />
                )}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {evidence.reference}
              </Badge>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground mt-2">
          <span>
            <span className="font-medium">Capturada em:</span>{' '}
            {formatTimestamp(evidence.timestamp)}
          </span>
        </div>

        {metadataSummary.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {metadataSummary.map((item) => (
              <Badge key={`${item.label}:${item.value}`} variant="outline" className="bg-muted/40">
                <span className="text-muted-foreground">{item.label}:</span> {item.value}
              </Badge>
            ))}
          </div>
        )}
      </CardHeader>

      <CardContent className="pt-0">
          <div className="border-t border-white/8 pt-3">
          <div className="flex gap-3">
            <QuoteIcon className="size-4 shrink-0 text-muted-foreground mt-0.5" />
            <p className="text-sm leading-relaxed text-slate-200">
              {displayContent}
            </p>
          </div>

          {needsTruncation && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              className="mt-2 h-7 text-xs"
            >
              {expanded ? (
                <>
                  <ChevronUpIcon className="size-3" />
                  Ver menos
                </>
              ) : (
                <>
                  <ChevronDownIcon className="size-3" />
                  Ver mais
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
