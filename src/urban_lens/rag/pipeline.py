"""End-to-end RAG pipeline: embedding, retrieval, prompt, generation, citations."""

from __future__ import annotations

from urban_lens.core.settings import AppConfig
from urban_lens.infrastructure.embedder import OllamaEmbedder
from urban_lens.infrastructure.vector_store import MilvusVectorStore
from urban_lens.rag.contracts import EvidenceCitation, RagAnswer, RagQuery, RagResponse
from urban_lens.rag.generation import OllamaGenerator, build_prompt, remove_repeated_question_prefix
from urban_lens.rag.retrieval import build_context_text, filters_to_vector_store, milvus_hits_to_context

FALLBACK_TEXT = (
    "Nao ha evidencia suficiente no contexto recuperado para responder com seguranca. "
    "Refine a pergunta, informe regiao/periodo/tipo de crime, ou indexe dados Gold adicionais."
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
        embeddings = self.embedder.embed([request.query])
        if not embeddings:
            return self._fallback(request, [], "embedding_empty")

        raw_hits = self.vector_store.search(
            query_embedding=embeddings[0],
            top_k=request.top_k,
            filters=filters_to_vector_store(request.filters, request.profile),
        )
        context = milvus_hits_to_context(raw_hits, request.profile)
        enough_context = bool(context) and max(chunk.score for chunk in context) >= request.min_score
        if not enough_context:
            return self._fallback(request, context, "insufficient_retrieved_evidence")

        context_text = build_context_text(context, request.max_context_chars)
        prompt = build_prompt(request.query, context_text, request.profile)
        answer_text = remove_repeated_question_prefix(self.generator.generate(prompt, request.model), request.query)
        if not answer_text:
            return self._fallback(request, context, "empty_generation")

        return RagResponse(
            answer=RagAnswer(text=answer_text, status="answered", model=request.model),
            evidences=_citations_from_context(context),
            context=context,
            profile=request.profile,
        )

    def _fallback(self, request: RagQuery, context, reason: str) -> RagResponse:
        return RagResponse(
            answer=RagAnswer(text=FALLBACK_TEXT, status="insufficient_evidence", model=request.model),
            evidences=_citations_from_context(context),
            context=context,
            profile=request.profile,
            fallback_reason=reason,
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
