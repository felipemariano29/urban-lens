import { NextRequest } from 'next/server'

import { proxyUrbanLensRequest } from '@/lib/api/proxy'

export async function POST(request: NextRequest) {
  const body = await request.text()

  return proxyUrbanLensRequest(request, '/api/v1/query', {
    method: 'POST',
    body,
  })
}
