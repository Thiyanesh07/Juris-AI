"""Temporal Legal Reasoning & Legal Version Resolution Module (Phase 15).

Provides a clean temporal data model, legal version resolution layer,
and amendment applicability evaluation.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

TemporalStatus = Literal[
    "IN_FORCE",
    "SUPERSEDED",
    "REPEALED",
    "NOT_YET_IN_FORCE",
    "HISTORICAL",
    "UNKNOWN",
]


class LegalVersionInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_id: str
    version_label: str
    effective_from: str | None = None
    effective_to: str | None = None
    status: TemporalStatus = "UNKNOWN"
    amendment_id: str | None = None
    amendment_title: str | None = None
    version_source: str = "corpus_registry"
    temporal_confidence: float = 1.0


class TemporalQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_temporal: bool = False
    target_date: str | None = None
    target_year: int | None = None
    date_range_start: int | None = None
    date_range_end: int | None = None
    temporal_operator: Literal["BEFORE", "AFTER", "SINCE", "UNTIL", "AS_OF", "HISTORICAL", "CURRENT_LAW"] = "CURRENT_LAW"
    referenced_amendment: str | None = None
    temporal_intent: str = "current_law"


# Canonical Indian Legal Milestones Registry (provenance-grounded)
KNOWN_LEGAL_VERSIONS: dict[str, list[LegalVersionInfo]] = {
    "article:constitution_of_india:21": [
        LegalVersionInfo(
            entity_id="article:constitution_of_india:21",
            version_label="Pre-44th Amendment (1950-1979)",
            effective_from="1950-01-26",
            effective_to="1979-06-19",
            status="HISTORICAL",
            amendment_id="amendment:const_amendment_44",
            amendment_title="44th Constitutional Amendment Act, 1978",
            version_source="Constitution of India (Original)",
            temporal_confidence=1.0,
        ),
        LegalVersionInfo(
            entity_id="article:constitution_of_india:21",
            version_label="Post-44th Amendment / Post-Maneka Gandhi (1979-Present)",
            effective_from="1979-06-20",
            effective_to=None,
            status="IN_FORCE",
            amendment_id="amendment:const_amendment_44",
            amendment_title="44th Constitutional Amendment Act, 1978",
            version_source="Constitution of India (As Amended)",
            temporal_confidence=1.0,
        ),
    ],
    "article:constitution_of_india:19": [
        LegalVersionInfo(
            entity_id="article:constitution_of_india:19",
            version_label="Original Article 19 (Including Art 19(1)(f) Right to Property)",
            effective_from="1950-01-26",
            effective_to="1979-06-19",
            status="HISTORICAL",
            amendment_id="amendment:const_amendment_44",
            amendment_title="44th Constitutional Amendment Act, 1978",
            version_source="Constitution of India (Original)",
            temporal_confidence=1.0,
        ),
        LegalVersionInfo(
            entity_id="article:constitution_of_india:19",
            version_label="Post-44th Amendment Article 19 (Property Right Omitted)",
            effective_from="1979-06-20",
            effective_to=None,
            status="IN_FORCE",
            amendment_id="amendment:const_amendment_44",
            amendment_title="44th Constitutional Amendment Act, 1978",
            version_source="Constitution of India (As Amended)",
            temporal_confidence=1.0,
        ),
    ],
    "section:it_act_2000:66a": [
        LegalVersionInfo(
            entity_id="section:it_act_2000:66a",
            version_label="IT (Amendment) Act 2008 Enactment",
            effective_from="2009-10-27",
            effective_to="2015-03-24",
            status="SUPERSEDED",
            amendment_id="act:it_act_2000",
            amendment_title="Information Technology (Amendment) Act, 2008",
            version_source="Information Technology Act, 2000",
            temporal_confidence=1.0,
        ),
        LegalVersionInfo(
            entity_id="section:it_act_2000:66a",
            version_label="Struck Down Unconstitutional (Shreya Singhal v. Union of India)",
            effective_from="2015-03-24",
            effective_to=None,
            status="REPEALED",
            amendment_id="judgment:shreya-singhal",
            amendment_title="Shreya Singhal v. Union of India (2015) 5 SCC 1",
            version_source="Supreme Court Judgment",
            temporal_confidence=1.0,
        ),
    ],
}


def parse_year_from_date_str(date_str: str | None) -> int | None:
    if not date_str:
        return None
    match = re.search(r"\b(19\d{2}|20\d{2})\b", date_str)
    if match:
        return int(match.group(1))
    return None


def resolve_legal_version(
    entity_id: str,
    target_year: int | None = None,
) -> LegalVersionInfo:
    """Determine the applicable legal version of a provision for a target year.

    If target_year is None, returns current in-force version.
    If no temporal metadata exists or date cannot be resolved, returns status UNKNOWN.
    """
    versions = KNOWN_LEGAL_VERSIONS.get(entity_id)
    if not versions:
        return LegalVersionInfo(
            entity_id=entity_id,
            version_label=f"Version for {entity_id}",
            status="UNKNOWN",
            temporal_confidence=0.0,
        )

    if target_year is None:
        # Return current in-force version
        in_force = [v for v in versions if v.status == "IN_FORCE"]
        if in_force:
            return in_force[0]
        return versions[-1]

    # Target year specified
    for ver in versions:
        from_year = parse_year_from_date_str(ver.effective_from) or 1950
        to_year = parse_year_from_date_str(ver.effective_to) or 9999

        if from_year <= target_year <= to_year:
            return ver

    # If before earliest version
    earliest_from = parse_year_from_date_str(versions[0].effective_from) or 1950
    if target_year < earliest_from:
        return LegalVersionInfo(
            entity_id=entity_id,
            version_label="Pre-enactment",
            status="NOT_YET_IN_FORCE",
            effective_to=versions[0].effective_from,
            temporal_confidence=0.9,
        )

    return LegalVersionInfo(
        entity_id=entity_id,
        version_label="Unknown Version",
        status="UNKNOWN",
        temporal_confidence=0.0,
    )
