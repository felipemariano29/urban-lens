'use client'

import { useState } from 'react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { EvidenceCitation } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ChevronUpIcon, ChevronDownIcon, QuoteIcon } from 'lucide-react'

interface ResultCardProps {
  evidence: EvidenceCitation
  rank: number
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return 'bg-emerald-100 text-emerald-800 border-emerald-200'
  if (score >= 0.6) return 'bg-amber-100 text-amber-800 border-amber-200'
  return 'bg-red-100 text-red-800 border-red-200'
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

  const title = evidence.source || metadata.title || `Evidencia ${rank}`
  const needsTruncation = excerpt.length > TRUNCATE_LENGTH
  const displayContent =
    needsTruncation && !expanded
      ? `${excerpt.slice(0, TRUNCATE_LENGTH)}...`
      : excerpt

  return (
    <Card className="py-4">
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
          {metadata.crime_type && (
            <span>
              <span className="font-medium">Tipo:</span> {String(metadata.crime_type)}
            </span>
          )}
          {metadata.lsoa_code && (
            <span>
              <span className="font-medium">LSOA:</span> {String(metadata.lsoa_code)}
            </span>
          )}
          {metadata.reference_month && (
            <span>
              <span className="font-medium">Ref.:</span>{' '}
              {String(metadata.reference_month)}
            </span>
          )}
          {metadata.dataset_version_id && (
            <span>
              <span className="font-medium">Dataset:</span>{' '}
              {String(metadata.dataset_version_id)}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="border-t pt-3">
          <div className="flex gap-3">
            <QuoteIcon className="size-4 shrink-0 text-muted-foreground mt-0.5" />
            <p className="text-sm leading-relaxed text-foreground/90">
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
