"""Unit tests for disease_matcher.py."""

from __future__ import annotations

# external imports
import pytest
from pytest_mock import MockerFixture

# package imports
from pdf2icd.disease_matcher import DiseaseMatcher


@pytest.fixture
def mock_data(mocker: MockerFixture) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Mock dictionary data for term_to_cuis and cui_to_icd (use real normalize_term).

    Args:
        mocker (MockerFixture): pytest-mock fixture

    Returns:
        tuple[dict[str, list[str]], dict[str, list[str]]]: mocked dictionaries
    """
    mock_term_to_cuis: dict[str, list[str]] = {
        "hypertension": ["C001"],
        "high blood pressure": ["C001"],
        "chronic kidney disease": ["C002"],
        "deep vein thrombosis": ["C003"],
        "atrial fibrillation": ["C004"],
        "cancer": ["C005"],
    }
    mock_cui_to_icd: dict[str, list[str]] = {
        "C001": ["I10"],
        "C002": ["N18.9"],
        "C003": ["I82.40"],
        "C004": ["I48.91"],
        "C005": ["C80.1"],
    }
    mocker.patch("pdf2icd.disease_matcher.load_term_to_cuis", return_value=mock_term_to_cuis)
    mocker.patch("pdf2icd.disease_matcher.load_cui_to_icd", return_value=mock_cui_to_icd)
    return mock_term_to_cuis, mock_cui_to_icd


@pytest.mark.parametrize(
    "term, expected_cuis",
    [
        ("Hypertension", ["C001"]),
        ("high blood pressure", ["C001"]),
        ("CKD", ["C002"]),  # Abbreviation expansion to "chronic kidney disease"
        ("DVT", ["C003"]),  # Abbreviation expansion to "deep vein thrombosis"
        ("AFIB", ["C004"]),  # Abbreviation expansion to "atrial fibrillation"
        ("cancers", ["C005"]),  # Plural normalization to "cancer"
        ("unknown", []),
    ],
)
def test_exact_match_with_normalization(
    mock_data: tuple[dict[str, list[str]], dict[str, list[str]]], term: str, expected_cuis: list[str]
) -> None:
    """Test exact_match with normalization/abbreviation/plural handling."""
    matcher = DiseaseMatcher()
    results = matcher.exact_match(term)
    assert [r["cui"] for r in results] == expected_cuis


def test_best_match_adds_score(mock_data: tuple[dict[str, list[str]], dict[str, list[str]]]) -> None:
    """Test best_match returns score=100 for exact matches."""
    matcher = DiseaseMatcher()
    results = matcher.best_match("HTN")  # Will normalize to "hypertension" by abbreviation
    assert results
    for row in results:
        assert row["score"] == 100
        assert row["matched"] == "hypertension"


def test_fuzzy_match_integration(
    mocker: MockerFixture, mock_data: tuple[dict[str, list[str]], dict[str, list[str]]]
) -> None:
    """Test fuzzy_match passes through RapidFuzz and uses normalization."""
    mocker.patch(
        "pdf2icd.disease_matcher.process.extract",
        return_value=[
            ("hypertension", 92, None),
            ("deep vein thrombosis", 90, None),
        ],
    )
    matcher = DiseaseMatcher()
    result = matcher.fuzzy_match("Hypertenshun", limit=2, threshold=85)
    assert {"matched": "hypertension", "score": 92, "cui": "C001", "icd_codes": ["I10"]} in result
    assert {"matched": "deep vein thrombosis", "score": 90, "cui": "C003", "icd_codes": ["I82.40"]} in result


def test_fuzzy_match_caching(
    mocker: MockerFixture, mock_data: tuple[dict[str, list[str]], dict[str, list[str]]]
) -> None:
    """Test fuzzy_match populates and hits the cache."""
    mocker.patch(
        "pdf2icd.disease_matcher.process.extract",
        return_value=[
            ("hypertension", 88, None),
        ],
    )
    matcher = DiseaseMatcher()
    result1 = matcher.fuzzy_match("Hypertenshun", limit=1, threshold=80)
    result2 = matcher.fuzzy_match("Hypertenshun", limit=1, threshold=80)
    assert result1 == result2  # Should come from cache the second time


def test_best_match_falls_back_to_fuzzy(
    mocker: MockerFixture, mock_data: tuple[dict[str, list[str]], dict[str, list[str]]]
) -> None:
    """Test best_match uses fuzzy_match if exact_match is empty."""
    matcher = DiseaseMatcher()
    mocker.patch.object(matcher, "exact_match", return_value=[])
    mocker.patch.object(
        matcher,
        "fuzzy_match",
        return_value=[{"matched": "hypertension", "score": 90, "cui": "C001", "icd_codes": ["I10"]}],
    )
    results = matcher.best_match("Hypertenshun")
    assert results[0]["cui"] == "C001"
    assert results[0]["score"] == 90
