'use client'

import { Badge } from '@/components/ui/badge'
import { useHealthCheck } from '@/hooks/use-urban-lens'
import type { HealthDependencies } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ActivityIcon, CircleIcon, DatabaseIcon, CpuIcon, HardDriveIcon } from 'lucide-react'

function StatusIndicator({
  status,
}: {
  status: 'healthy' | 'degraded' | 'error' | 'unknown'
}) {
  return (
    <CircleIcon
      className={cn(
        'size-3 fill-current',
        status === 'healthy' && 'text-emerald-500',
        status === 'degraded' && 'text-amber-500',
        (status === 'error' || status === 'unknown') && 'text-red-500'
      )}
    />
  )
}

function DependencyStatus({
  dependencies,
}: {
  dependencies: HealthDependencies | null
}) {
  if (!dependencies) {
    return (
      <span className="text-muted-foreground text-sm">
        Verificando serviços...
      </span>
    )
  }

  return (
    <div className="flex items-center gap-4 text-sm">
      <div className="flex items-center gap-1.5">
        <DatabaseIcon className="size-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">catalog:</span>
        <span
          className={cn(
            dependencies.catalog === 'ok'
              ? 'text-emerald-600'
              : 'text-red-500'
          )}
        >
          {dependencies.catalog}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <CpuIcon className="size-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">embedder:</span>
        <span
          className={cn(
            dependencies.rag_embedder === 'ok'
              ? 'text-emerald-600'
              : 'text-red-500'
          )}
        >
          {dependencies.rag_embedder}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <HardDriveIcon className="size-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">vector store:</span>
        <span
          className={cn(
            dependencies.rag_vector_store === 'ok'
              ? 'text-emerald-600'
              : 'text-red-500'
          )}
        >
          {dependencies.rag_vector_store}
        </span>
      </div>
    </div>
  )
}

export function TopBar() {
  const { status, dependencies, isLoading } = useHealthCheck()

  const displayStatus =
    status === 'healthy'
      ? 'healthy'
      : status === 'degraded'
        ? 'degraded'
        : 'error'

  return (
    <header className="border-b bg-card">
      <div className="flex h-14 items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <ActivityIcon className="size-5 text-primary" />
            <span className="font-semibold text-lg tracking-tight">
              urban-lens
            </span>
          </div>
          <Badge variant="secondary" className="text-xs font-mono">
            RAG
          </Badge>
          <div className="flex items-center gap-1.5">
            <StatusIndicator status={displayStatus} />
            <span
              className={cn(
                'text-sm font-medium',
                displayStatus === 'healthy' && 'text-emerald-600',
                displayStatus === 'degraded' && 'text-amber-600',
                displayStatus === 'error' && 'text-red-600'
              )}
            >
              {isLoading ? 'verificando...' : displayStatus}
            </span>
          </div>
        </div>

        <DependencyStatus dependencies={dependencies} />
      </div>
    </header>
  )
}
