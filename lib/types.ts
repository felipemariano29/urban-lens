// Urban-Lens Types

export type AppState = 'idle' | 'loading' | 'results' | 'error' | 'empty'
export type QueryMode = 'search' | 'chat'

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

// Chat / RAG types
export interface RagAnswer {
  text: string
  status: 'answered' | 'insufficient_evidence'
  model: string
}

export interface EvidenceCitation {
  id: string
  source: string
  reference: string
  score: number
  timestamp: string
  excerpt: string
  metadata: Record<string, unknown>
}

export interface RagContextChunk {
  id: string
  content: string
  score: number
  source: string
  reference: string
  timestamp: string
  metadata: Record<string, unknown>
}

export type AccessProfile = 'intel_user' | 'developer' | 'admin'

export interface ChatQueryRequest {
  query: string
  filters?: Partial<QueryFilters> | null
  top_k?: number
  model?: string
}

export interface ChatQueryResponse {
  answer: RagAnswer
  evidences: EvidenceCitation[]
  context: RagContextChunk[]
  profile: AccessProfile
  fallback_reason: string | null
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
