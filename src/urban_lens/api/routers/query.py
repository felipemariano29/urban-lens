from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from urban_lens.api.core.auth import UserProfile
from urban_lens.api.dependencies import require_roles
from urban_lens.api.schemas import ChatQueryRequest, ChatQueryResponse, QueryRequest, QueryResponse, QueryResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Query"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Semantic crime data search",
    description=(
        "Performs a semantic similarity search over indexed crime evidence chunks using "
        "the Milvus vector store. Accessible to all authenticated roles."
    ),
    responses={
        200: {"description": "Ranked list of matching evidence chunks."},
        401: {"description": "Missing or invalid authentication credentials."},
        502: {"description": "RAG backend (Milvus/Ollama) unavailable."},
    },
)
def query(
    body: QueryRequest,
    _profile: UserProfile = Depends(require_roles("viewer", "operator", "admin", "internal_service")),
) -> QueryResponse:
    from urban_lens.api.services import rag_service

    try:
        hits = rag_service.run_query(
            query=body.query,
            top_k=body.top_k,
            filters=body.filters,
        )
    except Exception as exc:
        logger.error("RAG service error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="RAG backend returned an error. Please try again later.",
        )

    return QueryResponse(results=[QueryResult(**h) for h in hits])


@router.post(
    "/chat/query",
    response_model=ChatQueryResponse,
    summary="Governed RAG chat answer with evidence citations",
    description=(
        "Runs the complete local RAG pipeline: query embedding, Milvus retrieval, "
        "role-filtered context assembly, Ollama generation, and evidence citation return."
    ),
    responses={
        200: {"description": "Generated answer with cited evidence, or an insufficient-evidence fallback."},
        401: {"description": "Missing or invalid authentication credentials."},
        403: {"description": "Authenticated profile is not allowed to use chat."},
        502: {"description": "RAG backend (Milvus/Ollama) unavailable."},
    },
)
def chat_query(
    body: ChatQueryRequest,
    profile: UserProfile = Depends(
        require_roles("viewer", "operator", "intel_user", "developer", "admin", "internal_service")
    ),
) -> ChatQueryResponse:
    from urban_lens.api.services import rag_service

    try:
        result = rag_service.run_chat_query(
            query=body.query,
            role=profile.role,
            top_k=body.top_k,
            filters=body.filters,
            model=body.model,
        )
    except Exception as exc:
        logger.error("RAG chat service error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="RAG backend returned an error. Please try again later.",
        )

    return ChatQueryResponse(**result.model_dump())
