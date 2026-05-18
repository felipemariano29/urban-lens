"""Demo script para demonstrar o RAG funcionando (sem dependências externas)."""

import json
import urllib.request

API_URL = "http://localhost:8000"
API_KEY = "urban-lens-api-key-2026"


def _post(endpoint: str, data: dict) -> dict:
    """Faz POST request usando apenas stdlib."""
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}{endpoint}",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(endpoint: str) -> tuple[int, dict]:
    """Faz GET request usando apenas stdlib."""
    req = urllib.request.Request(
        f"{API_URL}{endpoint}",
        headers={"X-API-Key": API_KEY},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except Exception:
        return 0, {}


def demo_search():
    """Demonstra busca semântica sem geração."""
    print("=" * 60)
    print("1. BUSCA SEMÂNTICA (sem LLM)")
    print("=" * 60)

    data = _post("/api/v1/query", {"query": "burglary incidents", "top_k": 3})

    print(f"\nQuery: 'burglary incidents'")
    print(f"Resultados: {len(data.get('results', []))}\n")

    for i, result in enumerate(data.get("results", []), 1):
        print(f"[{i}] Score: {result['score']:.3f}")
        print(f"    {result['content'][:100]}...")
        print()


def demo_rag_chat():
    """Demonstra RAG completo com geração LLM."""
    print("=" * 60)
    print("2. RAG COMPLETO (com geração Ollama)")
    print("=" * 60)

    query = "What are the main crime patterns in January 2024?"
    print(f"\nPergunta: {query}\n")

    data = _post("/api/v1/chat/query", {"query": query, "top_k": 5, "model": "llama3"})

    print("RESPOSTA GERADA:")
    print("-" * 40)
    print(data["answer"]["text"])
    print("-" * 40)

    print(f"\nStatus: {data['answer']['status']}")
    print(f"Modelo: {data['answer']['model']}")
    print(f"Evidências citadas: {len(data.get('evidences', []))}")

    print("\nEVIDÊNCIAS:")
    for ev in data.get("evidences", []):
        print(f"  [{ev['id']}] {ev['source']} (score: {ev['score']:.3f})")


def main():
    print("\n🔍 DEMONSTRAÇÃO DO RAG - Urban Lens\n")

    # Verificar health
    status, _ = _get("/api/v1/health")
    if status != 200:
        print("❌ API não está respondendo!")
        return

    print("✅ API online\n")

    demo_search()
    print("\n")
    demo_rag_chat()

    print("\n✅ Demonstração concluída!")


if __name__ == "__main__":
    main()
