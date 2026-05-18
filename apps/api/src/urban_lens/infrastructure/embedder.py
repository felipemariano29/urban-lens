"""Ollama-backed text embedding generation."""

from __future__ import annotations

import json
import urllib.request


class OllamaEmbedder:
    DEFAULT_MODEL = "nomic-embed-text"
    EMBEDDING_DIM = 768

    def __init__(self, base_url: str, model: str = DEFAULT_MODEL) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one 768-dimensional embedding vector per input text."""
        if not texts:
            return []
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result["embeddings"]

    def health_check(self) -> bool:
        """Return True if the Ollama server is reachable and the model is available."""
        try:
            request = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False
