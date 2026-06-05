import { NextRequest } from 'next/server'

import { proxyUrbanLensRequest } from '@/lib/api/proxy'

export async function GET(request: NextRequest) {
  return proxyUrbanLensRequest(request, '/api/v1/access/me/usage', {
    method: 'GET',
  })
}
