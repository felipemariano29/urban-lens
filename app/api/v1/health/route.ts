import { NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/health`, {
      signal: AbortSignal.timeout(5000),
    })
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch {
    return NextResponse.json(
      {
        status: 'degraded',
        dependencies: {
          catalog: 'unavailable',
          rag_embedder: 'unavailable',
          rag_vector_store: 'unavailable',
        },
      },
      { status: 200 }
    )
  }
}
