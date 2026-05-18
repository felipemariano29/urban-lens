"""End-to-end RAG pipeline: embedding, retrieval, prompt, generation, citations."""

from __future__ import annotations

import time

from urban_lens.core.settings import AppConfig
from urban_lens.infrastructure.embedder import OllamaEmbedder
from urban_lens.infrastructure.vector_store import MilvusVectorStore
from urban_lens.rag.composition import compose_structured_answer
from urban_lens.rag.contracts import AccessProfile, EvidenceCitation, RagAnswer, RagQuery, RagResponse, RagTimings
from urban_lens.rag.generation import OllamaGenerator, build_prompt, detect_question_language, remove_repeated_question_prefix
from urban_lens.rag.query_understanding import detect_query_intent, enrich_filters_from_question
from urban_lens.rag.retrieval import build_context_text, filters_to_vector_store, milvus_hits_to_context

FALLBACK_TEXT_PT = (
    "Nao ha evidencia suficiente no contexto recuperado para responder com seguranca. "
    "Refine a pergunta, informe regiao/periodo/tipo de crime, ou indexe dados Gold adicionais."
)
FALLBACK_TEXT_EN = (
    "There is not enough evidence in the retrieved context to answer safely. "
    "Refine the question, provide region/period/crime type, or index additional Gold data."
)


class RagPipeline:
    def __init__(
        self,
        config: AppConfig,
        embedder: OllamaEmbedder | None = None,
        vector_store: MilvusVectorStore | None = None,
        generator: OllamaGenerator | None = None,
    ) -> None:
        self.config = config
        self.embedder = embedder or OllamaEmbedder(config.ollama_base_url, config.embedding_model)
        self.vector_store = vector_store or MilvusVectorStore(config.milvus_uri)
        self.generator = generator or OllamaGenerator(config.ollama_base_url)

    def run(self, request: RagQuery) -> RagResponse:
        started_at = time.perf_counter()
        generation_ms = 0.0
        effective_filters = enrich_filters_from_question(request)
        intent = detect_query_intent(request.query)

        embedding_started_at = time.perf_counter()
        embeddings = self.embedder.embed([request.query])
        embedding_ms = (time.perf_counter() - embedding_started_at) * 1000
        if not embeddings:
            return self._fallback(
                request,
                [],
                "embedding_empty",
                self._timings(
                    started_at=started_at,
                    embedding_ms=embedding_ms,
                    retrieval_ms=0.0,
                    generation_ms=generation_ms,
                ),
            )

        retrieval_started_at = time.perf_counter()
        raw_hits = self.vector_store.search(
            query_embedding=embeddings[0],
            top_k=request.top_k,
            filters=filters_to_vector_store(effective_filters, request.profile),
        )
        if intent == "crime_type_listing":
            raw_hits = _augment_hits_for_crime_type_listing(
                raw_hits=raw_hits,
                query_embedding=embeddings[0],
                top_k=max(request.top_k, 12),
                effective_filters=effective_filters,
                vector_store=self.vector_store,
            )
        retrieval_ms = (time.perf_counter() - retrieval_started_at) * 1000
        context = milvus_hits_to_context(raw_hits, request.profile)
        enough_context = bool(context) and max(chunk.score for chunk in context) >= request.min_score
        if not enough_context:
            return self._fallback(
                request,
                context,
                "insufficient_retrieved_evidence",
                self._timings(
                    started_at=started_at,
                    embedding_ms=embedding_ms,
                    retrieval_ms=retrieval_ms,
                    generation_ms=generation_ms,
                ),
            )

        structured_answer = compose_structured_answer(request.query, context)
        if structured_answer:
            return RagResponse(
                answer=RagAnswer(text=structured_answer, status="answered", model=request.model),
                evidences=_citations_from_context(context),
                context=context,
                profile=request.profile,
                timings_ms=self._timings(
                    started_at=started_at,
                    embedding_ms=embedding_ms,
                    retrieval_ms=retrieval_ms,
                    generation_ms=generation_ms,
                ),
            )

        context_text = build_context_text(context, request.max_context_chars)
        prompt = build_prompt(request.query, context_text, request.profile)
        generation_started_at = time.perf_counter()
        answer_text = remove_repeated_question_prefix(self.generator.generate(prompt, request.model), request.query)
        generation_ms = (time.perf_counter() - generation_started_at) * 1000
        if not answer_text:
            return self._fallback(
                request,
                context,
                "empty_generation",
                self._timings(
                    started_at=started_at,
                    embedding_ms=embedding_ms,
                    retrieval_ms=retrieval_ms,
                    generation_ms=generation_ms,
                ),
            )

        return RagResponse(
            answer=RagAnswer(text=answer_text, status="answered", model=request.model),
            evidences=_citations_from_context(context),
            context=context,
            profile=request.profile,
            timings_ms=self._timings(
                started_at=started_at,
                embedding_ms=embedding_ms,
                retrieval_ms=retrieval_ms,
                generation_ms=generation_ms,
            ),
        )

    def _fallback(self, request: RagQuery, context, reason: str, timings: RagTimings) -> RagResponse:
        return RagResponse(
            answer=RagAnswer(text=_fallback_text_for(request.query), status="insufficient_evidence", model=request.model),
            evidences=_citations_from_context(context),
            context=context,
            profile=request.profile,
            fallback_reason=reason,
            timings_ms=timings,
        )

    def _timings(
        self,
        *,
        started_at: float,
        embedding_ms: float,
        retrieval_ms: float,
        generation_ms: float,
    ) -> RagTimings:
        return RagTimings(
            embedding_ms=round(embedding_ms, 1),
            retrieval_ms=round(retrieval_ms, 1),
            generation_ms=round(generation_ms, 1),
            total_ms=round((time.perf_counter() - started_at) * 1000, 1),
        )


def _citations_from_context(context) -> list[EvidenceCitation]:
    citations: list[EvidenceCitation] = []
    for index, chunk in enumerate(context, start=1):
        excerpt = chunk.content[:280]
        citations.append(
            EvidenceCitation(
                id=f"E{index}",
                source=chunk.source,
                reference=chunk.reference,
                score=chunk.score,
                timestamp=chunk.timestamp,
                excerpt=excerpt,
                metadata=chunk.metadata,
            )
        )
    return citations


def _fallback_text_for(question: str) -> str:
    return FALLBACK_TEXT_PT if detect_question_language(question) == "pt" else FALLBACK_TEXT_EN


def _augment_hits_for_crime_type_listing(
    *,
    raw_hits: list[dict[str, object]],
    query_embedding: list[float],
    top_k: int,
    effective_filters,
    vector_store: MilvusVectorStore,
) -> list[dict[str, object]]:
    base_filters = filters_to_vector_store(effective_filters, profile=AccessProfile.admin)
    # Prefer category chunks that enumerate crime types directly.
    preferred_chunk_type = "area_month_category" if base_filters.get("lsoa_code") else "month_category"
    targeted_hits = vector_store.search(
        query_embedding=query_embedding,
        top_k=top_k,
        filters={**base_filters, "chunk_type": preferred_chunk_type},
    )
    return _merge_hits_preserving_order(targeted_hits, raw_hits)


def _merge_hits_preserving_order(*hit_groups: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen_chunk_ids: set[str] = set()
    for hits in hit_groups:
        for hit in hits:
            entity = hit.get("entity", hit)
            chunk_id = str(entity.get("chunk_id") or entity.get("id") or "")
            if chunk_id and chunk_id in seen_chunk_ids:
                continue
            if chunk_id:
                seen_chunk_ids.add(chunk_id)
            merged.append(hit)
    return merged
