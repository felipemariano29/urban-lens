// Urban-Lens Types

export type AppState = 'idle' | 'loading' | 'results' | 'error' | 'empty'

export interface QueryFilters {
  crime_type: string | null
  lsoa_code: string | null
  reference_month: string | null
}

export interface QueryRequest {
  query: string
  filters?: QueryFilters | null
  top_k?: number
}

export interface ResultMetadata {
  chunk_type?: string
  reference_month?: string
  lsoa_code?: string
  crime_type?: string
  title?: string
  dataset_version_id?: string
}

export interface QueryResult {
  id: string
  score: number
  content: string
  metadata: ResultMetadata
}

export interface QueryResponse {
  results: QueryResult[]
}

export interface HealthDependencies {
  catalog: 'ok' | 'unavailable'
  rag_embedder: 'ok' | 'unavailable'
  rag_vector_store: 'ok' | 'unavailable'
}

export interface HealthResponse {
  status: 'healthy' | 'degraded'
  version?: string
  timestamp?: string
  dependencies: HealthDependencies
}

export interface HistoryItem {
  id: string
  query: string
  filters: QueryFilters
  timestamp: Date
}

export interface APIError {
  error: string
  message: string
  details?: Array<{
    type: string
    loc: string[]
    msg: string
  }>
}

// Crime types from DATA.POLICE.UK
export const CRIME_TYPES = [
  'Todos',
  'Anti-social behaviour',
  'Bicycle theft',
  'Burglary',
  'Criminal damage and arson',
  'Drugs',
  'Other crime',
  'Other theft',
  'Possession of weapons',
  'Public order',
  'Robbery',
  'Shoplifting',
  'Theft from the person',
  'Vehicle crime',
  'Violence and sexual offences',
] as const

export type CrimeType = (typeof CRIME_TYPES)[number]
