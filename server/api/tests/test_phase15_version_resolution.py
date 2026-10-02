import pytest
from app.rag.temporal import resolve_legal_version, LegalVersionInfo


def test_resolve_article_21_before_1978():
    version = resolve_legal_version("article:constitution_of_india:21", target_year=1978)
    assert version.status == "HISTORICAL"
    assert "Pre-44th Amendment" in version.version_label
    assert version.effective_from == "1950-01-26"
    assert version.effective_to == "1979-06-19"


def test_resolve_article_21_current():
    version = resolve_legal_version("article:constitution_of_india:21", target_year=None)
    assert version.status == "IN_FORCE"
    assert version.effective_from == "1979-06-20"


def test_resolve_section_66a_after_2015():
    version = resolve_legal_version("section:it_act_2000:66a", target_year=2016)
    assert version.status == "REPEALED"
    assert "Shreya Singhal" in version.amendment_title


def test_resolve_section_66a_in_2010():
    version = resolve_legal_version("section:it_act_2000:66a", target_year=2010)
    assert version.status == "SUPERSEDED"
    assert version.effective_from == "2009-10-27"


def test_resolve_unknown_provision():
    version = resolve_legal_version("section:nonexistent_act:999", target_year=2020)
    assert version.status == "UNKNOWN"
    assert version.temporal_confidence == 0.0
