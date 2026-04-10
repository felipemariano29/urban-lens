"""RAG contracts, schemas, and utility builders for Urban-Lens."""

from urban_lens.rag.contracts import (
    ChunkType,
    FailureType,
    QueryIntent,
    RetrievalMethod,
)
from urban_lens.rag.fallback import apply_low_confidence_warning
from urban_lens.rag.response_builder import ResponseBuilder
from urban_lens.rag.retrieval import InMemoryRetriever, RetrieverInterface
from urban_lens.rag.schemas import (
    ChatResponse,
    CitationEvidence,
    EvidenceSummary,
    FailureResponse,
    FactualResponse,
    RetrievalContext,
    RetrievedChunk,
    SourceReference,
    TemporalComparisonResponse,
)

__all__ = [
    "ChunkType",
    "FailureResponse",
    "FailureType",
    "FactualResponse",
    "QueryIntent",
    "RetrievalMethod",
    "RetrievedChunk",
    "RetrievalContext",
    "SourceReference",
    "CitationEvidence",
    "EvidenceSummary",
    "TemporalComparisonResponse",
    "ChatResponse",
    "apply_low_confidence_warning",
    "RetrieverInterface",
    "InMemoryRetriever",
    "ResponseBuilder",
]
