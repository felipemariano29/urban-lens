"""Split Markdown documents into RAG-compatible chunks by H2 heading."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd

_MAX_CONTENT_CHARS = 1000
_H2_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)

# Maps doc stem to a short category label stored in the crime_type field.
_DOC_CATEGORY = {
    "data-flow": "data_flow",
    "training-process": "training",
    "implementation-guide": "operations",
    "medallion-governance": "architecture",
    "metadata-contract": "governance",
    "backlog inicial": "backlog",
    "personas": "product",
    "product-vision": "product",
    "how-to-run": "operations",
    "how-to-populate-db": "operations",
    "governance-medallion-delivery-plan": "governance",
}


def _doc_category(file_path: Path) -> str:
    return _DOC_CATEGORY.get(file_path.stem, "documentation")


def chunk_markdown_file(file_path: Path) -> list[dict[str, object]]:
    """Return one chunk dict per H2 section in the Markdown file.

    Chunks follow the same schema as crime_chunks:
      chunk_id, chunk_type, reference_month, lsoa_code, crime_type, title, content
    """
    text = file_path.read_text(encoding="utf-8")
    category = _doc_category(file_path)

    splits = list(_H2_PATTERN.finditer(text))
    if not splits:
        # Treat the entire file as one chunk when no H2 headings exist.
        splits_data = [(file_path.stem, text.strip())]
    else:
        splits_data = []
        for i, match in enumerate(splits):
            heading = match.group(1).strip()
            start = match.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            body = text[start:end].strip()
            splits_data.append((heading, body))

    chunks: list[dict[str, object]] = []
    for heading, body in splits_data:
        # Remove inner markdown syntax for cleaner embeddings.
        content = re.sub(r"[`#*_|]", "", body)
        content = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", content)
        content = re.sub(r"\s{2,}", " ", content).strip()
        content = content[:_MAX_CONTENT_CHARS]

        if not content:
            continue

        title = f"{file_path.stem} > {heading}"
        chunk_id = hashlib.sha256(
            f"documentation:{file_path}:{heading}".encode("utf-8")
        ).hexdigest()

        chunks.append(
            {
                "chunk_id": chunk_id,
                "chunk_type": "documentation",
                "reference_month": "",
                "lsoa_code": "",
                "crime_type": category,
                "title": title[:256],
                "content": content,
            }
        )
    return chunks


def chunk_markdown_files(file_paths: list[Path]) -> pd.DataFrame:
    """Chunk all given Markdown files and return a combined DataFrame."""
    rows: list[dict[str, object]] = []
    for path in file_paths:
        rows.extend(chunk_markdown_file(path))
    return pd.DataFrame(rows)
