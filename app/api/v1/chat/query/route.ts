import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'
const BACKEND_API_KEY = process.env.BACKEND_API_KEY || ''

function buildHeaders() {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (BACKEND_API_KEY) headers['X-API-Key'] = BACKEND_API_KEY
  return headers
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    if (!body.query || typeof body.query !== 'string') {
      return NextResponse.json(
        {
          error: 'VALIDATION_ERROR',
          message: 'One or more request fields are invalid.',
          details: [{ type: 'missing', loc: ['body', 'query'], msg: 'Field required' }],
        },
        { status: 422 }
      )
    }

    // LLM generation can be slow — 60s timeout
    const response = await fetch(`${BACKEND_URL}/api/v1/chat/query`, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(60000),
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (err) {
    if (err instanceof Error && err.name === 'TimeoutError') {
      return NextResponse.json(
        { error: 'TIMEOUT', message: 'O modelo demorou mais de 60s para responder.' },
        { status: 504 }
      )
    }
    return NextResponse.json(
      { error: 'BACKEND_UNAVAILABLE', message: 'Backend service is unavailable.' },
      { status: 502 }
    )
  }
}
