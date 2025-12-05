"""Prepare two-step JSON lookup assets from UMLS RRF files for disease mention normalization and ICD code mapping.

- term_to_cuis.json: maps normalized disease mention strings to UMLS Concept Unique Identifiers (CUIs)
- cui_to_icd.json: maps CUIs to ICD code(s) using ICD code entries from MRCONSO.RRF

The following UMLS semantic type identifiers (TUIs) are included:
- T033: Finding (clinical findings - may include non-disease states)
- T047: Disease or Syndrome (core disease/diagnosis)
- T191: Neoplastic Process (cancer/tumors)

Usage:
    prepare_assets --mrsty MRSTY.RRF --mrconso MRCONSO.RRF --output-dir assets

"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

# package imports
from pdf2icd import DISEASE_TUIS
from pdf2icd.logs import get_logger
from pdf2icd.utils import normalize_term, write_json

log = get_logger()


def build_cui_to_icd(mrconso_path: str | Path, disease_cuis: set[str]) -> dict[str, list[str]]:
    """Build a mapping from CUI to ICD-10-CM code(s) (diseases only) using MRCONSO.RRF.

    Only CUIs in disease_cuis are included. Only codes with SAB == 'ICD10CM' are collected (U.S. diagnosis codes).

    Args:
        mrconso_path (str | Path): path to MRCONSO.RRF
        disease_cuis (set[str]): CUIs to include

    Returns:
        dict[str, list[str]]: CUI → list of ICD-10-CM code(s)

    Notes:
        Uses:
        - row[0]: CUI
        - row[11]: SAB (source vocabulary, filter for 'ICD10CM')
        - row[13]: CODE (ICD code string)
        See MRCONSO.ctl for layout.

    """
    cui_to_icd: dict[str, set[str]] = defaultdict(set)
    with open(mrconso_path, encoding="utf-8") as data_file:
        for row in csv.reader(data_file, delimiter="|"):
            if len(row) > 13:
                cui, sab, code = row[0], row[11], row[13]
                if cui in disease_cuis and sab == "ICD10CM" and code:
                    cui_to_icd[cui].add(code)
    return {k: sorted(v) for k, v in cui_to_icd.items()}


def build_term_to_cuis(mrconso_path: str | Path, disease_cuis: set[str]) -> dict[str, list[str]]:
    """Build a mapping from normalized term to associated CUIs (for diseases only).

    Only English-language terms (row[1] == "ENG") are included.

    Args:
        mrconso_path (str | Path): path to MRCONSO.RRF
        disease_cuis (set[str]): CUIs to include

    Returns:
        dict[str, list[str]]: normalized term → list of CUI(s)

    Notes:
        Uses:
        - row[0]: CUI
        - row[1]: LAT (language, filter for 'ENG')
        - row[14]: STR (the term string)
        See MRCONSO.ctl for layout.

    """
    term_to_cuis: dict[str, set[str]] = defaultdict(set)
    with open(mrconso_path, encoding="utf-8") as data_file:
        for row in csv.reader(data_file, delimiter="|"):
            if len(row) > 14:
                cui, lang, str_ = row[0], row[1], row[14]
                if cui in disease_cuis and lang == "ENG":
                    norm = normalize_term(str_)
                    term_to_cuis[norm].add(cui)
    return {k: sorted(v) for k, v in term_to_cuis.items()}


def get_arg_parser() -> argparse.ArgumentParser:
    """Return argument parser for CLI.

    Returns:
        argparse.ArgumentParser: argument parser with all arguments

    """
    parser = argparse.ArgumentParser(description=("Prepare UMLS disease mention to ICD mapping assets (JSON)."))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("assets"),
        help="Directory to save generated JSON mapping files (default: assets)",
    )
    parser.add_argument(
        "--mrsty",
        type=Path,
        required=True,
        help="Path to UMLS MRSTY.RRF file.",
    )
    parser.add_argument(
        "--mrconso",
        type=Path,
        required=True,
        help="Path to UMLS MRCONSO.RRF file.",
    )
    return parser


def load_disease_cuis(mrsty_path: str | Path) -> set[str]:
    """Load disease CUIs from MRSTY.RRF using predefined semantic types.

    Args:
        mrsty_path (str | Path): path to MRSTY.RRF

    Returns:
        set[str]: set of CUIs representing diseases

    Notes:
        Uses:
        - row[0]: CUI
        - row[1]: TUI (semantic type, filter for disease TUIs)
        See MRSTY.ctl for layout.

    """
    disease_cuis: set[str] = set()
    with open(mrsty_path, encoding="utf-8") as data_file:
        for row in csv.reader(data_file, delimiter="|"):
            if len(row) > 2:
                cui, tui = row[0], row[1]
                if tui in DISEASE_TUIS:
                    disease_cuis.add(cui)
    return disease_cuis


def main(args: list[str] | None = None) -> None:
    """Build term_to_cuis and cui_to_icd mappings and save as JSON.

    Args:
        args (list[str] | None): CLI argument list. If None, uses sys.argv[1:]

    """
    parser = get_arg_parser()
    parsed_args = parser.parse_args(args)

    output_dir = Path(parsed_args.output_dir)
    output_dir.mkdir(exist_ok=True)

    log.info("Parsing MRSTY.RRF")
    disease_cuis = load_disease_cuis(parsed_args.mrsty)
    log.info(f"  {len(disease_cuis):,} disease CUIs found")

    log.info("Building term_to_cuis.json")
    term_to_cuis = build_term_to_cuis(parsed_args.mrconso, disease_cuis)
    write_json(term_to_cuis, output_dir / "term_to_cuis.json")
    log.info(f"  {len(term_to_cuis):,} unique normalized terms")

    log.info("Building cui_to_icd.json")
    cui_to_icd = build_cui_to_icd(parsed_args.mrconso, disease_cuis)
    write_json(cui_to_icd, output_dir / "cui_to_icd.json")
    log.info(f"  {len(cui_to_icd):,} CUIs mapped to ICD codes")

    log.info(f"All assets saved to: {output_dir.expanduser().resolve()}")
