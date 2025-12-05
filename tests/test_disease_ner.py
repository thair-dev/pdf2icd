"""Unit tests for disease_ner.py."""

from __future__ import annotations

# external imports
import pytest

# package imports
from pdf2icd.disease_ner import DiseaseNER


@pytest.fixture(scope="module")
def ner() -> DiseaseNER:
    """Return a DiseaseNER instance (spaCy model loaded once per module)."""
    return DiseaseNER("en_ner_bc5cdr_md")


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "Patient history includes COPD, AFIB, and diabetes mellitus.",
            ["COPD", "chronic obstructive pulmonary disease atrial fibrillation", "diabetes mellitus"],
        ),
        (
            "The patient presented with Hypertension and myocardial infarction.",
            ["Hypertension", "myocardial infarction"],
        ),
        (
            "Symptoms included fever and chronic kidney disease.",
            ["chronic kidney disease", "fever"],
        ),
        (
            "No evidence of tuberculosis or coronary artery disease.",
            ["coronary artery disease", "tuberculosis"],
        ),
    ],
)
def test_extract_mentions_real_text(ner: DiseaseNER, text: str, expected: list[str]) -> None:
    """Test DiseaseNER.extract_mentions returns expected disease mentions.

    Args:
        ner (DiseaseNER): the DiseaseNER instance
        text (str): input biomedical text
        expected (list[str]): sorted list of expected disease mentions

    """
    mentions = ner.extract_mentions(text)
    assert mentions == expected, f"Expected {expected}, got {mentions} for text: {text}"
    assert mentions == expected, f"Expected {expected}, got {mentions} for text: {text}"
