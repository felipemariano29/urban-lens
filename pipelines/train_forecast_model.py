"""Train and register the baseline forecast model from Gold ML datasets."""

from __future__ import annotations

import argparse

from urban_lens.config import AppConfig
from urban_lens.pipeline.jobs import train_and_register_forecast_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the baseline forecast model and publish predictions.")
    parser.add_argument("--training-object-key", required=True)
    parser.add_argument("--training-dataset-version-id", required=True)
    parser.add_argument("--scoring-object-key", required=True)
    parser.add_argument("--scoring-dataset-version-id", required=True)
    parser.add_argument("--actor", default="system")
    args = parser.parse_args()

    result = train_and_register_forecast_model(
        training_object_key=args.training_object_key,
        training_dataset_version_id=args.training_dataset_version_id,
        scoring_object_key=args.scoring_object_key,
        scoring_dataset_version_id=args.scoring_dataset_version_id,
        actor=args.actor,
        config=AppConfig.from_env(),
    )
    print(result)


if __name__ == "__main__":
    main()

