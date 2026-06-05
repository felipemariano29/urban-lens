"""Publish Silver artifacts into Gold analytics, RAG, and ML datasets."""

from __future__ import annotations

import argparse

from urban_lens.core.settings import AppConfig
from urban_lens.workflows.gold import silver_to_gold


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Gold datasets from a Silver parquet object.")
    parser.add_argument("--silver-object-key", required=True)
    parser.add_argument("--silver-dataset-version-id", required=True)
    parser.add_argument("--actor", default="system")
    args = parser.parse_args()

    result = silver_to_gold(
        silver_object_key=args.silver_object_key,
        silver_dataset_version_id=args.silver_dataset_version_id,
        actor=args.actor,
        config=AppConfig.from_env(),
    )
    print(result)


if __name__ == "__main__":
    main()
