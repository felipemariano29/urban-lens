"""Hashing helpers shared across pipeline workflows."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def dataframe_hash(dataframe: pd.DataFrame) -> str:
    normalized = dataframe.copy()
    normalized = normalized.sort_index(axis=1)
    normalized = normalized.fillna("<NA>")
    payload = normalized.to_json(orient="records", date_format="iso")
    return sha256_text(payload)
