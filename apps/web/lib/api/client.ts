const DEFAULT_FRONTEND_API_BASE_URL = '/api/v1'

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

export function buildFrontendApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getFrontendApiBaseUrl()}${normalizedPath}`
}
