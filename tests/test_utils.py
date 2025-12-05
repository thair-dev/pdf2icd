"""Unit tests for utility functions used in PDF text extraction, normalization, and output.

Covers:
    - Unicode control/noncharacter removal (`clean_printable_unicode`)
    - Per-line whitespace compression (`compress_line_whitespace`)
    - Medical term normalization (`normalize_term`)
    - JSON output (`write_json`)
    - TSV output (`write_tsv`)
"""

from __future__ import annotations

import json
from pathlib import Path

# external imports
import pytest

# package imports
from pdf2icd.utils import (
    clean_printable_unicode,
    compress_line_whitespace,
    is_valid_mention,
    normalize_term,
    write_json,
    write_tsv,
)

TEST_DATA_DIR = Path("tests/data")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hello, world!", "Hello, world!"),
        ("Café μg β-blocker — test", "Café μg β-blocker — test"),
        ("test\u0000test\nnext", "testtest\nnext"),
        ("abc\ufdef\ufffe\uffffxyz", "abcxyz"),
        ("A\u200b\u000b\u000c\ufdd0B\n", "AB\n"),
        ("a\tb\rc", "a\tb\rc"),
    ],
)
def test_clean_printable_unicode(text: str, expected: str) -> None:
    """Test clean_printable_unicode."""
    assert clean_printable_unicode(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hello, world!", "Hello, world!"),
        ("A    B\tC", "A B C"),
        ("A\t\t\tB    C", "A B C"),
        ("foo   bar\nbaz\t\tqux", "foo bar\nbaz qux"),
        ("abc\n\n\t\nxyz", "abc\n\n\nxyz"),
        ("   foo   bar   ", "foo bar"),
        ("\n   foo    bar  \n\nbaz   qux\n", "\nfoo bar\n\nbaz qux"),
    ],
)
def test_compress_line_whitespace(text: str, expected: str) -> None:
    """Test compress_line_whitespace."""
    assert compress_line_whitespace(text) == expected


@pytest.mark.parametrize(
    "term,expected",
    [
        ("Cancer", True),
        ("•", False),
        ("---", False),
        ("Chronic kidney disease", True),
        ("    ", False),
        ("• Diabetes", True),  # alphanumeric after bullet
        ("", False),
        ("COVID-19", True),
        ("   .  ", False),
        ("Myocardial infarction", True),
        ("❖", False),
        ("α-thalassemia", True),  # Greek letter, but thalassemia is alphanumeric
        ("— HTN —", True),  # will normalize to 'htn', which is valid
    ],
)
def test_is_valid_mention(term: str, expected: bool) -> None:
    """Test is_valid_mention returns True only for real disease mentions (not symbols/punctuation)."""
    assert is_valid_mention(term) == expected, f"Failed on term: {term!r}"


@pytest.mark.parametrize(
    "input_term, expected",
    [
        ("COPD", "chronic obstructive pulmonary disease"),
        ("copd", "chronic obstructive pulmonary disease"),
        ("cancers", "cancer"),
        ("Findings", "finding"),
        ("HTN", "hypertension"),
        ("Diabetes", "diabetes"),
        ("Foo---Bar", "foo---bar"),  # Punctuation kept if hyphen/period
        ("multiple    spaces", "multiple spaces"),
    ],
)
def test_normalize_term(input_term: str, expected: str) -> None:
    """Test normalize_term with abbreviations, punctuation, plural reduction, and whitespace."""
    assert normalize_term(input_term) == expected


def test_write_json(tmp_path: Path) -> None:
    """Test write_json writes and formats output as JSON."""
    test_obj = {"foo": [1, 2], "bar": "baz"}
    out_file = tmp_path / "test.json"
    write_json(test_obj, out_file)
    assert out_file.exists()
    with out_file.open("r", encoding="utf-8") as f:
        result = json.load(f)
    assert result == test_obj


def test_write_tsv(tmp_path: Path) -> None:
    """Test write_tsv writes rows as TSV with correct header and values."""
    rows = [
        {"disease": "HTN", "icd": "I10"},
        {"disease": "COPD", "icd": "J44.9"},
    ]
    out_file = tmp_path / "test.tsv"
    write_tsv(rows, out_file)
    assert out_file.exists()
    with out_file.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    # Header present and both data lines present
    assert lines[0].split("\t") == sorted(rows[0].keys())
    data_lines = [line.split("\t") for line in lines[1:]]
    # Should contain both original rows (order not guaranteed)
    assert {"disease": "HTN", "icd": "I10"} in [dict(zip(sorted(rows[0].keys()), vals)) for vals in data_lines]
    assert {"disease": "COPD", "icd": "J44.9"} in [dict(zip(sorted(rows[0].keys()), vals)) for vals in data_lines]
