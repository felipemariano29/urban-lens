"""Deterministic answer composition for intent-specific RAG responses."""

from __future__ import annotations

import re
from dataclasses import dataclass

from urban_lens.rag.contracts import RagContextChunk
from urban_lens.rag.generation import detect_question_language
from urban_lens.rag.query_understanding import detect_query_intent, infer_lsoa_code, infer_reference_month

AREA_MONTH_CATEGORY_PATTERN = re.compile(
    r"recorded\s+(?P<count>\d+)\s+incidents?\s+for\s+crime\s+type\s+(?P<crime_type>[a-z_]+)",
    re.IGNORECASE,
)
MONTH_CATEGORY_PATTERN = re.compile(
    r"crime\s+type\s+(?P<crime_type>[a-z_]+)\s+recorded\s+(?P<count>\d+)\s+incidents?",
    re.IGNORECASE,
)

CRIME_TYPE_LABELS_PT: dict[str, str] = {
    "anti_social_behaviour": "comportamento antissocial",
    "bicycle_theft": "furto de bicicleta",
    "burglary": "furto qualificado",
    "criminal_damage_and_arson": "dano criminal e incendio",
    "drugs": "drogas",
    "other_crime": "outros crimes",
    "other_theft": "outros furtos",
    "possession_of_weapons": "posse de armas",
    "public_order": "ordem publica",
    "robbery": "roubo",
    "shoplifting": "furto em comercio",
    "theft_from_the_person": "furto contra a pessoa",
    "vehicle_crime": "crime veicular",
    "violence_and_sexual_offences": "violencia e delitos sexuais",
}


@dataclass(frozen=True)
class CrimeTypeEvidence:
    evidence_id: str
    lsoa_code: str | None
    reference_month: str | None
    title: str
    crime_type: str
    incident_count: int


def compose_structured_answer(question: str, context: list[RagContextChunk]) -> str | None:
    intent = detect_query_intent(question)
    if intent != "crime_type_listing":
        return None

    language = detect_question_language(question)
    evidence_rows = _extract_crime_type_evidence(context)
    if not evidence_rows:
        return None

    inferred_lsoa = infer_lsoa_code(question)
    inferred_month = infer_reference_month(question)

    if inferred_lsoa:
        evidence_rows = [row for row in evidence_rows if row.lsoa_code == inferred_lsoa]
    if inferred_month:
        evidence_rows = [row for row in evidence_rows if row.reference_month == inferred_month]
    if not evidence_rows:
        return None

    unique_crimes = _dedupe_crime_types(evidence_rows)
    if len(unique_crimes) < 2:
        return None

    if language == "pt":
        return _compose_pt_crime_type_listing(unique_crimes, inferred_lsoa, inferred_month)
    return _compose_en_crime_type_listing(unique_crimes, inferred_lsoa, inferred_month)


def _extract_crime_type_evidence(context: list[RagContextChunk]) -> list[CrimeTypeEvidence]:
    rows: list[CrimeTypeEvidence] = []
    for index, chunk in enumerate(context, start=1):
        chunk_type = str(chunk.metadata.get("chunk_type") or "")
        if chunk_type not in {"area_month_category", "month_category"}:
            continue

        match = AREA_MONTH_CATEGORY_PATTERN.search(chunk.content)
        if not match and chunk_type == "month_category":
            match = MONTH_CATEGORY_PATTERN.search(chunk.content)
        if not match:
            continue

        rows.append(
            CrimeTypeEvidence(
                evidence_id=f"E{index}",
                lsoa_code=_str(chunk.metadata.get("lsoa_code")),
                reference_month=_str(chunk.metadata.get("reference_month")),
                title=chunk.source,
                crime_type=str(match.group("crime_type")),
                incident_count=int(match.group("count")),
            )
        )
    return rows


def _dedupe_crime_types(rows: list[CrimeTypeEvidence]) -> list[CrimeTypeEvidence]:
    best_by_crime: dict[str, CrimeTypeEvidence] = {}
    for row in rows:
        current = best_by_crime.get(row.crime_type)
        if current is None or row.incident_count > current.incident_count:
            best_by_crime[row.crime_type] = row
    return sorted(best_by_crime.values(), key=lambda row: (-row.incident_count, row.crime_type))


def _compose_pt_crime_type_listing(
    rows: list[CrimeTypeEvidence],
    lsoa_code: str | None,
    reference_month: str | None,
) -> str:
    scope_parts = []
    if reference_month:
        scope_parts.append(f"em {reference_month}")
    if lsoa_code:
        scope_parts.append(f"na area {lsoa_code}")
    scope = " ".join(scope_parts).strip()
    scope_text = f" {scope}" if scope else ""

    intro = (
        f"Nas evidencias recuperadas{scope_text}, foram identificados {len(rows)} tipos de crime registrados."
    )
    bullets = [
        f"- {_crime_label_pt(row.crime_type)}: {row.incident_count} incidente(s) [{row.evidence_id}]"
        for row in rows
    ]
    closing = "Os itens acima listam os tipos de crime encontrados no contexto recuperado para essa consulta."
    return "\n".join([intro, *bullets, closing])


def _compose_en_crime_type_listing(
    rows: list[CrimeTypeEvidence],
    lsoa_code: str | None,
    reference_month: str | None,
) -> str:
    scope_parts = []
    if reference_month:
        scope_parts.append(f"in {reference_month}")
    if lsoa_code:
        scope_parts.append(f"for area {lsoa_code}")
    scope = " ".join(scope_parts).strip()
    scope_text = f" {scope}" if scope else ""

    intro = f"The retrieved evidence{scope_text} contains {len(rows)} recorded crime types."
    bullets = [
        f"- {row.crime_type}: {row.incident_count} incident(s) [{row.evidence_id}]"
        for row in rows
    ]
    closing = "The items above list the crime types found in the retrieved context for this query."
    return "\n".join([intro, *bullets, closing])


def _crime_label_pt(value: str) -> str:
    return CRIME_TYPE_LABELS_PT.get(value, value.replace("_", " "))


def _str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None
