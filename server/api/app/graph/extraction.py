"""Conservative, deterministic legal entity and relation extraction.

This module extracts explicit legal entities (Articles, Sections, Acts, Constitution, Courts,
Amendments, Judgments, Doctrines, Persons, Concepts) and their relations (DEFINES,
INTERPRETS, AMENDS, REFERENCES, OVERRULES, BELONGS_TO) with full provenance metadata.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

_ARTICLE = re.compile(r"\b(?:Article|Art\.)\s+(\d+[A-Z]?)\b", re.IGNORECASE)
_SECTION = re.compile(r"\b(?:Section|Sec\.|S\.)\s+(\d+[A-Z]?)\b", re.IGNORECASE)

_ACT_STRICT = re.compile(r"\b([A-Z][A-Za-z\s']{2,60}\s+(?:Act|Code)(?:,\s*\d{4})?)\b")

_ACT_BLACKLIST = frozenset(
    {
        "the act",
        "this act",
        "principal act",
        "a central act",
        "objects and reasons",
        "statement of objects",
        "amending act",
        "said act",
        "other act",
        "any act",
        "an act",
        "the constitution",
        "this constitution",
        "high court act",
        "supreme court act",
        "court act",
        "parliament act",
        "state act",
        "central act",
        "preamble to the act",
    }
)

_CANONICAL_ACTS: list[tuple[str, str, list[str]]] = [
    (
        "The Code of Criminal Procedure, 1973",
        "act:crpc_1973",
        [r"\bThe Code of Criminal Procedure, 1973\b", r"\bCode of Criminal Procedure\b", r"\bCr\.?P\.?C\.?\b"],
    ),
    (
        "The Indian Penal Code, 1860",
        "act:ipc_1860",
        [r"\bThe Indian Penal Code, 1860\b", r"\bIndian Penal Code\b", r"\bI\.?P\.?C\.?\b"],
    ),
    (
        "The Indian Evidence Act, 1872",
        "act:iea_1872",
        [r"\bThe Indian Evidence Act, 1872\b", r"\bIndian Evidence Act\b", r"\bEvidence Act\b"],
    ),
    (
        "Information Technology Act, 2000",
        "act:it_act_2000",
        [r"\bInformation Technology Act, 2000\b", r"\bInformation Technology Act\b", r"\bI\.?T\.?\s+Act\b"],
    ),
    (
        "Right to Information Act, 2005",
        "act:rti_act_2005",
        [r"\bRight to Information Act, 2005\b", r"\bRight to Information Act\b", r"\bR\.?T\.?I\.?\s+Act\b"],
    ),
    (
        "The Protection of Human Rights Act, 1993",
        "act:phra_1993",
        [r"\bThe Protection of Human Rights Act, 1993\b", r"\bProtection of Human Rights Act\b"],
    ),
    (
        "The Representation of the People Act, 1951",
        "act:rpa_1951",
        [r"\bThe Representation of the People Act, 1951\b", r"\bRepresentation of the People Act\b"],
    ),
    (
        "Bharatiya Nyaya Sanhita, 2023",
        "act:bns_2023",
        [r"\bBharatiya Nyaya Sanhita, 2023\b", r"\bBharatiya Nyaya Sanhita\b"],
    ),
    (
        "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "act:bnss_2023",
        [r"\bBharatiya Nagarik Suraksha Sanhita, 2023\b", r"\bBharatiya Nagarik Suraksha Sanhita\b"],
    ),
    (
        "Bharatiya Sakshya Adhiniyam, 2023",
        "act:bsa_2023",
        [r"\bBharatiya Sakshya Adhiniyam, 2023\b", r"\bBharatiya Sakshya Adhiniyam\b"],
    ),
    (
        "Passports Act, 1967",
        "act:passports_act_1967",
        [r"\bPassports Act, 1967\b", r"\bPassports Act\b"],
    ),
    (
        "Preventive Detention Act, 1950",
        "act:preventive_detention_act_1950",
        [r"\bPreventive Detention Act, 1950\b", r"\bPreventive Detention Act\b"],
    ),
    (
        "Aadhaar Act, 2016",
        "act:aadhaar_act_2016",
        [r"\bAadhaar (?:Targeted Delivery of Financial and Other Subsidies, Benefits and Services )?Act, 2016\b", r"\bAadhaar Act\b"],
    ),
]

_COURT_SC = re.compile(r"\bSupreme Court(?:\s+of\s+India)?\b", re.IGNORECASE)
_COURT_HC = re.compile(r"\b([A-Z][a-z]+)\s+High Court\b")
_DEFINES = re.compile(
    r"\bdefines?\s+(?:[‘\"']([^‘\"']+)[’\"']|"
    r"([A-Za-z][A-Za-z-]+(?:\s+(?!for\b|under\b|within\b)[A-Za-z][A-Za-z-]+)*))"
    r"(?=[.;,:\"']|\s|$)",
    re.IGNORECASE,
)
_AMENDMENT = re.compile(
    r"\b(\d+)(?:st|nd|rd|th)?\s+(?:Constitutional\s+)?Amendment(?:\s+Act(?:,\s*\d{4})?)?\b|"
    r"\bConstitution\s*\(([^)]+)\)\s*Act\b",
    re.IGNORECASE,
)
_DOCTRINE = re.compile(
    r"\b(Basic Structure(?: Doctrine)?|Due Process(?: of Law)?|Procedure Established by Law|"
    r"Pith and Substance|Doctrine of Severability|Doctrine of Eclipse|Colorable Legislation|"
    r"Public Trust Doctrine)\b",
    re.IGNORECASE,
)
_JUDGMENT_NAMES = re.compile(
    r"\b(Kesavananda Bharati|Indira (?:Nehru )?Gandhi|Minerva Mills|I\.?R\.? Coelho|"
    r"L\.? Chandra Kumar|E\.?P\.? Royappa|Maneka Gandhi|Shayara Bano|Romesh Thappar|"
    r"Bennett Coleman|Shreya Singhal|A\.?K\.? Gopalan|Puttaswamy|Common Cause|"
    r"S\.?R\.? Bommai|Vishaka|NALSA|Navtej Singh Johar)\b",
    re.IGNORECASE,
)
_PERSON_JUDGE = re.compile(
    r"\b([A-Z][a-zA-Z.]+(?:\s+[A-Z][a-zA-Z.]+)*\s+(?:J\.|C\.?J\.?))\b"
)

_LEGAL_ENTITY_LABELS = frozenset(
    {
        "Article",
        "Section",
        "Act",
        "Court",
        "Concept",
        "Amendment",
        "Judgment",
        "Rule",
        "Regulation",
        "Person",
        "Organization",
        "Doctrine",
        "Constitution",
    }
)


@dataclass(frozen=True)
class Entity:
    id: str
    label: str
    name: str
    confidence: float = 1.0


@dataclass(frozen=True)
class Relation:
    source_id: str
    target_id: str
    type: str
    confidence: float = 1.0
    extraction_method: str = "deterministic_rule"
    page: int | None = None
    evidence_text: str = ""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _instrument_slug(document_title: str, document_id: str) -> str:
    return _slug(document_title) or _slug(document_id) or "unknown-instrument"


def _court_id(raw_name: str) -> str | None:
    """Return a stable court id, or None when the mention is too ambiguous."""
    cleaned = " ".join(raw_name.split())
    lowered = cleaned.lower()
    if lowered == "high court":
        return None
    if lowered.startswith("supreme court"):
        return "court:supreme-court-of-india"
    if lowered.endswith("high court"):
        return f"court:{_slug(cleaned)}"
    return None


def _court_display_name(raw_name: str) -> str:
    cleaned = " ".join(raw_name.split())
    if cleaned.lower().startswith("supreme court"):
        return "Supreme Court of India"
    return cleaned


def extract_entities(text: str, document_title: str = "", document_id: str = "") -> list[Entity]:
    """Extract explicit articles, sections, constitution, acts, courts, amendments, judgments, doctrines, judges, and definitions."""
    entities: dict[str, Entity] = {}
    instrument = _instrument_slug(document_title, document_id)

    # 1. Constitution
    if re.search(r"\bConstitution\s+of\s+India\b|\bthe\s+Constitution\b", text, re.IGNORECASE) or document_id == "constitution_of_india":
        entities["constitution:india"] = Entity(
            id="constitution:india",
            label="Constitution",
            name="Constitution of India",
            confidence=1.0,
        )

    # 2. Articles
    for number in _ARTICLE.findall(text):
        canonical = number.upper()
        entity = Entity(
            f"article:constitution_of_india:{canonical.lower()}",
            "Article",
            f"Article {canonical}",
        )
        entities[entity.id] = entity

    # 3. Sections
    for number in _SECTION.findall(text):
        canonical = number.upper()
        sec_inst = "constitution_of_india" if "constitution" in instrument else instrument
        entity = Entity(
            f"section:{sec_inst}:{canonical.lower()}",
            "Section",
            f"Section {canonical}",
        )
        entities[entity.id] = entity

    # 4. Acts (Canonical Acts first, then strict regex with blacklist)
    for title, act_id, patterns in _CANONICAL_ACTS:
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                entities[act_id] = Entity(act_id, "Act", title)
                break

    for match in _ACT_STRICT.finditer(text):
        name = match.group(1)
        cleaned = " ".join(name.split())
        lowered = cleaned.lower()
        if lowered in _ACT_BLACKLIST or any(b in lowered for b in ["the act", "this act", "preamble", "objects and reasons"]):
            continue
        if lowered.startswith("constitution"):
            continue
        act_id = f"act:{_slug(cleaned)}"
        if act_id not in entities:
            entities[act_id] = Entity(act_id, "Act", cleaned)

    # 5. Courts
    for match in _COURT_SC.finditer(text):
        c_id = _court_id(match.group(0))
        if c_id is not None:
            display = _court_display_name(match.group(0))
            entities[c_id] = Entity(c_id, "Court", display)
    for match in _COURT_HC.finditer(text):
        prefix = match.group(1).strip()
        if not prefix or prefix.lower() in ("high", "the", "a", "an", "this", "hon'ble"):
            continue
        full_name = f"{prefix} High Court"
        c_id = _court_id(full_name)
        if c_id is not None:
            entities[c_id] = Entity(c_id, "Court", full_name)

    # 6. Concepts / Definitions
    for match in _DEFINES.finditer(text):
        raw = match.group(1) or match.group(2) or ""
        cleaned = " ".join(raw.split()).strip(" .;:")
        if cleaned and len(cleaned) > 2 and cleaned.lower() not in _ACT_BLACKLIST:
            entity = Entity(
                f"concept:{instrument}:{_slug(cleaned)}",
                "Concept",
                cleaned,
                0.9,
            )
            entities[entity.id] = entity

    # 7. Amendments
    for match in _AMENDMENT.finditer(text):
        num = match.group(1) or match.group(2) or match.group(0)
        num_clean = re.sub(r"\D+", "", str(num))
        if num_clean:
            name = f"{num_clean}th Constitutional Amendment"
            entity = Entity(f"amendment:const_amendment_{num_clean}", "Amendment", name)
            entities[entity.id] = entity

    # 8. Doctrines
    for match in _DOCTRINE.finditer(text):
        doc_name = " ".join(match.group(0).split())
        entity = Entity(f"doctrine:{_slug(doc_name)}", "Doctrine", doc_name.title())
        entities[entity.id] = entity

    # 9. Judgments
    for match in _JUDGMENT_NAMES.finditer(text):
        case_name = " ".join(match.group(0).split())
        entity = Entity(f"judgment:{_slug(case_name)}", "Judgment", case_name)
        entities[entity.id] = entity

    # 10. Judges / Persons
    for match in _PERSON_JUDGE.finditer(text):
        judge_name = " ".join(match.group(0).split())
        entity = Entity(f"person:{_slug(judge_name)}", "Person", judge_name)
        entities[entity.id] = entity

    return list(entities.values())


def _provision_positions(text: str, provisions: list[Entity]) -> list[tuple[int, Entity]]:
    positions: list[tuple[int, Entity]] = []
    lowered = text.lower()
    for provision in provisions:
        idx = lowered.find(provision.name.lower())
        if idx >= 0:
            positions.append((idx, provision))
    positions.sort(key=lambda item: item[0])
    return positions


def _concept_for_definiendum(
    definiendum: str,
    instrument: str,
    concepts: list[Entity],
) -> Entity | None:
    slug = _slug(definiendum)
    concept_id = f"concept:{instrument}:{slug}"
    for concept in concepts:
        if concept.id == concept_id:
            return concept
    return None


def extract_relations(
    text: str,
    entities: list[Entity],
    document_title: str = "",
    document_id: str = "",
    document_type: str = "",
    page_number: int | None = None,
) -> list[Relation]:
    """Extract BELONGS_TO, DEFINES, INTERPRETS, AMENDS, REFERENCES, and OVERRULES relations."""
    relations: list[Relation] = []
    seen: set[tuple[str, str, str]] = set()
    instrument = _instrument_slug(document_title, document_id)

    articles = [e for e in entities if e.label == "Article"]
    sections = [e for e in entities if e.label == "Section"]
    provisions = articles + sections
    concepts = [e for e in entities if e.label == "Concept"]
    judgments = [e for e in entities if e.label == "Judgment"]
    amendments = [e for e in entities if e.label == "Amendment"]
    acts = [e for e in entities if e.label == "Act"]
    doctrines = [e for e in entities if e.label == "Doctrine"]

    # 1. BELONGS_TO relations
    # Articles belong to Constitution of India
    for art in articles:
        key = (art.id, "constitution:india", "BELONGS_TO")
        if key not in seen:
            seen.add(key)
            relations.append(
                Relation(
                    source_id=art.id,
                    target_id="constitution:india",
                    type="BELONGS_TO",
                    confidence=1.0,
                    page=page_number,
                    evidence_text=f"{art.name} belongs to Constitution of India",
                )
            )

    # Sections belong to parent Act
    if document_type.lower() == "act" or "act" in document_id.lower() or "sanhita" in document_id.lower() or "adhiniyam" in document_id.lower() or "code" in document_id.lower():
        act_target_id = f"act:{_slug(document_id)}"
        for sec in sections:
            key = (sec.id, act_target_id, "BELONGS_TO")
            if key not in seen:
                seen.add(key)
                relations.append(
                    Relation(
                        source_id=sec.id,
                        target_id=act_target_id,
                        type="BELONGS_TO",
                        confidence=1.0,
                        page=page_number,
                        evidence_text=f"{sec.name} belongs to {document_title}",
                    )
                )

    # 2. DEFINES: provision -> concept
    if provisions and concepts:
        positions = _provision_positions(text, provisions)
        if positions:
            for match in _DEFINES.finditer(text):
                def_pos = match.start()
                raw = match.group(1) or match.group(2) or ""
                concept = _concept_for_definiendum(raw, instrument, concepts)
                if concept is None:
                    continue
                preceding = [provision for pos, provision in positions if pos < def_pos]
                if not preceding:
                    continue
                provision = preceding[-1]
                key = (provision.id, concept.id, "DEFINES")
                if key not in seen:
                    seen.add(key)
                    relations.append(
                        Relation(
                            source_id=provision.id,
                            target_id=concept.id,
                            type="DEFINES",
                            confidence=0.9,
                            page=page_number,
                            evidence_text=text[max(0, def_pos - 40) : min(len(text), def_pos + 80)],
                        )
                    )

    # 3. INTERPRETS & REFERENCES (When document is a judgment)
    is_judgment = (
        document_type.lower() == "judgment"
        or bool(_JUDGMENT_NAMES.search(document_title or document_id))
        or "v." in document_title.lower()
        or "vs." in document_title.lower()
    )

    if is_judgment:
        source_judg_id = f"judgment:{_slug(document_title or document_id)}"

        # Judgment INTERPRETS / REFERENCES Articles and Sections
        for prov in provisions:
            if re.search(r"\b(?:held|interpreted|struck down|upheld|construed|read down|expanded|validity of|scope of)\b", text, re.I):
                key = (source_judg_id, prov.id, "INTERPRETS")
                if key not in seen:
                    seen.add(key)
                    relations.append(
                        Relation(
                            source_id=source_judg_id,
                            target_id=prov.id,
                            type="INTERPRETS",
                            confidence=0.90,
                            page=page_number,
                            evidence_text=f"{document_title} interprets {prov.name}",
                        )
                    )
            elif re.search(r"\b(?:referred to|cited|relied upon|under Section|under Article|pursuant to)\b", text, re.I):
                key = (source_judg_id, prov.id, "REFERENCES")
                if key not in seen:
                    seen.add(key)
                    relations.append(
                        Relation(
                            source_id=source_judg_id,
                            target_id=prov.id,
                            type="REFERENCES",
                            confidence=0.85,
                            page=page_number,
                            evidence_text=f"{document_title} references {prov.name}",
                        )
                    )

        # Judgment INTERPRETS Doctrines
        for doc in doctrines:
            key = (source_judg_id, doc.id, "INTERPRETS")
            if key not in seen:
                seen.add(key)
                relations.append(
                    Relation(
                        source_id=source_judg_id,
                        target_id=doc.id,
                        type="INTERPRETS",
                        confidence=0.90,
                        page=page_number,
                        evidence_text=f"{document_title} interprets {doc.name}",
                    )
                )

        # Judgment REFERENCES Acts
        for act in acts:
            if act.id != f"act:{_slug(document_title)}":
                if re.search(r"\b(?:referred to|cited|relied upon|under the|provisions of|statute|act)\b", text, re.I):
                    key = (source_judg_id, act.id, "REFERENCES")
                    if key not in seen:
                        seen.add(key)
                        relations.append(
                            Relation(
                                source_id=source_judg_id,
                                target_id=act.id,
                                type="REFERENCES",
                                confidence=0.85,
                                page=page_number,
                                evidence_text=f"{document_title} references {act.name}",
                            )
                        )

    # 4. AMENDS: amendment -> provision / act / constitution
    for amd in amendments:
        for prov in provisions:
            if re.search(r"\b(?:amend|amends|amended|inserted|substituted|repealed|omitted)\b", text, re.I):
                key = (amd.id, prov.id, "AMENDS")
                if key not in seen:
                    seen.add(key)
                    relations.append(
                        Relation(
                            source_id=amd.id,
                            target_id=prov.id,
                            type="AMENDS",
                            confidence=0.90,
                            page=page_number,
                            evidence_text=f"{amd.name} amends {prov.name}",
                        )
                    )

    # 5. OVERRULES: judgment -> judgment
    if len(judgments) >= 2 and re.search(r"\b(?:overruled|overruling)\b", text, re.I):
        primary_j = judgments[0]
        for target_j in judgments[1:]:
            key = (primary_j.id, target_j.id, "OVERRULES")
            if key not in seen:
                seen.add(key)
                relations.append(
                    Relation(
                        source_id=primary_j.id,
                        target_id=target_j.id,
                        type="OVERRULES",
                        confidence=0.90,
                        page=page_number,
                        evidence_text=f"{primary_j.name} overruled {target_j.name}",
                    )
                )

    return relations


def entity_provenance_key(chunk_id: str, entity_id: str) -> str:
    """Stable provenance key for entity-to-chunk SUPPORTED_BY relationships."""
    return sha256(f"{chunk_id}|{entity_id}|SUPPORTED_BY".encode()).hexdigest()


def contains_provenance_key(document_id: str, chunk_id: str) -> str:
    """Stable provenance key for document-to-chunk CONTAINS relationships."""
    return sha256(f"{document_id}|{chunk_id}|CONTAINS".encode()).hexdigest()


def source_fingerprint(chunk_id: str, relation: Relation) -> str:
    """Stable relationship provenance key for idempotent MERGE operations."""
    return sha256(
        f"{chunk_id}|{relation.source_id}|{relation.type}|{relation.target_id}".encode()
    ).hexdigest()


def entity_properties(entity: Entity) -> dict[str, Any]:
    return {"id": entity.id, "name": entity.name, "confidence": entity.confidence}
