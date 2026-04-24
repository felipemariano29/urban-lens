"""Index Gold RAG crime_chunks into Milvus via Ollama embeddings."""

from __future__ import annotations

import argparse

from urban_lens.core.settings import AppConfig
from urban_lens.workflows.embeddings import gold_to_vector_index


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate embeddings from Gold RAG chunks and index into Milvus."
    )
    parser.add_argument(
        "--rag-object-key",
        required=True,
        help="MinIO object key for the crime_chunks Parquet file.",
    )
    parser.add_argument(
        "--rag-dataset-version-id",
        required=True,
        help="Governance dataset_version_id for the RAG chunk file.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of chunks per Ollama embedding request (default: 32).",
    )
    parser.add_argument("--actor", default="system")
    args = parser.parse_args()

    result = gold_to_vector_index(
        rag_object_key=args.rag_object_key,
        rag_dataset_version_id=args.rag_dataset_version_id,
        actor=args.actor,
        batch_size=args.batch_size,
        config=AppConfig.from_env(),
    )
    print(result)


if __name__ == "__main__":
    main()
