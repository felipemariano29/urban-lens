'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { QueryResult } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ChevronUpIcon, ChevronDownIcon } from 'lucide-react'

interface ResultCardProps {
  result: QueryResult
  rank: number
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return 'bg-emerald-100 text-emerald-800 border-emerald-200'
  if (score >= 0.6) return 'bg-amber-100 text-amber-800 border-amber-200'
  return 'bg-red-100 text-red-800 border-red-200'
}

function getScoreLabel(score: number): string {
  if (score >= 0.8) return 'Alta similaridade'
  if (score >= 0.6) return 'Similaridade média'
  return 'Baixa similaridade'
}

const TRUNCATE_LENGTH = 300

export function ResultCard({ result, rank }: ResultCardProps) {
  const [expanded, setExpanded] = useState(false)
  const { score, content, metadata } = result

  const title =
    metadata.title || result.id || `Resultado ${rank}`
  const needsTruncation = content.length > TRUNCATE_LENGTH
  const displayContent =
    needsTruncation && !expanded
      ? content.slice(0, TRUNCATE_LENGTH) + '...'
      : content

  return (
    <Card className="py-4">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <CardTitle className="text-base font-semibold leading-tight">
            {title}
          </CardTitle>
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
        </div>

        {/* Metadados */}
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground mt-2">
          {metadata.crime_type && (
            <span>
              <span className="font-medium">Tipo:</span> {metadata.crime_type}
            </span>
          )}
          {metadata.lsoa_code && (
            <span>
              <span className="font-medium">LSOA:</span> {metadata.lsoa_code}
            </span>
          )}
          {metadata.reference_month && (
            <span>
              <span className="font-medium">Ref.:</span>{' '}
              {metadata.reference_month}
            </span>
          )}
          {metadata.dataset_version_id && (
            <span>
              <span className="font-medium">Dataset:</span>{' '}
              {metadata.dataset_version_id}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="border-t pt-3">
          <p className="text-sm leading-relaxed text-foreground/90">
            {`"${displayContent}"`}
          </p>

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
