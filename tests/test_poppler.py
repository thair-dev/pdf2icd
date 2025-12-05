"""Unit tests for poppler.py."""

from __future__ import annotations

from pathlib import Path

# package imports
from pdf2icd.poppler import extract_pdf_text, fetch_pdf_images, get_image_page_numbers

TEST_DATA_DIR = Path("tests/data")


def assert_images_equal(path1: str | Path, path2: str | Path) -> None:
    """Assert that two image files are byte-for-byte identical."""
    with open(path1, "rb") as f1, open(path2, "rb") as f2:
        data1 = f1.read()
        data2 = f2.read()
    assert data1 == data2, f"Image files differ: {path1} vs {path2}"


def test_extract_pdf_text() -> None:
    """Test extract_pdf_text."""
    test_file = TEST_DATA_DIR / "input" / "mixed_data.pdf"
    expected = TEST_DATA_DIR / "output" / "digital.txt"
    assert extract_pdf_text(test_file) == expected.read_text(
        encoding="utf-8"
    ), "Extracted text does not match expected output"


def test_get_image_page_numbers() -> None:
    """Test get_image_page_numbers."""
    test_file = TEST_DATA_DIR / "input" / "mixed_data.pdf"
    assert get_image_page_numbers(test_file) == [
        2,
        3,
    ], "Page numbers do not match expected output"


def test_fetch_pdf_images() -> None:
    """Test fetch_pdf_images and compare to expected output images using a temporary directory."""
    test_file = TEST_DATA_DIR / "input" / "mixed_data.pdf"
    test_output_dir = TEST_DATA_DIR / "output" / "images"

    for idx, img_path in enumerate(fetch_pdf_images(test_file), 1):
        expected = test_output_dir / f"image{idx}.ppm"
        assert_images_equal(img_path, expected)
