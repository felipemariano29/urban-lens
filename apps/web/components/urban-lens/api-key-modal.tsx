'use client'

import { useCallback, useState } from 'react'
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

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { useApiKey } from '@/contexts/api-key-context'
import { submitAccessRequest } from '@/hooks/use-urban-lens'

interface ApiKeyModalProps {
  trigger?: ReactNode
}

export function ApiKeyModal({ trigger }: ApiKeyModalProps) {
  const { maskedApiKey, setApiKey, clearApiKey, isAuthenticated } = useApiKey()
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState<string>(isAuthenticated ? 'session' : 'existing')
  const [inputKey, setInputKey] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [organization, setOrganization] = useState('')
  const [useCase, setUseCase] = useState('')
  const [isSubmittingRequest, setIsSubmittingRequest] = useState(false)
  const [isActivatingKey, setIsActivatingKey] = useState(false)
  const [requestError, setRequestError] = useState<string | null>(null)
  const [requestResult, setRequestResult] = useState<{ requestId: string; message: string } | null>(null)

  const resetState = useCallback(() => {
    setInputKey('')
    setName('')
    setEmail('')
    setOrganization('')
    setUseCase('')
    setRequestError(null)
    setRequestResult(null)
    setIsSubmittingRequest(false)
    setIsActivatingKey(false)
    setTab(isAuthenticated ? 'session' : 'existing')
  }, [isAuthenticated])

  const handleClose = useCallback(() => {
    setOpen(false)
    resetState()
  }, [resetState])

  const handleSaveExistingKey = useCallback(async () => {
    if (!inputKey.trim()) return

    setIsActivatingKey(true)
    setRequestError(null)

    try {
      await setApiKey(inputKey.trim())
      setInputKey('')
      setTab('session')
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : 'Nao foi possivel validar a chave informada.')
    } finally {
      setIsActivatingKey(false)
    }
  }, [inputKey, setApiKey])

  const handleAccessRequest = useCallback(async () => {
    if (!name.trim() || !email.trim() || !useCase.trim()) {
      setRequestError('Preencha nome, email e objetivo de uso.')
      return
    }

    setIsSubmittingRequest(true)
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
      setIsSubmittingRequest(false)
    }
  }, [email, name, organization, useCase])

  const handleClearSession = useCallback(async () => {
    await clearApiKey()
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
          <Button variant={isAuthenticated ? 'outline' : 'default'} className="gap-2 rounded-full">
            <KeyRoundIcon className="size-4" />
            {isAuthenticated ? 'Credencial ativa' : 'Conectar chave'}
          </Button>
        )}
      </DialogTrigger>

      <DialogContent className="max-w-2xl border-white/10 bg-[#10161e] p-0 text-white backdrop-blur">
        <div className="border-b border-white/10 bg-[#121922] p-6">
          <DialogHeader>
            <div className="mb-3 flex items-center gap-2 text-xs">
              <Badge className="border border-white/10 bg-white/6 text-slate-200 hover:bg-white/6">
                Acesso governado
              </Badge>
              <Badge className="bg-[#7dd3fc] text-[#08202b] hover:bg-[#7dd3fc]">
                Urban Lens Analytics
              </Badge>
            </div>
            <DialogTitle className="text-2xl font-semibold tracking-tight">Gerenciar credencial</DialogTitle>
            <DialogDescription className="max-w-xl text-slate-400">
              A sessao do painel exige uma chave valida. A chave bruta e validada no servidor e fica apenas em
              cookie httpOnly durante esta sessao.
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="p-6">
          <Tabs value={tab} onValueChange={setTab} className="space-y-5">
            <TabsList className={`grid w-full ${isAuthenticated ? 'grid-cols-3' : 'grid-cols-2'}`}>
              {isAuthenticated ? <TabsTrigger value="session">Sessao atual</TabsTrigger> : null}
              <TabsTrigger value="existing">Usar chave</TabsTrigger>
              <TabsTrigger value="request">Solicitar acesso</TabsTrigger>
            </TabsList>

            {isAuthenticated ? (
              <TabsContent value="session" className="space-y-4">
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">
                  <div className="mb-3 flex items-center gap-2">
                    <ShieldCheckIcon className="size-5 text-emerald-500" />
                    <h3 className="font-semibold text-white">Sessao autenticada neste navegador</h3>
                  </div>
                  <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
                    <div className="space-y-2">
                      <Label>Chave em uso</Label>
                      <Input
                        value={maskedApiKey ?? '*******'}
                        readOnly
                        className="border-white/10 bg-black/20 font-mono tracking-wide text-white"
                      />
                      <p className="text-sm text-slate-400">
                        O frontend nao mantem a chave em `localStorage` nem em `sessionStorage`.
                      </p>
                    </div>
                    <Button variant="destructive" onClick={handleClearSession} className="gap-2">
                      <Trash2Icon className="size-4" />
                      Encerrar sessao
                    </Button>
                  </div>
                </div>
              </TabsContent>
            ) : null}

            <TabsContent value="existing" className="space-y-4">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-5">
                <div className="mb-4 flex items-center gap-2">
                  <LockKeyholeIcon className="size-5 text-[#7dd3fc]" />
                  <h3 className="font-semibold text-white">Usar uma chave existente</h3>
                </div>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="api-key-input">API key governada</Label>
                    <Input
                      id="api-key-input"
                      value={inputKey}
                      onChange={(event) => setInputKey(event.target.value)}
                      placeholder="ul_abcdef123456_xxxxxxxxxxxxx"
                      className="border-white/10 bg-[#0d1218] font-mono text-white"
                    />
                    <p className="text-sm text-slate-400">
                      A chave e validada no backend antes de liberar a sessao.
                    </p>
                  </div>

                  {requestError && tab === 'existing' ? (
                    <p className="text-sm text-destructive">{requestError}</p>
                  ) : null}

                  <Button
                    onClick={handleSaveExistingKey}
                    disabled={!inputKey.trim() || isActivatingKey}
                    className="gap-2 rounded-full"
                  >
                    {isActivatingKey ? (
                      <Loader2Icon className="size-4 animate-spin" />
                    ) : (
                      <KeyRoundIcon className="size-4" />
                    )}
                    Ativar nesta sessao
                  </Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="request" className="space-y-4">
              {requestResult ? (
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5 text-white">
                  <div className="mb-4 flex items-center gap-2">
                    <CheckCircle2Icon className="size-5 text-emerald-500" />
                    <h3 className="font-semibold">Solicitacao registrada</h3>
                  </div>
                  <div className="space-y-3 text-sm">
                    <p className="text-slate-200">{requestResult.message}</p>
                    <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Request ID</p>
                      <p className="mt-1 font-mono text-sm">{requestResult.requestId}</p>
                    </div>
                    <p className="text-slate-400">
                      O endpoint publico nao emite chave automaticamente. Emissao, rotacao e revogacao permanecem
                      no fluxo administrativo governado.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl border border-white/10 bg-black/20 p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <MailPlusIcon className="size-5 text-[#7dd3fc]" />
                    <h3 className="font-semibold text-white">Solicitar acesso governado</h3>
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

                  {requestError && tab === 'request' ? (
                    <p className="mt-4 text-sm text-destructive">{requestError}</p>
                  ) : null}

                  <div className="mt-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <p className="max-w-xl text-sm text-slate-400">
                      O cadastro publico registra a solicitacao para triagem. Planos elevados e privilegios extras
                      continuam dependentes de aprovacao manual.
                    </p>
                    <Button
                      onClick={handleAccessRequest}
                      disabled={isSubmittingRequest || !name.trim() || !email.trim() || !useCase.trim()}
                      className="gap-2"
                    >
                      {isSubmittingRequest ? (
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
