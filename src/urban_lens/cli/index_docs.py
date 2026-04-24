"""Index Markdown documentation files into Milvus via Ollama embeddings."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_lens.core.settings import AppConfig
from urban_lens.workflows.doc_indexing import docs_to_vector_index

_DEFAULT_DOCS_DIR = Path(__file__).resolve().parents[4] / "docs"
_DEFAULT_PATTERNS = ["*.md", "**/*.md"]


def _discover_docs(docs_dir: Path, patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for p in sorted(docs_dir.glob(pattern)):
            if p.is_file() and p not in seen:
                paths.append(p)
                seen.add(p)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk and index Markdown docs into Milvus."
    )
    parser.add_argument(
        "--docs-dir",
        default=str(_DEFAULT_DOCS_DIR),
        help="Root directory to discover Markdown files (default: docs/).",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="Explicit list of Markdown file paths. Overrides --docs-dir discovery.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of chunks per Ollama embedding request (default: 32).",
    )
    parser.add_argument("--actor", default="system")
    args = parser.parse_args()

    if args.files:
        doc_paths = [Path(f) for f in args.files]
    else:
        doc_paths = _discover_docs(Path(args.docs_dir), _DEFAULT_PATTERNS)

    if not doc_paths:
        print(f"No Markdown files found in {args.docs_dir}")
        return

    print(f"Indexing {len(doc_paths)} document(s)...")
    result = docs_to_vector_index(
        doc_paths=doc_paths,
        actor=args.actor,
        batch_size=args.batch_size,
        config=AppConfig.from_env(),
    )
    print(result)


if __name__ == "__main__":
    main()
