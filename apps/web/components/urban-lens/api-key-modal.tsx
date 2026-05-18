'use client'

import { useState, useCallback } from 'react'
import { KeyIcon, PlusIcon, EyeIcon, EyeOffIcon, CopyIcon, CheckIcon, Loader2Icon } from 'lucide-react'

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useApiKey } from '@/contexts/api-key-context'
import { getBackendApiBaseUrl } from '@/lib/api/client'

const PLAN_OPTIONS = [
  { value: 'free', label: 'Free', description: '100 requisições/dia' },
  { value: 'basic', label: 'Basic', description: '1.000 requisições/dia' },
  { value: 'pro', label: 'Pro', description: '10.000 requisições/dia' },
  { value: 'enterprise', label: 'Enterprise', description: 'Ilimitado' },
]

interface ApiKeyModalProps {
  trigger?: React.ReactNode
}

export function ApiKeyModal({ trigger }: ApiKeyModalProps) {
  const { apiKey, setApiKey, clearApiKey, isAuthenticated } = useApiKey()
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState<string>(isAuthenticated ? 'current' : 'enter')

  // Enter key state
  const [inputKey, setInputKey] = useState('')
  const [showKey, setShowKey] = useState(false)

  // Create key state
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [plan, setPlan] = useState('free')
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleSaveKey = useCallback(() => {
    if (inputKey.trim()) {
      setApiKey(inputKey.trim())
      setInputKey('')
      setOpen(false)
    }
  }, [inputKey, setApiKey])

  const handleCreateKey = useCallback(async () => {
    if (!name.trim() || !email.trim()) {
      setCreateError('Nome e email são obrigatórios')
      return
    }

    setIsCreating(true)
    setCreateError(null)

    try {
      const response = await fetch(`${getBackendApiBaseUrl()}/system/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          plan,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || 'Erro ao criar API key')
      }

      const data = await response.json()
      setCreatedKey(data.api_key)
      setApiKey(data.api_key)
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : 'Erro desconhecido')
    } finally {
      setIsCreating(false)
    }
  }, [name, email, plan, setApiKey])

  const handleCopyKey = useCallback(async () => {
    if (createdKey) {
      await navigator.clipboard.writeText(createdKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [createdKey])

  const handleClear = useCallback(() => {
    clearApiKey()
    setTab('enter')
  }, [clearApiKey])

  const handleClose = useCallback(() => {
    setOpen(false)
    setInputKey('')
    setName('')
    setEmail('')
    setPlan('free')
    setCreateError(null)
    setCreatedKey(null)
    setCopied(false)
  }, [])

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      if (!isOpen) handleClose()
      else setOpen(true)
    }}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant={isAuthenticated ? 'outline' : 'default'} size="sm" className="gap-2">
            <KeyIcon className="size-4" />
            {isAuthenticated ? 'API Key' : 'Configurar API Key'}
          </Button>
        )}
      </DialogTrigger>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyIcon className="size-5" />
            Configuração de API Key
          </DialogTitle>
          <DialogDescription>
            Configure sua API key para acessar os recursos do Urban-Lens.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={setTab} className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            {isAuthenticated && <TabsTrigger value="current">Atual</TabsTrigger>}
            <TabsTrigger value="enter">Inserir</TabsTrigger>
            <TabsTrigger value="create">Criar</TabsTrigger>
          </TabsList>

          {isAuthenticated && (
            <TabsContent value="current" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>API Key ativa</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type={showKey ? 'text' : 'password'}
                    value={apiKey || ''}
                    readOnly
                    className="font-mono text-sm"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowKey(!showKey)}
                  >
                    {showKey ? <EyeOffIcon className="size-4" /> : <EyeIcon className="size-4" />}
                  </Button>
                </div>
              </div>
              <Button variant="destructive" onClick={handleClear} className="w-full">
                Remover API Key
              </Button>
            </TabsContent>
          )}

          <TabsContent value="enter" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="api-key-input">API Key</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="api-key-input"
                  type={showKey ? 'text' : 'password'}
                  placeholder="ul_xxxxxxxxxxxxxxxx"
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value)}
                  className="font-mono text-sm"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowKey(!showKey)}
                >
                  {showKey ? <EyeOffIcon className="size-4" /> : <EyeIcon className="size-4" />}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Cole sua API key existente ou crie uma nova na aba "Criar".
              </p>
            </div>
            <Button onClick={handleSaveKey} disabled={!inputKey.trim()} className="w-full">
              Salvar API Key
            </Button>
          </TabsContent>

          <TabsContent value="create" className="space-y-4 mt-4">
            {createdKey ? (
              <div className="space-y-4">
                <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950">
                  <p className="text-sm font-medium text-green-800 dark:text-green-200 mb-2">
                    API Key criada com sucesso!
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400 mb-3">
                    Guarde esta chave em local seguro. Ela não será exibida novamente.
                  </p>
                  <div className="flex items-center gap-2">
                    <Input
                      type="text"
                      value={createdKey}
                      readOnly
                      className="font-mono text-xs bg-white dark:bg-black"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={handleCopyKey}
                    >
                      {copied ? (
                        <CheckIcon className="size-4 text-green-600" />
                      ) : (
                        <CopyIcon className="size-4" />
                      )}
                    </Button>
                  </div>
                </div>
                <Button onClick={handleClose} className="w-full">
                  Fechar
                </Button>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="create-name">Nome</Label>
                  <Input
                    id="create-name"
                    placeholder="Seu nome ou organização"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="create-email">Email</Label>
                  <Input
                    id="create-email"
                    type="email"
                    placeholder="seu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="create-plan">Plano</Label>
                  <Select value={plan} onValueChange={setPlan}>
                    <SelectTrigger id="create-plan">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PLAN_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          <span className="flex items-center gap-2">
                            <span className="font-medium">{option.label}</span>
                            <span className="text-muted-foreground text-xs">
                              ({option.description})
                            </span>
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {createError && (
                  <p className="text-sm text-destructive">{createError}</p>
                )}

                <Button
                  onClick={handleCreateKey}
                  disabled={isCreating || !name.trim() || !email.trim()}
                  className="w-full gap-2"
                >
                  {isCreating ? (
                    <>
                      <Loader2Icon className="size-4 animate-spin" />
                      Criando...
                    </>
                  ) : (
                    <>
                      <PlusIcon className="size-4" />
                      Criar API Key
                    </>
                  )}
                </Button>
              </>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
