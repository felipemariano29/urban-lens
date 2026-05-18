"""Standardize Bronze CSV data into Silver parquet."""

from __future__ import annotations

import argparse

from urban_lens.core.settings import AppConfig
from urban_lens.workflows.silver import bronze_to_silver


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform Bronze CSV objects into Silver parquet.")
    parser.add_argument("--bronze-object-key", required=True)
    parser.add_argument("--bronze-dataset-version-id", required=True)
    parser.add_argument("--actor", default="system")
    args = parser.parse_args()

    result = bronze_to_silver(
        bronze_object_key=args.bronze_object_key,
        bronze_dataset_version_id=args.bronze_dataset_version_id,
        actor=args.actor,
        config=AppConfig.from_env(),
    )
    print(result)


if __name__ == "__main__":
    main()
