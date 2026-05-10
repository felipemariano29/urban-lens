import { NextResponse } from 'next/server'

// Mock health endpoint para demonstração
// Em produção, isso seria proxy para a API real
export async function GET() {
  // Simular verificação de saúde dos serviços
  const mockResponse = {
    status: 'healthy' as const,
    version: '0.1.0',
    timestamp: new Date().toISOString(),
    dependencies: {
      catalog: 'ok' as const,
      rag_embedder: 'ok' as const,
      rag_vector_store: 'ok' as const,
    },
  }

  return NextResponse.json(mockResponse)
}
