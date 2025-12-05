"""Unit tests for ocr.py."""

from __future__ import annotations

from pathlib import Path

# external imports
import pytest

# package imports
from pdf2icd.ocr import extract_ocr_text

TEST_DATA_DIR = Path("tests/data")


@pytest.mark.parametrize(
    "test_file, pages, expected_file",
    [
        (
            TEST_DATA_DIR / "input" / "mixed_data.pdf",
            None,
            TEST_DATA_DIR / "output" / "ocr.txt",
        ),
        (
            TEST_DATA_DIR / "input" / "mixed_data.pdf",
            [2],
            TEST_DATA_DIR / "output" / "ocr_page2.txt",
        ),
    ],
)
def test_extract_ocr_text(test_file: Path, pages: list[int] | None, expected_file: Path) -> None:
    """Test extract_ocr_text."""
    assert extract_ocr_text(test_file, pages=pages) == expected_file.read_text(
        encoding="utf-8"
    ), f"Extracted OCR text does not match expected output for {test_file} with pages {pages}"
