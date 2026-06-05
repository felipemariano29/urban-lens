"""Seed helpers for governance reference data."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from urban_lens.governance.models import AccessPolicy
from urban_lens.infrastructure.db import SessionLocal


def populate_database() -> None:
    db = SessionLocal()
    try:
        existing_profile = db.query(AccessPolicy).filter(AccessPolicy.profile_name == "external_auditor").first()
        if existing_profile:
            return

        new_profile = AccessPolicy(
            id=uuid.uuid4(),
            profile_name="external_auditor",
            layer_scope="gold",
            dataset_scope="*",
            allowed_actions=["read", "audit"],
            metadata_visibility={"dataset_version": True, "pipeline_run": True, "model_version": False},
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_profile)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_database()
