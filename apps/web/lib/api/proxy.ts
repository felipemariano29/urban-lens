import 'server-only'

import { NextRequest, NextResponse } from 'next/server'

const DEFAULT_BACKEND_API_BASE_URL = `http://localhost:${process.env.RAG_API_HOST_PORT || '8000'}`
const DEFAULT_PROXY_TIMEOUT_MS = 180_000

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value
}

function getBackendApiBaseUrl(): string {
  const configured = process.env.URBAN_LENS_API_BASE_URL?.trim()
  if (!configured) {
    return DEFAULT_BACKEND_API_BASE_URL
  }
  return trimTrailingSlash(configured)
}

function buildBackendApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getBackendApiBaseUrl()}${normalizedPath}`
}

function buildUpstreamHeaders(request: NextRequest, initHeaders?: HeadersInit): Headers {
  const headers = new Headers(initHeaders)
  const contentType = request.headers.get('content-type')
  const requestId = request.headers.get('x-request-id')
  const authorization = request.headers.get('authorization')
  const apiKey = request.headers.get('x-api-key')

  if (contentType && !headers.has('Content-Type')) {
    headers.set('Content-Type', contentType)
  }
  if (requestId && !headers.has('X-Request-ID')) {
    headers.set('X-Request-ID', requestId)
  }
  if (authorization && !headers.has('Authorization')) {
    headers.set('Authorization', authorization)
  }
  if (apiKey && !headers.has('X-API-Key')) {
    headers.set('X-API-Key', apiKey)
  }
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json')
  }

  return headers
}

async function toProxyResponse(upstream: Response): Promise<NextResponse> {
  const body = await upstream.text()
  const headers = new Headers()
  const contentType = upstream.headers.get('content-type')
  const requestId = upstream.headers.get('x-request-id')

  if (contentType) {
    headers.set('content-type', contentType)
  }
  if (requestId) {
    headers.set('x-request-id', requestId)
  }

  return new NextResponse(body, {
    status: upstream.status,
    headers,
  })
}

export async function proxyUrbanLensRequest(
  request: NextRequest,
  path: string,
  init?: RequestInit
): Promise<NextResponse> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), DEFAULT_PROXY_TIMEOUT_MS)

  try {
    const upstream = await fetch(buildBackendApiUrl(path), {
      ...init,
      headers: buildUpstreamHeaders(request, init?.headers),
      cache: 'no-store',
      signal: controller.signal,
    })
    return await toProxyResponse(upstream)
  } catch (error) {
    const message =
      error instanceof Error && error.name === 'AbortError'
        ? 'Urban Lens API timed out while processing the request.'
        : 'Urban Lens API is unavailable.'

    return NextResponse.json(
      {
        error: 'BAD_GATEWAY',
        message,
        details: [],
      },
      { status: 502 }
    )
  } finally {
    clearTimeout(timeout)
  }
}
