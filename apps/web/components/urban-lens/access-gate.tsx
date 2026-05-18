'use client'

import type { ReactNode } from 'react'
import { KeyRoundIcon, LockKeyholeIcon, ShieldCheckIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ApiKeyModal } from './api-key-modal'

export function AccessGate() {
  return (
    <main className="mx-auto flex min-h-[calc(100vh-72px)] w-full max-w-6xl items-center px-4 py-10 lg:px-8">
      <div className="grid w-full gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-[28px] border border-white/8 bg-[#0f141b]/92 p-8 shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
          <div className="mb-5 flex flex-wrap items-center gap-2">
            <Badge className="border border-white/10 bg-white/6 text-slate-200 hover:bg-white/6">
              Urban Lens Analytics
            </Badge>
            <Badge className="bg-[#7dd3fc] text-[#08202b] hover:bg-[#7dd3fc]">Acesso governado</Badge>
          </div>

          <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-white">
            Workspace analitico protegido por credencial
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">
            O Urban Lens exige uma API key governada antes de liberar consultas, catalogo de modelos, historico e
            evidencias. Isso mantem rastreabilidade por usuario, auditoria por requisicao e aplicacao de limites por
            plano.
          </p>

          <div className="mt-8 grid gap-3 md:grid-cols-3">
            <FeatureCard
              icon={<LockKeyholeIcon className="size-4" />}
              title="Credencial obrigatoria"
              text="Nenhuma consulta e executada sem identidade governada."
            />
            <FeatureCard
              icon={<ShieldCheckIcon className="size-4" />}
              title="Auditoria ativa"
              text="Usuario, plano, modelo, filtros e tempos ficam associados a chamada."
            />
            <FeatureCard
              icon={<KeyRoundIcon className="size-4" />}
              title="Sessao temporaria"
              text="A chave fica apenas em cookie httpOnly durante esta sessao."
            />
          </div>
        </section>

        <section className="rounded-[28px] border border-white/8 bg-[#131922]/94 p-8 shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
          <h2 className="text-lg font-semibold text-white">Entrar no ambiente</h2>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            Use uma chave ja emitida ou registre uma solicitacao para analise. Chaves elevadas continuam sendo
            emitidas somente por administradores.
          </p>

          <div className="mt-6">
            <ApiKeyModal
              trigger={
                <Button className="h-11 w-full gap-2 rounded-full bg-[#7dd3fc] text-[#071b25] hover:bg-[#a5e2ff]">
                  <KeyRoundIcon className="size-4" />
                  Conectar credencial
                </Button>
              }
            />
          </div>

          <div className="mt-6 rounded-2xl border border-white/8 bg-black/20 p-4 text-sm text-slate-300">
            Melhor pratica aplicada:
            <div className="mt-2 space-y-2 text-slate-400">
              <p>1. Solicitacao publica registra interesse, mas nao emite chave automaticamente.</p>
              <p>2. Emissao e rotacao seguem fluxo administrativo autenticado.</p>
              <p>3. A chave nao e persistida em armazenamento acessivel ao JavaScript do navegador.</p>
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}

function FeatureCard({
  icon,
  title,
  text,
}: {
  icon: ReactNode
  title: string
  text: string
}) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
      <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/6 px-2.5 py-1 text-xs text-slate-200">
        {icon}
        {title}
      </div>
      <p className="text-sm leading-6 text-slate-400">{text}</p>
    </div>
  )
}
