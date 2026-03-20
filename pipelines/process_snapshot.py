"""Process a DATA.POLICE.UK snapshot directory, selecting supported street CSV files."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_lens.config import AppConfig
from urban_lens.pipeline.jobs import process_snapshot_directory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process a DATA.POLICE.UK snapshot directory and publish supported street-crime files."
    )
    parser.add_argument("--snapshot-dir", required=True, type=Path)
    parser.add_argument("--source-name", default="data.police.uk")
    parser.add_argument("--actor", default="system")
    args = parser.parse_args()

    result = process_snapshot_directory(
        snapshot_dir=args.snapshot_dir,
        source_name=args.source_name,
        actor=args.actor,
        config=AppConfig.from_env(),
    )
    print(result)


if __name__ == "__main__":
    main()
