"""Demonstracao simples do fluxo RAG via API HTTP."""

from __future__ import annotations

import json
import os
import urllib.request

API_URL = os.getenv("URBAN_LENS_DEMO_API_URL", "http://localhost:8000")
API_KEY = os.getenv("URBAN_LENS_DEMO_API_KEY", "urban-lens-api-key-2026")


def _post(endpoint: str, data: dict) -> dict:
    payload = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        f"{API_URL}{endpoint}",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _get(endpoint: str) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{API_URL}{endpoint}",
        headers={"X-API-Key": API_KEY},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except Exception:
        return 0, {}


def demo_search() -> None:
    print("=" * 60)
    print("1. BUSCA SEMANTICA")
    print("=" * 60)

    data = _post("/api/v1/query", {"query": "burglary incidents", "top_k": 3})
    print("\nQuery: 'burglary incidents'")
    print(f"Resultados: {len(data.get('results', []))}\n")

    for index, result in enumerate(data.get("results", []), start=1):
        print(f"[{index}] Score: {result['score']:.3f}")
        print(f"    {result['content'][:100]}...")
        print()


def demo_rag_chat() -> None:
    print("=" * 60)
    print("2. RAG COMPLETO")
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
    print(f"Evidencias citadas: {len(data.get('evidences', []))}")

    print("\nEVIDENCIAS:")
    for evidence in data.get("evidences", []):
        print(f"  [{evidence['id']}] {evidence['source']} (score: {evidence['score']:.3f})")


def main() -> None:
    print("\nUrban Lens - Demonstracao do RAG\n")

    status, _ = _get("/api/v1/health")
    if status not in (200, 207):
        print("API nao esta respondendo.")
        return

    print("API online.\n")
    demo_search()
    print("\n")
    demo_rag_chat()
    print("\nDemonstracao concluida.")


if __name__ == "__main__":
    main()
