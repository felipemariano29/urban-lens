"""Manual CSV ingestion into the Bronze layer."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_lens.core.settings import AppConfig
from urban_lens.workflows.ingestion import ingest_to_bronze


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a local CSV file into Bronze and register metadata.")
    parser.add_argument("--csv-path", required=True, type=Path)
    parser.add_argument("--source-name", default="data.police.uk")
    parser.add_argument("--force-name", required=True)
    parser.add_argument("--actor", default="system")
    args = parser.parse_args()

    result = ingest_to_bronze(
        csv_path=args.csv_path,
        source_name=args.source_name,
        force_name=args.force_name,
        actor=args.actor,
        config=AppConfig.from_env(),
    )
    print(result)


if __name__ == "__main__":
    main()
