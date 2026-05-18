'use client'

import { useCallback, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  CheckCircle2Icon,
  KeyRoundIcon,
  Loader2Icon,
  LockKeyholeIcon,
  MailPlusIcon,
  ShieldCheckIcon,
  Trash2Icon,
} from 'lucide-react'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { useApiKey } from '@/contexts/api-key-context'
import { submitAccessRequest } from '@/hooks/use-urban-lens'

interface ApiKeyModalProps {
  trigger?: ReactNode
}

function maskApiKey(value: string | null): string {
  if (!value) return ''
  if (value.length <= 12) return '********'
  return `${value.slice(0, 7)}******${value.slice(-6)}`
}

export function ApiKeyModal({ trigger }: ApiKeyModalProps) {
  const { apiKey, setApiKey, clearApiKey, isAuthenticated } = useApiKey()
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState<string>(isAuthenticated ? 'session' : 'existing')

  const [inputKey, setInputKey] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [organization, setOrganization] = useState('')
  const [useCase, setUseCase] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [requestError, setRequestError] = useState<string | null>(null)
  const [requestResult, setRequestResult] = useState<{ requestId: string; message: string } | null>(null)

  const maskedApiKey = useMemo(() => maskApiKey(apiKey), [apiKey])

  const resetRequestState = useCallback(() => {
    setName('')
    setEmail('')
    setOrganization('')
    setUseCase('')
    setRequestError(null)
    setRequestResult(null)
    setIsSubmitting(false)
  }, [])

  const handleClose = useCallback(() => {
    setOpen(false)
    setInputKey('')
    resetRequestState()
    setTab(isAuthenticated ? 'session' : 'existing')
  }, [isAuthenticated, resetRequestState])

  const handleSaveExistingKey = useCallback(() => {
    if (!inputKey.trim()) return
    setApiKey(inputKey.trim())
    setInputKey('')
    setTab('session')
  }, [inputKey, setApiKey])

  const handleAccessRequest = useCallback(async () => {
    if (!name.trim() || !email.trim() || !useCase.trim()) {
      setRequestError('Preencha nome, email e objetivo de uso.')
      return
    }

    setIsSubmitting(true)
    setRequestError(null)

    try {
      const result = await submitAccessRequest({
        full_name: name.trim(),
        email: email.trim(),
        organization: organization.trim() || null,
        use_case: useCase.trim(),
      })

      setRequestResult({
        requestId: result.request_id,
        message: result.message,
      })
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : 'Nao foi possivel registrar a solicitacao.')
    } finally {
      setIsSubmitting(false)
    }
  }, [email, name, organization, useCase])

  const handleClearSession = useCallback(() => {
    clearApiKey()
    setTab('existing')
  }, [clearApiKey])

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          handleClose()
          return
        }
        setOpen(true)
      }}
    >
      <DialogTrigger asChild>
        {trigger || (
          <Button variant={isAuthenticated ? 'outline' : 'default'} className="gap-2">
            <KeyRoundIcon className="size-4" />
            {isAuthenticated ? 'Credencial ativa' : 'Acessar ambiente'}
          </Button>
        )}
      </DialogTrigger>

      <DialogContent className="max-w-2xl border-border/70 bg-card/95 p-0 backdrop-blur">
        <div className="border-b border-border/70 bg-gradient-to-r from-[#10212f] via-[#163246] to-[#1b4e63] p-6 text-white">
          <DialogHeader>
            <div className="mb-3 flex items-center gap-2">
              <Badge className="bg-white/12 text-white hover:bg-white/12">Governed Access</Badge>
              <Badge className="bg-[#f59e0b] text-[#1b1303] hover:bg-[#f59e0b]">Urban Lens Analytics</Badge>
            </div>
            <DialogTitle className="text-2xl font-semibold tracking-tight">
              Controle de acesso ao ambiente analitico
            </DialogTitle>
            <DialogDescription className="max-w-xl text-slate-200">
              Credenciais sao governadas e auditaveis. Use uma chave existente para operar no painel ou registre uma
              solicitacao para avaliacao do time administrador.
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="p-6">
          <Tabs value={tab} onValueChange={setTab} className="space-y-5">
            <TabsList className={`grid w-full ${isAuthenticated ? 'grid-cols-3' : 'grid-cols-2'}`}>
              {isAuthenticated && <TabsTrigger value="session">Sessao atual</TabsTrigger>}
              <TabsTrigger value="existing">Usar chave</TabsTrigger>
              <TabsTrigger value="request">Solicitar acesso</TabsTrigger>
            </TabsList>

            {isAuthenticated && (
              <TabsContent value="session" className="space-y-4">
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">
                  <div className="mb-3 flex items-center gap-2">
                    <ShieldCheckIcon className="size-5 text-emerald-600" />
                    <h3 className="font-semibold text-foreground">Sessao autenticada neste navegador</h3>
                  </div>
                  <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
                    <div className="space-y-2">
                      <Label>Chave em uso</Label>
                      <Input value={maskedApiKey} readOnly className="font-mono tracking-wide" />
                      <p className="text-sm text-muted-foreground">
                        A chave fica apenas nesta sessao do navegador e nao e persistida apos fechar a aba.
                      </p>
                    </div>
                    <Button variant="destructive" onClick={handleClearSession} className="gap-2">
                      <Trash2Icon className="size-4" />
                      Encerrar sessao
                    </Button>
                  </div>
                </div>
              </TabsContent>
            )}

            <TabsContent value="existing" className="space-y-4">
              <div className="rounded-2xl border border-border/70 bg-muted/30 p-5">
                <div className="mb-4 flex items-center gap-2">
                  <LockKeyholeIcon className="size-5 text-primary" />
                  <h3 className="font-semibold">Usar uma credencial existente</h3>
                </div>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="api-key-input">Governed API key</Label>
                    <Input
                      id="api-key-input"
                      value={inputKey}
                      onChange={(event) => setInputKey(event.target.value)}
                      placeholder="ul_abcdef123456_xxxxxxxxxxxxx"
                      className="font-mono"
                    />
                    <p className="text-sm text-muted-foreground">
                      Use a credencial emitida por um administrador. Ela sera mantida apenas durante esta sessao.
                    </p>
                  </div>
                  <Button onClick={handleSaveExistingKey} disabled={!inputKey.trim()} className="gap-2">
                    <KeyRoundIcon className="size-4" />
                    Ativar credencial nesta sessao
                  </Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="request" className="space-y-4">
              {requestResult ? (
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <CheckCircle2Icon className="size-5 text-emerald-600" />
                    <h3 className="font-semibold">Solicitacao registrada</h3>
                  </div>
                  <div className="space-y-3 text-sm">
                    <p className="text-foreground/90">{requestResult.message}</p>
                    <div className="rounded-xl border border-border/70 bg-background px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Request ID</p>
                      <p className="mt-1 font-mono text-sm">{requestResult.requestId}</p>
                    </div>
                    <p className="text-muted-foreground">
                      O endpoint publico nao emite plano elevado nem libera chave automaticamente. A emissao real
                      permanece no fluxo governado do backend.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl border border-border/70 bg-muted/30 p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <MailPlusIcon className="size-5 text-primary" />
                    <h3 className="font-semibold">Solicitar acesso governado</h3>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="request-name">Nome completo</Label>
                      <Input
                        id="request-name"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="Ex: Ana Silva"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="request-email">Email corporativo</Label>
                      <Input
                        id="request-email"
                        type="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        placeholder="ana.silva@org.local"
                      />
                    </div>
                  </div>
                  <div className="mt-4 space-y-2">
                    <Label htmlFor="request-org">Organizacao</Label>
                    <Input
                      id="request-org"
                      value={organization}
                      onChange={(event) => setOrganization(event.target.value)}
                      placeholder="Ex: Urban Safety Operations"
                    />
                  </div>
                  <div className="mt-4 space-y-2">
                    <Label htmlFor="request-use-case">Contexto de uso</Label>
                    <Textarea
                      id="request-use-case"
                      value={useCase}
                      onChange={(event) => setUseCase(event.target.value)}
                      placeholder="Descreva o motivo da solicitacao, o tipo de analise e o contexto operacional."
                      rows={5}
                    />
                  </div>
                  {requestError && <p className="mt-4 text-sm text-destructive">{requestError}</p>}
                  <div className="mt-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <p className="max-w-xl text-sm text-muted-foreground">
                      O cadastro publico registra a solicitacao para triagem. Chaves PRO ou qualquer expansao de
                      privilegio devem ser emitidas manualmente por um administrador.
                    </p>
                    <Button
                      onClick={handleAccessRequest}
                      disabled={isSubmitting || !name.trim() || !email.trim() || !useCase.trim()}
                      className="gap-2"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2Icon className="size-4 animate-spin" />
                          Enviando
                        </>
                      ) : (
                        <>
                          <MailPlusIcon className="size-4" />
                          Registrar solicitacao
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  )
}
