'use client'

import { ActivityIcon, CpuIcon, GaugeIcon, HardDriveIcon, KeyRoundIcon, ShieldIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { useAccessProfile, useHealthCheck, useUsageStats } from '@/hooks/use-urban-lens'
import { useApiKey } from '@/contexts/api-key-context'
import { ApiKeyModal } from './api-key-modal'
import type { HealthDependencies } from '@/lib/types'
import { cn } from '@/lib/utils'

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
    return <span className="text-sm text-muted-foreground">telemetria operacional indisponivel</span>
  }

  const items = [
    { label: 'catalog', value: dependencies.catalog, icon: GaugeIcon },
    { label: 'embedder', value: dependencies.rag_embedder, icon: CpuIcon },
    { label: 'vector', value: dependencies.rag_vector_store, icon: HardDriveIcon },
  ]

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5 rounded-full border border-border/60 bg-background/70 px-2.5 py-1">
          <item.icon className="size-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">{item.label}</span>
          <span className={item.value === 'ok' ? 'text-emerald-600' : 'text-rose-600'}>{item.value}</span>
        </div>
      ))}
    </div>
  )
}

function roleLabel(role: string | undefined): string {
  switch (role) {
    case 'internal_service':
      return 'internal'
    case 'intel_user':
      return 'intel'
    default:
      return role || 'anon'
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
    <header className="border-b border-white/10 bg-[#0f1a24]/90 text-white backdrop-blur">
      <div className="flex flex-col gap-4 px-5 py-4 lg:px-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="border border-white/10 bg-white/8 text-white hover:bg-white/8">Urban Intelligence</Badge>
              <Badge className="bg-[#f59e0b] text-[#201203] hover:bg-[#f59e0b]">Analytics Workspace</Badge>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <ActivityIcon className="size-5 text-[#64d3ff]" />
                <h1 className="text-2xl font-semibold tracking-tight">Urban Lens Analytics</h1>
              </div>
              <p className="max-w-3xl text-sm text-slate-300">
                Painel governado para exploracao de evidencias, consulta RAG e operacao local sobre dados de seguranca
                urbana.
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-3 lg:items-end">
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-sm">
                <StatusDot status={displayStatus as 'healthy' | 'degraded' | 'error' | 'unknown'} />
                <span className="text-slate-200">{isLoading ? 'verificando stack' : displayStatus}</span>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-sm">
                <ShieldIcon className="size-4 text-[#64d3ff]" />
                <span className="text-slate-200">
                  {isAuthenticated ? `sessao ${roleLabel(profile?.role)}` : 'sem credencial ativa'}
                </span>
              </div>
              <ApiKeyModal
                trigger={
                  <button className="inline-flex items-center gap-2 rounded-full border border-[#64d3ff]/30 bg-[#64d3ff]/10 px-3 py-1.5 text-sm font-medium text-[#dff7ff] transition hover:bg-[#64d3ff]/18">
                    <KeyRoundIcon className="size-4" />
                    {isAuthenticated ? 'Gerenciar sessao' : 'Entrar com chave'}
                  </button>
                }
              />
            </div>
            <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
              {profile?.plan_code && (
                <span className="rounded-full border border-white/10 bg-white/6 px-3 py-1">
                  plano {profile.plan_code.toLowerCase()}
                </span>
              )}
              {usage?.remaining_day !== undefined && usage?.remaining_day !== null && (
                <span className="rounded-full border border-white/10 bg-white/6 px-3 py-1">
                  {usage.remaining_day} consultas restantes hoje
                </span>
              )}
              {profile?.plan_max_top_k && (
                <span className="rounded-full border border-white/10 bg-white/6 px-3 py-1">
                  top-k max {profile.plan_max_top_k}
                </span>
              )}
            </div>
          </div>
        </div>

        <DependencyStrip dependencies={dependencies} />
      </div>
    </header>
  )
}
