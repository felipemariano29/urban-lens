'use client'

import { ActivityIcon, CpuIcon, GaugeIcon, HardDriveIcon, KeyRoundIcon, ShieldIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { useApiKey } from '@/contexts/api-key-context'
import { useAccessProfile, useHealthCheck, useUsageStats } from '@/hooks/use-urban-lens'
import type { HealthDependencies } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ApiKeyModal } from './api-key-modal'

function StatusDot({
  status,
}: {
  status: 'healthy' | 'degraded' | 'error' | 'unknown'
}) {
  return (
    <span
      className={cn(
        'inline-flex size-2.5 rounded-full',
        status === 'healthy' && 'bg-emerald-500',
        status === 'degraded' && 'bg-amber-500',
        (status === 'error' || status === 'unknown') && 'bg-rose-500'
      )}
    />
  )
}

function DependencyStrip({ dependencies }: { dependencies: HealthDependencies | null }) {
  if (!dependencies) {
    return null
  }

  const items = [
    { label: 'catalogo', value: dependencies.catalog, icon: GaugeIcon },
    { label: 'embedder', value: dependencies.rag_embedder, icon: CpuIcon },
    { label: 'vetor', value: dependencies.rag_vector_store, icon: HardDriveIcon },
  ]

  return (
    <div className="hidden xl:flex flex-wrap items-center gap-2 text-xs">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/6 px-2.5 py-1"
        >
          <item.icon className="size-3.5 text-slate-500" />
          <span className="text-slate-400">{item.label}</span>
          <span className={item.value === 'ok' ? 'text-emerald-400' : 'text-rose-400'}>{item.value}</span>
        </div>
      ))}
    </div>
  )
}

function roleLabel(role: string | undefined): string {
  switch (role) {
    case 'internal_service':
      return 'interno'
    case 'intel_user':
      return 'intel'
    default:
      return role || 'n/d'
  }
}

export function TopBar() {
  const { apiKey, isAuthenticated } = useApiKey()
  const { status, dependencies, isLoading } = useHealthCheck(apiKey)
  const { profile } = useAccessProfile(apiKey)
  const { usage } = useUsageStats(apiKey)

  const displayStatus =
    status === 'healthy' ? 'healthy' : status === 'degraded' ? 'degraded' : status || 'unknown'

  return (
    <header className="border-b border-white/8 bg-[#0a0f14]/94 text-white backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-3 lg:px-8">
        <div className="flex min-w-0 items-center gap-4">
          <div className="flex items-center gap-3">
            <ActivityIcon className="size-5 text-[#7dd3fc]" />
            <div className="min-w-0">
              <h1 className="truncate text-base font-semibold tracking-tight">Urban Lens Analytics</h1>
              <p className="text-xs text-slate-400">RAG governado para analise de seguranca urbana</p>
            </div>
          </div>

          <div className="hidden lg:flex flex-wrap items-center gap-2">
            <Badge className="border border-white/10 bg-white/6 text-slate-200 hover:bg-white/6">
              <StatusDot status={displayStatus as 'healthy' | 'degraded' | 'error' | 'unknown'} />
              <span className="ml-1">{isLoading ? 'verificando' : displayStatus}</span>
            </Badge>
            <Badge className="border border-white/10 bg-white/6 text-slate-200 hover:bg-white/6">
              <ShieldIcon className="mr-1 size-3.5 text-[#7dd3fc]" />
              {isAuthenticated ? `perfil ${roleLabel(profile?.role)}` : 'chave obrigatoria'}
            </Badge>
            {profile?.plan_code ? (
              <Badge className="border border-white/10 bg-white/6 text-slate-200 hover:bg-white/6">
                plano {profile.plan_code.toLowerCase()}
              </Badge>
            ) : null}
            {usage?.requests_per_day_limit ? (
              <Badge className="border border-white/10 bg-white/6 text-slate-200 hover:bg-white/6">
                hoje {usage.requests_last_day}/{usage.requests_per_day_limit}
              </Badge>
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <DependencyStrip dependencies={dependencies} />
          <ApiKeyModal
            trigger={
              <button className="inline-flex h-10 items-center gap-2 rounded-full border border-[#7dd3fc]/25 bg-[#7dd3fc]/10 px-4 text-sm font-medium text-[#d9f6ff] transition hover:bg-[#7dd3fc]/18">
                <KeyRoundIcon className="size-4" />
                {isAuthenticated ? 'Gerenciar chave' : 'Conectar chave'}
              </button>
            }
          />
        </div>
      </div>
    </header>
  )
}
