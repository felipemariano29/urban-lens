'use client'

import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { EvidenceCitation } from '@/lib/types'
import { cn } from '@/lib/utils'

interface EvidenceCardProps {
  evidence: EvidenceCitation
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return 'bg-emerald-100 text-emerald-800 border-emerald-200'
  if (score >= 0.6) return 'bg-amber-100 text-amber-800 border-amber-200'
  return 'bg-slate-100 text-slate-700 border-slate-200'
}

export function EvidenceCard({ evidence }: EvidenceCardProps) {
  return (
    <Card className="py-3 border-l-4 border-l-primary/40">
      <CardHeader className="pb-2 pt-0 px-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <Badge variant="outline" className="font-mono text-xs shrink-0">
              {evidence.id}
            </Badge>
            <span className="text-sm font-medium truncate">{evidence.source}</span>
          </div>
          <Badge
            variant="outline"
            className={cn('font-mono text-xs shrink-0', getScoreColor(evidence.score))}
            title={`Similaridade: ${(evidence.score * 100).toFixed(1)}%`}
          >
            {(evidence.score * 100).toFixed(0)}%
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 font-mono">{evidence.reference}</p>
      </CardHeader>
      <CardContent className="px-4 pt-0">
        <p className="text-sm text-foreground/80 leading-relaxed italic">
          &ldquo;{evidence.excerpt}&rdquo;
        </p>
      </CardContent>
    </Card>
  )
}
