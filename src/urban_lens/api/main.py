from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI

from urban_lens.api.routers import metadata
from urban_lens.rag.response_builder import ResponseBuilder
from urban_lens.rag.retrieval import InMemoryRetriever
from urban_lens.rag.schemas import RetrievedChunk, SourceReference

from .schemas import ChatQueryRequest, ChatQueryResponse


app = FastAPI(
    title="Urban Lens Internal API",
    description=(
        "Internal API for structured MLflow metadata queries and governance. "
        "All endpoints require a valid `x-profile-name` header for RBAC enforcement."
    ),
    version="0.1.0",
)

app.include_router(metadata.router)


@app.get("/health", tags=["System"], summary="Liveness probe")
def health_check() -> dict[str, str]:
    return {"status": "online"}


@app.post("/api/v1/chat/query", response_model=ChatQueryResponse, tags=["RAG"])
def chat_query(payload: ChatQueryRequest) -> ChatQueryResponse:
    sample_chunks = [
        RetrievedChunk(
            chunk_id="chunk-westminster-2024-01-burglary",
            content="In 2024-01, Westminster recorded 5 burglary incidents.",
            relevance_score=0.41,
            crime_type="burglary",
            reference_month="2024-01",
            dataset_version_id=uuid4(),
            source_path="s3://urban-lens/gold/rag/crime_chunks/year=2024/month=01/part-000.parquet",
            lsoa_code="E01004736",
        ),
        RetrievedChunk(
            chunk_id="chunk-westminster-2024-02-burglary",
            content="In 2024-02, Westminster recorded 7 burglary incidents.",
            relevance_score=0.38,
            crime_type="burglary",
            reference_month="2024-02",
            dataset_version_id=uuid4(),
            source_path="s3://urban-lens/gold/rag/crime_chunks/year=2024/month=02/part-000.parquet",
            lsoa_code="E01004736",
        ),
    ]

    retriever = InMemoryRetriever(sample_chunks)
    retrieval_context = retriever.retrieve(payload.question, top_k=payload.top_k)

    source_references = [
        SourceReference(
            dataset_version_id=uuid4(),
            logical_name="crime_chunks",
            version="2024-02",
            gold_product="gold/rag/crime_chunks",
            reference_month="2024-02",
            row_count=2,
            content_hash="mock-hash-2024-02",
            valid_from=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
    ]

    response = ResponseBuilder().build_factual_response(
        query=payload.question,
        retrieval_context=retrieval_context,
        generated_answer=(
            "Os dados recuperados sugerem aumento de burglary entre 2024-01 e 2024-02 em Westminster."
        ),
        model_used="ollama-mistral-7b",
        source_references=source_references,
    )

    return ChatQueryResponse(result=response)
