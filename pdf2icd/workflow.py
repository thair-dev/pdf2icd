"""End-to-end PDF → Disease Mention → ICD Code(s) Mapping Workflow (TSV Output).

Extracts text (embedded + OCR) from PDF, detects disease mentions with spaCy NER,
maps each mention to UMLS CUIs and ICD codes using dictionary and fuzzy match,
and writes results to a TSV (mention, matched, score, cui, icd_codes).

Usage:
    workflow --pdf input.pdf --output output.tsv

"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

# package imports
from pdf2icd.disease_matcher import DiseaseMatcher
from pdf2icd.disease_ner import DiseaseNER
from pdf2icd.logs import get_logger
from pdf2icd.ocr import extract_ocr_text
from pdf2icd.poppler import extract_pdf_text, get_image_page_numbers
from pdf2icd.utils import write_tsv

log = get_logger()


def get_arg_parser() -> argparse.ArgumentParser:
    """Return argument parser for CLI workflow."""
    parser = argparse.ArgumentParser(description="Extract and map disease mentions from PDF to ICD codes (TSV output)")
    parser.add_argument("--pdf", type=Path, required=True, help="Path to input PDF file")
    parser.add_argument("--output", type=Path, required=True, help="Path to output TSV file")
    parser.add_argument("--ner-model", type=str, default="en_ner_bc5cdr_md", help="spaCy NER model to use")
    parser.add_argument("--fuzzy-limit", type=int, default=3, help="Number of fuzzy matches per mention")
    parser.add_argument("--fuzzy-threshold", type=int, default=85, help="Fuzzy match score threshold")
    parser.add_argument("--ocr-languages", type=str, default="eng", help="OCR language(s) (default: eng)")
    parser.add_argument("--ocr-timeout", type=int, default=600, help="OCR extraction timeout (seconds)")
    parser.add_argument("--pdf-timeout", type=int, default=180, help="Embedded text extraction timeout (seconds)")
    parser.add_argument("--deduplicate", action="store_true", help="Deduplicate lines between PDF and OCR text")
    return parser


def extract_all_pdf_text(
    pdf_path: str | Path,
    ocr_languages: str = "eng",
    ocr_timeout: int = 600,
    pdf_timeout: int = 180,
    deduplicate: bool = True,
) -> str:
    """Extract and return all available text from a PDF using embedded and OCR text.

    Args:
        pdf_path (str | Path): path to the PDF file
        ocr_languages (str): language(s) for OCR
        ocr_timeout (int): OCR engine timeout (seconds)
        pdf_timeout (int): embedded text extraction timeout (seconds)
        deduplicate (bool): whether to deduplicate lines between PDF and OCR text

    Returns:
        str: cleaned, merged text from all sources

    """
    log.info(f"Extracting embedded text from PDF: {pdf_path}")
    text_pdf = extract_pdf_text(pdf_path, timeout=pdf_timeout)
    log.info("Identifying image-based pages for OCR...")
    image_pages = get_image_page_numbers(pdf_path, timeout=pdf_timeout)

    text_ocr = ""
    if image_pages:
        log.info(f"Performing OCR on {len(image_pages)} image-based pages")
        text_ocr = extract_ocr_text(
            input_pdf=pdf_path,
            pages=image_pages,
            languages=ocr_languages,
            timeout=ocr_timeout,
        )

    if deduplicate:
        lines: set[str] = set()
        if text_pdf:
            lines.update(line.strip() for line in text_pdf.splitlines() if line.strip())
        if text_ocr:
            lines.update(line.strip() for line in text_ocr.splitlines() if line.strip())
        all_text = "\n".join(sorted(lines))
    else:
        all_text = text_pdf + "\n" + text_ocr

    log.info(f"Extracted {len(all_text)} characters of text from PDF")
    return all_text.strip()


def main(args: list[str] | None = None) -> None:
    """Run the PDF-to-ICD mapping workflow from command-line arguments.

    Args:
        args (list[str] | None): CLI argument list, or None for sys.argv[1:]
    """
    parser = get_arg_parser()
    parsed_args = parser.parse_args(args)

    log.info(f"Running workflow for PDF: {parsed_args.pdf}")
    text = extract_all_pdf_text(
        pdf_path=parsed_args.pdf,
        ocr_languages=parsed_args.ocr_languages,
        ocr_timeout=parsed_args.ocr_timeout,
        pdf_timeout=parsed_args.pdf_timeout,
        deduplicate=parsed_args.deduplicate,
    )

    rows = map_diseases(
        text=text,
        ner_model=parsed_args.ner_model,
        fuzzy_limit=parsed_args.fuzzy_limit,
        fuzzy_threshold=parsed_args.fuzzy_threshold,
    )

    write_tsv(rows, parsed_args.output, ["mention", "matched", "score", "cui", "icd_codes"])
    log.info(f"Workflow complete. Output saved to {parsed_args.output.resolve()}")


def map_diseases(
    text: str,
    ner_model: str = "en_ner_bc5cdr_md",
    fuzzy_limit: int = 3,
    fuzzy_threshold: int = 85,
) -> list[dict[str, Any]]:
    """Extract disease mentions from input text and map each to CUIs and ICD codes.

    Args:
        text (str): biomedical text (already extracted from PDF)
        ner_model (str): spaCy NER model name
        fuzzy_limit (int): max number of fuzzy matches per mention
        fuzzy_threshold (int): minimum fuzzy match score

    Returns:
        list[dict[str, Any]]: list of result rows with mention, matched, score, cui, icd_codes

    """
    log.info("Extracting disease mentions from text")
    ner = DiseaseNER(ner_model=ner_model)
    mentions = sorted(set(ner.extract_mentions(text)))
    log.info(f"  Found {len(mentions)} unique disease mentions")

    matcher = DiseaseMatcher()

    rows: list[dict[str, Any]] = []
    for mention in mentions:
        match_rows = matcher.best_match(mention, limit=fuzzy_limit, threshold=fuzzy_threshold)
        if match_rows:
            for row in match_rows:
                rows.append(
                    {
                        "mention": mention,
                        "matched": row["matched"],
                        "score": str(row["score"]),
                        "cui": row["cui"],
                        "icd_codes": (
                            ",".join(row["icd_codes"])
                            if isinstance(row["icd_codes"], list)
                            else str(row["icd_codes"] or "")
                        ),
                    }
                )
        else:
            rows.append(
                {
                    "mention": mention,
                    "matched": "",
                    "score": "",
                    "cui": "",
                    "icd_codes": "",
                }
            )
    return rows
