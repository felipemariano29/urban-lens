import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

import { proxyUrbanLensRequest } from '@/lib/api/proxy'
import { decryptApiKey, encryptApiKey, getSessionCookieName, maskApiKey } from '@/lib/api/session'

interface SessionCreateRequest {
  apiKey?: string
}

async function readRequestBody(request: NextRequest): Promise<SessionCreateRequest> {
  try {
    return (await request.json()) as SessionCreateRequest
  } catch {
    return {}
  }
}

function buildSessionCookieOptions() {
  return {
    httpOnly: true,
    sameSite: 'lax' as const,
    secure: process.env.NODE_ENV === 'production',
    path: '/',
  }
}

export async function GET(request: NextRequest) {
  const cookieStore = await cookies()
  const encrypted = cookieStore.get(getSessionCookieName())?.value
  const apiKey = decryptApiKey(encrypted)

  if (!apiKey) {
    return NextResponse.json({
      authenticated: false,
      masked_key: null,
    })
  }

  const upstream = await proxyUrbanLensRequest(request, '/api/v1/access/me', {
    method: 'GET',
    headers: {
      'X-API-Key': apiKey,
    },
  })

  if (!upstream.ok) {
    const response = NextResponse.json({
      authenticated: false,
      masked_key: null,
    })
    response.cookies.delete(getSessionCookieName())
    return response
  }

  const profile = await upstream.json()
  return NextResponse.json({
    authenticated: true,
    masked_key: maskApiKey(apiKey),
    profile,
  })
}

export async function POST(request: NextRequest) {
  const body = await readRequestBody(request)
  const apiKey = body.apiKey?.trim()

  if (!apiKey) {
    return NextResponse.json(
      {
        error: 'BAD_REQUEST',
        message: 'Informe uma API key valida para iniciar a sessao.',
      },
      { status: 400 }
    )
  }

  const upstream = await proxyUrbanLensRequest(request, '/api/v1/access/me', {
    method: 'GET',
    headers: {
      'X-API-Key': apiKey,
    },
  })

  if (!upstream.ok) {
    const bodyText = await upstream.text()
    return new NextResponse(bodyText, {
      status: upstream.status,
      headers: {
        'content-type': upstream.headers.get('content-type') || 'application/json',
      },
    })
  }

  const profile = await upstream.json()
  const response = NextResponse.json({
    authenticated: true,
    masked_key: maskApiKey(apiKey),
    profile,
  })
  response.cookies.set(getSessionCookieName(), encryptApiKey(apiKey), buildSessionCookieOptions())
  return response
}

export async function DELETE() {
  const response = NextResponse.json({ authenticated: false, masked_key: null })
  response.cookies.delete(getSessionCookieName())
  return response
}
