import type { ChatQueryResponse, EvidenceCitation, RagChunkMetadata } from '@/lib/types'

const CRIME_TYPE_PT_LABELS: Record<string, string> = {
  anti_social_behaviour: 'Comportamento antissocial',
  bicycle_theft: 'Furto de bicicleta',
  burglary: 'Furto qualificado',
  criminal_damage_and_arson: 'Dano criminal e incendio',
  drugs: 'Drogas',
  other_crime: 'Outros crimes',
  other_theft: 'Outros furtos',
  possession_of_weapons: 'Posse de armas',
  public_order: 'Ordem publica',
  robbery: 'Roubo',
  shoplifting: 'Furto em comercio',
  theft_from_the_person: 'Furto contra a pessoa',
  vehicle_crime: 'Crime veicular',
  violence_and_sexual_offences: 'Violencia e delitos sexuais',
}

const CHUNK_TYPE_PT_LABELS: Record<string, string> = {
  area_month: 'Panorama da area',
  area_month_category: 'Categoria por area',
  area_month_top_crimes: 'Ranking da area',
  month_category: 'Categoria do mes',
  month_top_crimes: 'Ranking do mes',
}

const PROFILE_PT_LABELS: Record<string, string> = {
  intel_user: 'inteligencia',
  developer: 'desenvolvimento',
  admin: 'administracao',
}

const CRIME_TYPE_LABELS_PT = Object.values(CRIME_TYPE_PT_LABELS)

export function formatCrimeTypePt(value: string | null | undefined): string | null {
  if (!value) return null
  const normalized = value.trim().toLowerCase()
  return CRIME_TYPE_PT_LABELS[normalized] ?? humanizeToken(normalized)
}

export function formatChunkTypePt(value: string | null | undefined): string | null {
  if (!value) return null
  return CHUNK_TYPE_PT_LABELS[value] ?? humanizeToken(value)
}

export function formatProfilePt(value: ChatQueryResponse['profile']): string {
  return PROFILE_PT_LABELS[value] ?? value
}

export function normalizeAnswerText(text: string): string {
  let normalized = text

  for (const [raw, label] of Object.entries(CRIME_TYPE_PT_LABELS)) {
    normalized = normalized.replace(new RegExp(`\\b${escapeRegExp(raw)}\\b`, 'gi'), label)
  }

  normalized = normalized
    .replace(/\bincidents\b/gi, 'incidentes')
    .replace(/\bincident\b/gi, 'incidente')
    .replace(/\bcrime type\b/gi, 'tipo de crime')
    .replace(/\bdominant crime type\b/gi, 'tipo de crime dominante')
    .replace(/\barea\b/gi, 'area')

  return normalized
}

export function extractCrimeTypesFromAnswer(text: string): string[] {
  const normalized = normalizeAnswerText(text).toLowerCase()
  return CRIME_TYPE_LABELS_PT.filter((label) => normalized.includes(label.toLowerCase()))
}

export function summarizeEvidence(response: ChatQueryResponse): {
  months: string[]
  crimeTypes: string[]
  chunkTypes: string[]
  lsoaCodes: string[]
} {
  const metadataList = response.evidences.map((evidence) => evidence.metadata)
  return {
    months: unique(metadataList.map((metadata) => str(metadata.reference_month))),
    crimeTypes: unique(metadataList.map((metadata) => formatCrimeTypePt(str(metadata.crime_type))).filter(Boolean)),
    chunkTypes: unique(metadataList.map((metadata) => formatChunkTypePt(str(metadata.chunk_type))).filter(Boolean)),
    lsoaCodes: unique(metadataList.map((metadata) => str(metadata.lsoa_code))),
  }
}

export function formatEvidenceTitle(evidence: EvidenceCitation, rank: number): string {
  return evidence.source || str(evidence.metadata.title) || `Evidencia ${rank}`
}

export function summarizeMetadata(metadata: RagChunkMetadata): Array<{ label: string; value: string }> {
  const items: Array<{ label: string; value: string | null }> = [
    { label: 'Tipo de crime', value: formatCrimeTypePt(str(metadata.crime_type)) },
    { label: 'Escopo', value: formatChunkTypePt(str(metadata.chunk_type)) },
    { label: 'LSOA', value: str(metadata.lsoa_code) },
    { label: 'Mes ref.', value: str(metadata.reference_month) },
    { label: 'Dataset', value: str(metadata.dataset_version_id) },
  ]

  return items.filter((item): item is { label: string; value: string } => Boolean(item.value))
}

function str(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value : null
}

function unique(values: Array<string | null | undefined>): string[] {
  return [...new Set(values.filter((value): value is string => Boolean(value)))]
}

function humanizeToken(value: string): string {
  return value
    .split('_')
    .filter(Boolean)
    .map((part, index) => (index === 0 ? capitalize(part) : part.toLowerCase()))
    .join(' ')
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
