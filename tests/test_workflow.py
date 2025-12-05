"""Unit tests for workflow.py."""

from __future__ import annotations

from pathlib import Path

# external imports
import pytest

# package imports
from pdf2icd.utils import load_cui_to_icd, load_term_to_cuis
from pdf2icd.workflow import extract_all_pdf_text, map_diseases

TEST_DATA_DIR = Path("tests/data")


def _assets_available() -> bool:
    """Return True if UMLS-derived assets can be loaded via project loaders."""
    try:
        load_cui_to_icd()
        load_term_to_cuis()
        return True
    except Exception:
        return False


def test_extract_all_pdf_text() -> None:
    """Test extract_all_pdf_text (PDF + OCR)."""
    expected_file = TEST_DATA_DIR / "output" / "all_text.txt"
    expected = expected_file.read_text(encoding="utf-8")
    assert (
        extract_all_pdf_text(TEST_DATA_DIR / "input" / "mixed_data.pdf") == expected
    ), f"Extracted text does not match expected output for {expected_file}"


@pytest.mark.skipif(
    not _assets_available(),
    reason="Requires locally built UMLS-derived assets (see README: Preparing UMLS Mapping Assets)",
)
def test_map_diseases() -> None:
    """Verify mapping using subset checks only (no UMLS leakage)."""
    text = "History of HTN, DM, and COPD."

    expected = [
        {"mention": "COPD", "score": "100"},
        {"mention": "COPD", "score": "100"},
        {"mention": "HTN", "score": "100"},
        {"mention": "hypertension diabetes", "score": "85.0"},
    ]

    result = map_diseases(text)

    def _sort_key(row: dict[str, str]) -> tuple[str, str, str]:
        # Keep your original deterministic key; defaults guard missing keys
        return (row.get("mention", ""), row.get("matched", ""), row.get("cui", ""))

    sorted_result = sorted(result, key=_sort_key)

    # Ensure we have at least as many rows as expected for position-wise comparison
    assert len(sorted_result) >= len(
        expected
    ), f"Expected ≥{len(expected)} rows, got {len(sorted_result)}; result={sorted_result}"

    # Subset-by-position: each expected dict must be contained in the actual row
    for idx, (exp, row) in enumerate(zip(expected, sorted_result), start=1):
        assert exp.items() <= row.items(), (
            f"[{idx}] expected subset not satisfied.\n" f"expected_subset={exp}\n" f"actual_row={row}"
        )
