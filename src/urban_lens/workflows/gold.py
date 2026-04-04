"""Gold publication workflow."""

from __future__ import annotations

from urban_lens.core.hashing import dataframe_hash
from urban_lens.core.settings import AppConfig
from urban_lens.forecasting.features import build_ml_datasets
from urban_lens.governance.contracts import (
    GOLD_ANALYTICS_AREA_MONTH,
    GOLD_ANALYTICS_AREA_MONTH_CATEGORY,
    GOLD_ANALYTICS_MONTH_CATEGORY,
    GOLD_LAYER,
    GOLD_ML_SCORING,
    GOLD_ML_TRAINING,
    GOLD_RAG_PRODUCT,
    AuditEventPayload,
    DatasetVersionPayload,
    PipelineRunPayload,
)
from urban_lens.governance.store import MetadataStore
from urban_lens.infrastructure.object_store import MinIOStorage
from urban_lens.sources.police_uk import (
    build_gold_analytics_by_area_month,
    build_gold_analytics_by_area_month_category,
    build_gold_analytics_by_month_category,
    build_rag_evidence_records,
)


def silver_to_gold(
    silver_object_key: str,
    silver_dataset_version_id: str,
    actor: str,
    config: AppConfig,
    storage: MinIOStorage | None = None,
    metadata_store: MetadataStore | None = None,
) -> dict[str, str]:
    storage = storage or MinIOStorage(config)
    metadata_store = metadata_store or MetadataStore(config.postgres_dsn)

    pipeline_run_id = metadata_store.register_pipeline_run(
        PipelineRunPayload(
            pipeline_name="silver_to_gold",
            run_type="manual",
            status="running",
            triggered_by=actor,
            input_versions=[silver_dataset_version_id],
        )
    )

    silver_frame = storage.read_parquet(silver_object_key)
    area_month_category = build_gold_analytics_by_area_month_category(silver_frame)
    area_month = build_gold_analytics_by_area_month(area_month_category)
    month_category = build_gold_analytics_by_month_category(area_month_category)
    rag_records = build_rag_evidence_records(area_month, area_month_category, month_category)
    training_set, scoring_set = build_ml_datasets(area_month_category)

    reference_month = str(area_month_category["reference_month"].max())
    year = reference_month[:4]
    month = reference_month[5:7]
    artifact_map = {
        GOLD_ANALYTICS_AREA_MONTH_CATEGORY: (
            area_month_category,
            f"{GOLD_ANALYTICS_AREA_MONTH_CATEGORY}/year={year}/month={month}/part-000.parquet",
            "crime_metrics_area_month_category",
        ),
        GOLD_ANALYTICS_AREA_MONTH: (
            area_month,
            f"{GOLD_ANALYTICS_AREA_MONTH}/year={year}/month={month}/part-000.parquet",
            "crime_metrics_area_month",
        ),
        GOLD_ANALYTICS_MONTH_CATEGORY: (
            month_category,
            f"{GOLD_ANALYTICS_MONTH_CATEGORY}/year={year}/month={month}/part-000.parquet",
            "crime_metrics_month_category",
        ),
        GOLD_RAG_PRODUCT: (
            rag_records,
            f"{GOLD_RAG_PRODUCT}/year={year}/month={month}/part-000.parquet",
            "crime_chunks",
        ),
        GOLD_ML_TRAINING: (
            training_set,
            f"{GOLD_ML_TRAINING}/year={year}/month={month}/part-000.parquet",
            "forecast_training_set",
        ),
        GOLD_ML_SCORING: (
            scoring_set,
            f"{GOLD_ML_SCORING}/year={year}/month={month}/part-000.parquet",
            "forecast_scoring_set",
        ),
    }

    outputs: dict[str, str] = {"pipeline_run_id": pipeline_run_id}
    output_ids: list[str] = []
    for gold_product, (frame, object_key, logical_name) in artifact_map.items():
        storage.write_parquet(frame, object_key)
        dataset_version_id = metadata_store.register_dataset_version(
            DatasetVersionPayload(
                source_name="data.police.uk",
                layer=GOLD_LAYER,
                logical_name=logical_name,
                version=reference_month,
                schema_version="1.0.0",
                object_path=object_key,
                row_count=len(frame),
                content_hash=dataframe_hash(frame),
                valid_from=reference_month,
                metadata_json={"gold_product": gold_product, "pipeline_run_id": pipeline_run_id},
            )
        )
        metadata_store.register_lineage(
            upstream_dataset_version_id=silver_dataset_version_id,
            downstream_dataset_version_id=dataset_version_id,
            transformation_name=f"silver_to_{logical_name}",
            pipeline_run_id=pipeline_run_id,
        )
        output_ids.append(dataset_version_id)
        outputs[f"{logical_name}_dataset_version_id"] = dataset_version_id
        outputs[f"{logical_name}_object_key"] = object_key

    metadata_store.register_audit_event(
        AuditEventPayload(
            event_type="gold_published",
            actor=actor,
            object_type="pipeline_run",
            object_id=pipeline_run_id,
            details_json={"reference_month": reference_month, "output_count": len(output_ids)},
        )
    )
    metadata_store.finalize_pipeline_run(pipeline_run_id, "completed", output_ids)
    return outputs
