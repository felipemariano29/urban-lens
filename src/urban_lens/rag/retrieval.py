"""Retrieval interfaces and minimal implementations for RAG context assembly."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from urban_lens.rag.contracts import QueryIntent, RetrievalMethod, TOP_K_DEFAULT
from urban_lens.rag.schemas import RetrievalContext, RetrievedChunk


class RetrieverInterface(ABC):
    @abstractmethod
    def retrieve(self, query: str, top_k: int = TOP_K_DEFAULT) -> RetrievalContext:
        raise NotImplementedError


class InMemoryRetriever(RetrieverInterface):
    def __init__(self, chunks: list[RetrievedChunk], *, query_intent: QueryIntent = QueryIntent.FACTUAL) -> None:
        self._chunks = chunks
        self._query_intent = query_intent

    def retrieve(self, query: str, top_k: int = TOP_K_DEFAULT) -> RetrievalContext:
        sorted_chunks = sorted(self._chunks, key=lambda chunk: chunk.relevance_score, reverse=True)
        selected = sorted_chunks[:top_k]
        return RetrievalContext(
            query=query,
            query_intent=self._query_intent,
            chunks=selected,
            coverage_period=self._derive_coverage_period(selected),
            geographic_scope=selected[0].lsoa_code if selected else None,
            total_chunks_indexed=len(self._chunks),
            retrieval_method=RetrievalMethod.HYBRID,
            retrieval_timestamp=datetime.now(timezone.utc),
            retrieval_latency_ms=0.0,
        )

    @staticmethod
    def _derive_coverage_period(chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "n/a"
        months = sorted({chunk.reference_month for chunk in chunks})
        return f"{months[0]} a {months[-1]}"
