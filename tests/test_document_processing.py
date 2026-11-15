"""Unit tests for PDF document extraction and cryptographic hashing."""

from pathlib import Path
import pytest

from src.document_processing.pdf_extractor import PDFExtractor


def test_pdf_extraction_page_count_and_text(sample_pdf: Path):
    """Verify PDFExtractor extracts page-level text, metadata, and calculates SHA-256."""
    extractor = PDFExtractor()
    result = extractor.extract_document(sample_pdf)

    assert result.total_pages == 2
    assert result.file_name == "gemastik_pedoman_2024.pdf"
    assert len(result.file_hash_sha256) == 64
    assert result.is_verified is False  # Must require human confirmation

    # Check Page 1 text
    page1 = result.pages[0]
    assert page1.page_number == 1
    assert "GEMASTIK XVII 2024" in page1.text
    assert "Pengembangan Perangkat Lunak" in page1.text
    assert page1.character_count > 0
    assert page1.word_count > 5

    # Check Page 2 text
    page2 = result.pages[1]
    assert page2.page_number == 2
    assert "KRITERIA PENILAIAN" in page2.text
    assert "Inovasi dan Keaslian Ide" in page2.text


def test_pdf_search_excerpts(sample_pdf: Path):
    """Verify searching candidate excerpts for specific keywords across pages."""
    extractor = PDFExtractor()
    result = extractor.extract_document(sample_pdf)

    matches = extractor.search_excerpts(result, keywords=["bobot", "anggota", "dosen"])
    assert len(matches) >= 2

    # Verify page location and snippet
    bobot_match = next(m for m in matches if m["keyword"] == "bobot")
    assert bobot_match["page_number"] == 2
    assert "Bobot" in bobot_match["candidate_snippet"]

    dosen_match = next(m for m in matches if m["keyword"] == "dosen")
    assert dosen_match["page_number"] == 1
    assert "dosen pembimbing" in dosen_match["candidate_snippet"].lower()


def test_missing_file_raises_error():
    """Verify FileNotFoundError is raised when file does not exist."""
    extractor = PDFExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract_document("/tmp/non_existent_file_98765.pdf")

