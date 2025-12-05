"""PDF text and image extraction functions."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

# package imports
from pdf2icd.utils import clean_printable_unicode, compress_line_whitespace


def extract_pdf_text(pdf_path: str | Path, timeout: int = 180) -> str:
    """Extract all text from a PDF using pdftotext and clean Unicode control/noncharacter codepoints.

    Args:
        pdf_path (str | Path): path to PDF file
        timeout (int): subprocess timeout in seconds

    Returns:
        str: extracted and cleaned text

    """
    cmd = ["pdftotext", pdf_path, "-"]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pdftotext failed: {e.stderr.decode(errors='ignore')}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("pdftotext timed out")

    text = result.stdout.decode("utf-8", errors="replace")
    text = clean_printable_unicode(text)
    return compress_line_whitespace(text)


def fetch_pdf_images(
    pdf_path: str | Path,
    timeout: int = 60,
) -> Iterator[Path]:
    """Yield image file paths from a PDF, one page at a time, using a temporary directory.

    For each page number containing an image, run pdfimages on just that page in a fresh temporary directory and yield
    all extracted image file(s).

    Args:
        pdf_path (str | Path): path to PDF file
        timeout (int): subprocess timeout in seconds

    Yields:
        Path: path to each extracted image

    """
    page_numbers = get_image_page_numbers(pdf_path, timeout=timeout)
    for page in page_numbers:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            out_prefix = tmpdir_path / f"page_{page}"
            cmd = [
                "pdfimages",
                "-f",
                str(page),
                "-l",
                str(page),
                str(pdf_path),
                str(out_prefix),
            ]
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"pdfimages failed: {e.stderr.decode(errors='ignore')}")
            except subprocess.TimeoutExpired:
                raise RuntimeError("pdfimages timed out")

            for image_file in sorted(tmpdir_path.glob(f"{out_prefix.name}-*")):
                yield image_file


def get_image_page_numbers(pdf_path: str | Path, timeout: int = 60) -> list[int]:
    """Return sorted unique page numbers containing images in a PDF using a simple parser.

    Args:
        pdf_path (str | Path): path to PDF file
        timeout (int): subprocess timeout in seconds

    Returns:
        list[int]: sorted list of unique page numbers (1-based)

    """
    cmd = ["pdfimages", "-list", str(pdf_path)]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pdfimages failed: {e.stderr.decode(errors='ignore')}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("pdfimages timed out")

    page_numbers = set()
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        fields = line.split()
        page_numbers.add(int(fields[0]))
    return sorted(page_numbers)
