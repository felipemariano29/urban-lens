import 'server-only'

import { createCipheriv, createDecipheriv, createHash, randomBytes } from 'node:crypto'

const SESSION_COOKIE_NAME = 'urban_lens_session'
const SESSION_ALGORITHM = 'aes-256-gcm'
const IV_LENGTH = 12
const AUTH_TAG_LENGTH = 16
const FALLBACK_SECRET = 'urban-lens-dev-session-secret'

function toBase64Url(buffer: Buffer): string {
  return buffer
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
}

function fromBase64Url(value: string): Buffer {
  const padding = (4 - (value.length % 4)) % 4
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat(padding)
  return Buffer.from(normalized, 'base64')
}

function getSessionKey(): Buffer {
  const secret = process.env.URBAN_LENS_WEB_SESSION_SECRET?.trim() || FALLBACK_SECRET
  return createHash('sha256').update(secret).digest()
}

export function getSessionCookieName(): string {
  return SESSION_COOKIE_NAME
}

export function maskApiKey(value: string): string {
  if (value.length <= 12) return '********'
  return `${value.slice(0, 7)}******${value.slice(-6)}`
}

export function encryptApiKey(apiKey: string): string {
  const iv = randomBytes(IV_LENGTH)
  const cipher = createCipheriv(SESSION_ALGORITHM, getSessionKey(), iv)
  const encrypted = Buffer.concat([cipher.update(apiKey, 'utf8'), cipher.final()])
  const authTag = cipher.getAuthTag()
  return [iv, authTag, encrypted].map(toBase64Url).join('.')
}

export function decryptApiKey(payload: string | undefined): string | null {
  if (!payload) return null

  const parts = payload.split('.')
  if (parts.length !== 3) return null

  try {
    const [ivPart, authTagPart, encryptedPart] = parts
    const iv = fromBase64Url(ivPart)
    const authTag = fromBase64Url(authTagPart)
    const encrypted = fromBase64Url(encryptedPart)

    if (iv.length !== IV_LENGTH || authTag.length !== AUTH_TAG_LENGTH) {
      return null
    }

    const decipher = createDecipheriv(SESSION_ALGORITHM, getSessionKey(), iv)
    decipher.setAuthTag(authTag)
    const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()])
    return decrypted.toString('utf8')
  } catch {
    return null
  }
}
