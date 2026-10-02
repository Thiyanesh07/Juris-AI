import pytest
from app.rag.query_analysis import analyze_query


def test_temporal_query_extraction_before_44th_amendment():
    query = "What did Article 21 provide before the 44th Amendment?"
    analysis = analyze_query(query)
    
    assert analysis.is_temporal is True
    assert analysis.temporal_operator == "BEFORE"
    assert "44th" in analysis.referenced_amendment
    assert analysis.target_year == 1978


def test_temporal_query_extraction_specific_year():
    query = "What did Article 21 protect in 1978?"
    analysis = analyze_query(query)
    
    assert analysis.is_temporal is True
    assert analysis.target_year == 1978
    assert analysis.target_date == "1978"


def test_temporal_query_extraction_after_amendment():
    query = "What changed after the 44th Constitutional Amendment?"
    analysis = analyze_query(query)
    
    assert analysis.is_temporal is True
    assert analysis.temporal_operator == "AFTER"
    assert "44th" in analysis.referenced_amendment


def test_non_temporal_query_compatibility():
    query = "What does Article 21 protect?"
    analysis = analyze_query(query)
    
    assert analysis.is_temporal is False
    assert analysis.target_year is None
    assert analysis.referenced_amendment is None
    assert analysis.temporal_operator == "CURRENT_LAW"
