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
  model?: string
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

export interface RagAnswer {
  text: string
  status: 'answered' | 'insufficient_evidence'
  model: string
}

export interface RagChunkMetadata {
  chunk_type?: string
  reference_month?: string
  lsoa_code?: string
  crime_type?: string
  title?: string
  dataset_version_id?: string
  run_id?: string
  experiment_id?: string
  artifact_uri?: string
  [key: string]: unknown
}

export interface EvidenceCitation {
  id: string
  source: string
  reference: string
  score: number
  timestamp: string
  excerpt: string
  metadata: RagChunkMetadata
}

export interface RagContextChunk {
  id: string
  content: string
  score: number
  source: string
  reference: string
  timestamp: string
  metadata: RagChunkMetadata
}

export interface ChatQueryResponse {
  answer: RagAnswer
  evidences: EvidenceCitation[]
  context: RagContextChunk[]
  profile: 'intel_user' | 'developer' | 'admin'
  fallback_reason: string | null
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

export interface OllamaModelInfo {
  name: string
  size_bytes?: number | null
  digest?: string | null
  modified_at?: string | null
}

export interface AvailableModelsResponse {
  default_chat_model: string
  default_embedding_model: string
  models: OllamaModelInfo[]
}

export interface HistoryItem {
  id: string
  query: string
  filters: QueryFilters
  topK: number
  model: string
  response: ChatQueryResponse | null
  latency: number | null
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

export interface CrimeTypeOption {
  label: string
  value: string | null
}

export const CRIME_TYPE_OPTIONS: CrimeTypeOption[] = [
  { label: 'Todos', value: null },
  { label: 'Anti-social behaviour', value: 'anti_social_behaviour' },
  { label: 'Bicycle theft', value: 'bicycle_theft' },
  { label: 'Burglary', value: 'burglary' },
  { label: 'Criminal damage and arson', value: 'criminal_damage_and_arson' },
  { label: 'Drugs', value: 'drugs' },
  { label: 'Other crime', value: 'other_crime' },
  { label: 'Other theft', value: 'other_theft' },
  { label: 'Possession of weapons', value: 'possession_of_weapons' },
  { label: 'Public order', value: 'public_order' },
  { label: 'Robbery', value: 'robbery' },
  { label: 'Shoplifting', value: 'shoplifting' },
  { label: 'Theft from the person', value: 'theft_from_the_person' },
  { label: 'Vehicle crime', value: 'vehicle_crime' },
  {
    label: 'Violence and sexual offences',
    value: 'violence_and_sexual_offences',
  },
]
