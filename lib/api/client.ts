const DEFAULT_FRONTEND_API_BASE_URL = '/api/v1'
const DEFAULT_BACKEND_API_BASE_URL = 'http://localhost:8000/api/v1'

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value
}

export function getFrontendApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim()
  if (!configured) {
    return DEFAULT_FRONTEND_API_BASE_URL
  }
  return trimTrailingSlash(configured)
}

export function getBackendApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_BACKEND_URL?.trim()
  if (!configured) {
    return DEFAULT_BACKEND_API_BASE_URL
  }
  return trimTrailingSlash(configured)
}

export function buildFrontendApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getFrontendApiBaseUrl()}${normalizedPath}`
}

export function buildBackendApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getBackendApiBaseUrl()}${normalizedPath}`
}
