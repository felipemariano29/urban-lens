"""Milvus-backed vector storage for RAG evidence chunks."""

from __future__ import annotations

from pymilvus import DataType, MilvusClient

COLLECTION_NAME = "crime_chunks"
EMBEDDING_DIM = 768
FILTERABLE_FIELDS = {"chunk_type", "reference_month", "lsoa_code", "crime_type", "dataset_version_id"}


def _escape_filter_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class MilvusVectorStore:
    def __init__(self, uri: str) -> None:
        self.uri = uri
        self._client: MilvusClient | None = None

    def _get_client(self) -> MilvusClient:
        if self._client is None:
            self._client = MilvusClient(uri=self.uri)
        return self._client

    def ensure_collection(self) -> None:
        """Create the crime_chunks collection if it does not already exist."""
        client = self._get_client()
        if client.has_collection(COLLECTION_NAME):
            return
        schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("chunk_id", DataType.VARCHAR, max_length=64, is_primary=True)
        schema.add_field("chunk_type", DataType.VARCHAR, max_length=32)
        schema.add_field("reference_month", DataType.VARCHAR, max_length=7)
        schema.add_field("lsoa_code", DataType.VARCHAR, max_length=16)
        schema.add_field("crime_type", DataType.VARCHAR, max_length=64)
        schema.add_field("title", DataType.VARCHAR, max_length=512)
        schema.add_field("content", DataType.VARCHAR, max_length=65535)
        schema.add_field("dataset_version_id", DataType.VARCHAR, max_length=36)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            metric_type="COSINE",
            index_type="HNSW",
            params={"M": 16, "efConstruction": 200},
        )
        client.create_collection(
            collection_name=COLLECTION_NAME,
            schema=schema,
            index_params=index_params,
        )

    def upsert_chunks(self, records: list[dict[str, object]]) -> int:
        """Upsert records into the collection. Returns the number of records written."""
        client = self._get_client()
        result = client.upsert(collection_name=COLLECTION_NAME, data=records)
        return result.get("upsert_count", len(records))

    def count(self) -> int:
        client = self._get_client()
        stats = client.get_collection_stats(COLLECTION_NAME)
        return int(stats.get("row_count", 0))

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, str] | None = None,
    ) -> list[dict[str, object]]:
        """Return the top-k most similar chunks to the query embedding."""
        client = self._get_client()
        filter_expr = ""
        if filters:
            clauses = [
                f'{key} == "{_escape_filter_value(value)}"'
                for key, value in filters.items()
                if key in FILTERABLE_FIELDS and value
            ]
            if clauses:
                filter_expr = " && ".join(clauses)
        results = client.search(
            collection_name=COLLECTION_NAME,
            data=[query_embedding],
            limit=top_k,
            filter=filter_expr or "",
            output_fields=[
                "chunk_id",
                "chunk_type",
                "reference_month",
                "lsoa_code",
                "crime_type",
                "title",
                "content",
                "dataset_version_id",
            ],
        )
        return list(results[0]) if results else []
