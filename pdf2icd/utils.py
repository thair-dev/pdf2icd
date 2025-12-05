"""General-purpose utility functions for PDF text extraction and disease mention normalization.

Includes:
    - Unicode cleaning and whitespace normalization utilities.
    - Functions to load prebuilt dictionaries for disease term → CUI and CUI → ICD mappings.
    - Medical term normalization for dictionary and NER matching (lowercase, punctuation removal, abbreviation
      expansion, plural handling).
    - JSON/TSV output helpers for downstream processing.

These utilities are used across the pipeline for robust, reproducible preprocessing and mapping.

"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any


def clean_printable_unicode(text: str) -> str:
    """Remove control and noncharacter Unicode codepoints but keep printable letters, digits, punctuation, and spaces.

    Args:
        text (str): input text

    Returns:
        str: cleaned text

    """
    return "".join(
        c
        for c in text
        if (
            (unicodedata.category(c)[0] != "C" or c in "\n\t\r")
            and not (0xFDD0 <= ord(c) <= 0xFDEF or (ord(c) & 0xFFFE) == 0xFFFE)
        )
    )


def compress_line_whitespace(text: str) -> str:
    """Collapse runs of whitespace within each line to a single space, preserving line breaks.

    Args:
        text (str): input text

    Returns:
        str: text with compressed internal whitespace per line

    """
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(lines)


def is_valid_mention(term: str) -> bool:
    """Return True if the mention is not just punctuation or symbols.

    Args:
        term (str): input medical term or mention

    Returns:
        bool: True if the term contains alphanumeric characters, False otherwise

    """
    norm = normalize_term(term)
    return any(c.isalnum() for c in norm)


@lru_cache(maxsize=1)
def load_cui_to_icd() -> dict[str, list[str]]:
    """Load the local mapping of UMLS CUI to ICD code(s).

    Asset is prepared using prepare_umls_assets.py.

    Returns:
        dict[str, list[str]]: cui → list of ICD code(s)

    """
    with resources.files("pdf2icd.assets").joinpath("cui_to_icd.json").open("r", encoding="utf-8") as data_file:
        return json.load(data_file)  # type: ignore[no-any-return]


@lru_cache(maxsize=1)
def load_term_to_cuis() -> dict[str, list[str]]:
    """Load the local mapping of normalized disease mentions to UMLS CUIs.

    Asset is prepared using prepare_umls_assets.py.

    Returns:
        dict[str, list[str]]: normalized term → list of UMLS CUIs
    """
    with resources.files("pdf2icd.assets").joinpath("term_to_cuis.json").open("r", encoding="utf-8") as data_file:
        return json.load(data_file)  # type: ignore[no-any-return]


def normalize_term(term: str) -> str:
    """Normalize a medical term for robust dictionary/NER matching.

    Normalization includes:
    - Lowercasing
    - Removing punctuation (except periods and hyphens)
    - Collapsing whitespace
    - Abbreviation expansion
    - Irregular plural handling

    Args:
        term (str): input medical term or mention

    Returns:
        str: normalized term

    """
    term = term.lower()
    term = re.sub(r"[^\w\s.-]", " ", term)
    term = re.sub(r"\s+", " ", term).strip()

    abbreviations = {
        "afib": "atrial fibrillation",
        "ca": "cancer",
        "cad": "coronary artery disease",
        "ckd": "chronic kidney disease",
        "copd": "chronic obstructive pulmonary disease",
        "dm": "diabetes",
        "dvt": "deep vein thrombosis",
        "dz": "disease",
        "hf": "heart failure",
        "htn": "hypertension",
        "mi": "myocardial infarction",
        "pe": "pulmonary embolism",
        "tb": "tuberculosis",
        "uti": "urinary tract infection",
    }
    for abbreviation, expansion in abbreviations.items():
        term = re.sub(rf"\b{abbreviation}\b", expansion, term)

    plural_map = {
        "cancers": "cancer",
        "diseases": "disease",
        "failures": "failure",
        "findings": "finding",
        "infarctions": "infarction",
        "syndromes": "syndrome",
        "tumors": "tumor",
    }
    for plural, singular in plural_map.items():
        term = re.sub(rf"\b{plural}\b", singular, term)

    return term


def write_json(obj: dict[str, Any], path: Path) -> None:
    """Write an object to a file as JSON.

    Args:
        obj (dict[str, Any]): dictionary to serialize
        path (Path): output file path

    """
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4, ensure_ascii=False, sort_keys=True)


def write_tsv(rows: list[dict[str, str]], output_path: str | Path, fieldnames: list[str] | None = None) -> None:
    """Write results to a TSV file.

    Args:
        rows (list[dict[str, str]]): list of mapping result dictionaries
        output_path (str | Path): output TSV file path
        fieldnames (list[str] | None): optional list of field names to use as header. If None defaults to first row keys

    """
    if not fieldnames:
        fieldnames = list(rows[0].keys())

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
