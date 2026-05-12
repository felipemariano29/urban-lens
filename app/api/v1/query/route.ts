import { NextRequest, NextResponse } from 'next/server'

// Mock query endpoint para demonstração
// Em produção, isso seria proxy para a API real

interface QueryRequest {
  query: string
  filters?: {
    crime_type?: string
    lsoa_code?: string
    reference_month?: string
  }
  top_k?: number
}

// Dados mockados para demonstração
const MOCK_RESULTS = [
  {
    id: 'chunk-e01001234-2024-01',
    score: 0.92,
    content:
      'In January 2024, Westminster recorded 3 burglaries in LSOA E01001234. This represents a 15% decrease compared to the same period in 2023. The majority of incidents occurred during nighttime hours between 10pm and 4am.',
    metadata: {
      chunk_type: 'area_month',
      reference_month: '2024-01',
      lsoa_code: 'E01001234',
      crime_type: 'Burglary',
      title: 'Westminster 2024-01',
      dataset_version_id: 'v1',
    },
  },
  {
    id: 'chunk-e01001234-2024-02',
    score: 0.85,
    content:
      'In February 2024, Westminster recorded 2 burglaries in LSOA E01001234. The trend continues to show improvement with focused community policing efforts in the area.',
    metadata: {
      chunk_type: 'area_month',
      reference_month: '2024-02',
      lsoa_code: 'E01001234',
      crime_type: 'Burglary',
      title: 'Westminster 2024-02',
      dataset_version_id: 'v1',
    },
  },
  {
    id: 'chunk-e01001567-2024-01',
    score: 0.78,
    content:
      'In January 2024, Camden recorded 5 burglaries in LSOA E01001567. This area has seen increased activity compared to neighboring regions.',
    metadata: {
      chunk_type: 'area_month',
      reference_month: '2024-01',
      lsoa_code: 'E01001567',
      crime_type: 'Burglary',
      title: 'Camden 2024-01',
      dataset_version_id: 'v1',
    },
  },
  {
    id: 'chunk-e01001234-2023-12',
    score: 0.71,
    content:
      'In December 2023, Westminster recorded 4 burglaries in LSOA E01001234. Holiday season typically shows increased property crime rates.',
    metadata: {
      chunk_type: 'area_month',
      reference_month: '2023-12',
      lsoa_code: 'E01001234',
      crime_type: 'Burglary',
      title: 'Westminster 2023-12',
      dataset_version_id: 'v1',
    },
  },
  {
    id: 'chunk-e01001890-2024-01',
    score: 0.65,
    content:
      'In January 2024, Hackney recorded 7 incidents of violence and sexual offences in LSOA E01001890. This includes both domestic and public incidents.',
    metadata: {
      chunk_type: 'area_month',
      reference_month: '2024-01',
      lsoa_code: 'E01001890',
      crime_type: 'Violence and sexual offences',
      title: 'Hackney 2024-01',
      dataset_version_id: 'v1',
    },
  },
  {
    id: 'chunk-e01002345-2024-01',
    score: 0.58,
    content:
      'In January 2024, Islington recorded 12 incidents of anti-social behaviour in LSOA E01002345. Most incidents were noise complaints and public disturbances.',
    metadata: {
      chunk_type: 'area_month',
      reference_month: '2024-01',
      lsoa_code: 'E01002345',
      crime_type: 'Anti-social behaviour',
      title: 'Islington 2024-01',
      dataset_version_id: 'v1',
    },
  },
]

export async function POST(request: NextRequest) {
  try {
    const body: QueryRequest = await request.json()

    // Validação básica
    if (!body.query || typeof body.query !== 'string') {
      return NextResponse.json(
        {
          error: 'VALIDATION_ERROR',
          message: 'One or more request fields are invalid.',
          details: [
            { type: 'missing', loc: ['body', 'query'], msg: 'Field required' },
          ],
        },
        { status: 422 }
      )
    }

    const topK = body.top_k ?? 5
    if (topK < 1 || topK > 20) {
      return NextResponse.json(
        {
          error: 'VALIDATION_ERROR',
          message: 'One or more request fields are invalid.',
          details: [
            {
              type: 'value_error',
              loc: ['body', 'top_k'],
              msg: 'top_k must be between 1 and 20',
            },
          ],
        },
        { status: 422 }
      )
    }

    // Simular latência de rede
    await new Promise((resolve) => setTimeout(resolve, 500 + Math.random() * 500))

    // Filtrar resultados mockados baseado nos filtros
    let filteredResults = [...MOCK_RESULTS]

    if (body.filters?.crime_type) {
      filteredResults = filteredResults.filter(
        (r) => r.metadata.crime_type === body.filters?.crime_type
      )
    }

    if (body.filters?.lsoa_code) {
      filteredResults = filteredResults.filter(
        (r) => r.metadata.lsoa_code === body.filters?.lsoa_code
      )
    }

    if (body.filters?.reference_month) {
      filteredResults = filteredResults.filter(
        (r) => r.metadata.reference_month === body.filters?.reference_month
      )
    }

    // Aplicar top_k
    const results = filteredResults.slice(0, topK)

    return NextResponse.json({ results })
  } catch {
    return NextResponse.json(
      {
        error: 'INTERNAL_ERROR',
        message: 'An unexpected error occurred.',
      },
      { status: 500 }
    )
  }
}
