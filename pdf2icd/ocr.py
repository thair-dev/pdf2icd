"""OCR text extraction functions."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

# package imports
from pdf2icd.utils import compress_line_whitespace


def extract_ocr_text(
    input_pdf: str | Path,
    pages: list[int] | None = None,
    languages: str = "eng",
    timeout: int = 600,
) -> str:
    """Extract text from PDF/images using ocrmypdf, returning only the sidecar text.

    Args:
        input_pdf (str | Path): path to PDF or image
        pages (list[int] | None): list of 1-based page numbers to OCR
        languages (str): ocr language code(s)
        timeout (int): max seconds to wait

    Returns:
        str: extracted OCR text

    Raises:
        subprocess.CalledProcessError: if ocrmypdf fails

    """
    page_str = ",".join(str(p) for p in pages) if pages else None
    with tempfile.TemporaryDirectory() as tmpdir:
        sidecar_txt = Path(tmpdir) / "output.txt"
        cmd = [
            "ocrmypdf",
            "-l",
            languages,
            "--force-ocr",
            "-r",
            "-d",
            "-c",
            "--output-type",
            "none",
            "--sidecar",
            str(sidecar_txt),
        ]
        if page_str:
            cmd += ["--pages", page_str]
        cmd += [str(input_pdf), "-"]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ocrmypdf failed: {e.stderr.decode(errors='ignore')}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("ocrmypdf timed out")

        return compress_line_whitespace(sidecar_txt.read_text(encoding="utf-8"))
