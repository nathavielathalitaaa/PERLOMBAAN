"""PDF Document Processing module using PyMuPDF (fitz).

Extracts text, metadata, page numbers, and calculates cryptographic hashes.
Adheres to Section 6 & 7: Extracted text is treated as unverified staging data.
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class PageExtraction:
    """Extracted text and structural information for an individual document page."""
    page_number: int  # 1-indexed
    text: str
    character_count: int
    word_count: int


@dataclass
class DocumentExtractionResult:
    """Full extraction result for a source document with provenance metadata."""
    file_path: str
    file_name: str
    file_hash_sha256: str
    total_pages: int
    title: Optional[str]
    author: Optional[str]
    pages: List[PageExtraction] = field(default_factory=list)
    is_verified: bool = False  # Always False upon initial extraction (human oversight required)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class PDFExtractor:
    """Service to process PDF competition documents with provenance tracking."""

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file to ensure document provenance integrity."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def extract_document(self, file_path: str | Path) -> DocumentExtractionResult:
        """Extract text and metadata from a PDF file page by page.
        
        Args:
            file_path: Path to the target PDF file.

        Returns:
            DocumentExtractionResult with page-level text and metadata.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is not a valid PDF.
        """
        path = Path(file_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Source document file not found: {path}")

        file_hash = self.calculate_sha256(path)
        logger.info("Processing document: %s (SHA-256: %s)", path.name, file_hash)

        try:
            doc = pymupdf.open(str(path))
        except Exception as exc:
            raise ValueError(f"Failed to open PDF document: {path}. Error: {exc}") from exc

        pages_data: List[PageExtraction] = []
        doc_metadata = doc.metadata or {}

        for page_index in range(len(doc)):
            page = doc[page_index]
            page_text = page.get_text("text").strip()
            word_count = len(page_text.split()) if page_text else 0
            
            pages_data.append(
                PageExtraction(
                    page_number=page_index + 1,
                    text=page_text,
                    character_count=len(page_text),
                    word_count=word_count,
                )
            )

        total_pages = len(doc)
        title = doc_metadata.get("title") or path.stem
        author = doc_metadata.get("author")
        doc.close()

        result = DocumentExtractionResult(
            file_path=str(path),
            file_name=path.name,
            file_hash_sha256=file_hash,
            total_pages=total_pages,
            title=title,
            author=author,
            pages=pages_data,
            is_verified=False,  # Unverified until confirmed by researcher
        )

        return result

    def search_excerpts(
        self, extraction_result: DocumentExtractionResult, keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """Search for candidate excerpts in extracted pages matching specified keywords.
        
        Aids researchers in locating evidence without making automated assertions.
        """
        matches = []
        lowered_keywords = [k.lower() for k in keywords]

        for page in extraction_result.pages:
            lowered_text = page.text.lower()
            for kw in lowered_keywords:
                if kw in lowered_text:
                    # Extract surrounding context
                    start_idx = lowered_text.find(kw)
                    snippet_start = max(0, start_idx - 100)
                    snippet_end = min(len(page.text), start_idx + len(kw) + 100)
                    snippet = page.text[snippet_start:snippet_end].replace("\n", " ")

                    matches.append({
                        "keyword": kw,
                        "page_number": page.page_number,
                        "candidate_snippet": snippet.strip(),
                    })
        return matches
