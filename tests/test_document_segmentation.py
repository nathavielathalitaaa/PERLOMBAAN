"""Automated tests for Stage 3 Document Segmentation (`CompetitionBranchUnit`)."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, List

import pytest

from src.document_processing.document_segmenter import segment_documents

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_TXT_DIR = PROJECT_ROOT / "data" / "raw" / "txt"
INITIAL_CSV = PROJECT_ROOT / "data" / "processed" / "document_inventory.csv"
INITIAL_JSON = PROJECT_ROOT / "data" / "processed" / "document_inventory.json"
VALIDATED_CSV = PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.csv"
VALIDATED_JSON = PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.json"
TAXONOMY_JSON = PROJECT_ROOT / "data" / "processed" / "competition_taxonomy.json"
UNITS_JSON = PROJECT_ROOT / "data" / "processed" / "competition_branch_units.json"
UNITS_CSV = PROJECT_ROOT / "data" / "processed" / "competition_branch_units.csv"
REPORT_MD = PROJECT_ROOT / "docs" / "research_notes" / "document_segmentation_report.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage1_and_stage2_files_untouched_during_segmentation(tmp_path: Path) -> None:
    """Running segment_documents must never alter Stage 1 or Stage 2 files."""
    hashes_before = {
        p: _sha256(p)
        for p in (INITIAL_CSV, INITIAL_JSON, VALIDATED_CSV, VALIDATED_JSON, TAXONOMY_JSON)
    }

    out_json = tmp_path / "units.json"
    out_csv = tmp_path / "units.csv"
    segment_documents(
        raw_txt_dir=RAW_TXT_DIR,
        validated_inventory_json=VALIDATED_JSON,
        taxonomy_json_path=TAXONOMY_JSON,
        output_units_json=out_json,
        output_units_csv=out_csv,
    )

    for path, before_digest in hashes_before.items():
        assert _sha256(path) == before_digest


def test_every_branch_unit_has_valid_document_id_and_taxonomy_branch_code() -> None:
    """Every branch_unit must reference a valid parent document_id and valid taxonomy branch_code."""
    assert UNITS_JSON.exists()
    assert UNITS_CSV.exists()
    assert REPORT_MD.exists()

    validated_data = json.loads(VALIDATED_JSON.read_text(encoding="utf-8"))
    valid_doc_ids = {d["document_id"] for d in validated_data["documents"]}

    taxonomy_data = json.loads(TAXONOMY_JSON.read_text(encoding="utf-8"))
    valid_branch_codes = {
        b["branch_code"]
        for dom in taxonomy_data["competition_domains"]
        for b in dom["branches"]
    }

    units_data = json.loads(UNITS_JSON.read_text(encoding="utf-8"))
    units = units_data["branch_units"]
    assert len(units) == 114

    with UNITS_CSV.open("r", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    assert len(csv_rows) == len(units)

    for u in units:
        assert u["document_id"] in valid_doc_ids
        assert u["branch_code"] in valid_branch_codes
        assert len(u["required_component_branches"]) >= 1
        for comp_code in u["required_component_branches"]:
            assert comp_code in valid_branch_codes
        assert u["evidence_type"] in ("explicit", "inferred")
        assert 0.0 < float(u["confidence"]) <= 1.0


def test_character_ranges_within_document_bounds_and_traceable_to_source() -> None:
    """Character ranges (start_char, end_char) must never exceed document length and must trace to source text."""
    units_data = json.loads(UNITS_JSON.read_text(encoding="utf-8"))
    for u in units_data["branch_units"]:
        txt_path = RAW_TXT_DIR / u["file_name"]
        assert txt_path.exists(), f"Source TXT missing for {u['branch_unit_id']}"
        raw_text = txt_path.read_text(encoding="utf-8", errors="replace")
        doc_len = len(raw_text)

        start_char = u["start_char"]
        end_char = u["end_char"]
        assert 0 <= start_char < end_char <= doc_len, (
            f"Out-of-bounds char span {start_char}..{end_char} for doc length {doc_len} in {u['branch_unit_id']}"
        )
        assert u["char_length"] == end_char - start_char
        assert u["evidence_text"] and len(u["evidence_text"].strip()) >= 10

        # If page range is populated, start_page <= end_page
        if u["start_page"] is not None or u["end_page"] is not None:
            assert u["start_page"] is not None and u["end_page"] is not None
            assert 1 <= int(u["start_page"]) <= int(u["end_page"])


def test_no_duplicate_branch_units() -> None:
    """Branch unit IDs and unit signatures must be strictly unique."""
    units_data = json.loads(UNITS_JSON.read_text(encoding="utf-8"))
    units = units_data["branch_units"]

    unit_ids = [u["branch_unit_id"] for u in units]
    assert len(unit_ids) == len(set(unit_ids)), "Duplicate branch_unit_id detected"

    signatures = [
        (u["document_id"], u["branch_code"], u["section_title"], u["start_char"], u["end_char"])
        for u in units
    ]
    assert len(signatures) == len(set(signatures)), "Duplicate branch unit signature detected"


def test_multi_branch_documents_have_separate_units_and_composite_records_components() -> None:
    """Every multi_branch_event document must have >= 2 separate units, and composite docs record all components."""
    validated_data = json.loads(VALIDATED_JSON.read_text(encoding="utf-8"))
    units_data = json.loads(UNITS_JSON.read_text(encoding="utf-8"))

    units_by_doc: Dict[str, List[dict]] = {}
    for u in units_data["branch_units"]:
        units_by_doc.setdefault(u["document_id"], []).append(u)

    for doc in validated_data["documents"]:
        doc_id = doc["document_id"]
        mtype = doc["multi_branch_type"]
        if mtype == "multi_branch_event":
            assert doc_id in units_by_doc
            assert len(units_by_doc[doc_id]) >= 2, (
                f"multi_branch_event {doc_id} must have >= 2 separate units"
            )
        elif mtype == "composite_branch_competition":
            assert doc_id in units_by_doc
            assert len(units_by_doc[doc_id]) == 1
            comp_unit = units_by_doc[doc_id][0]
            assert len(comp_unit["required_component_branches"]) >= 2
            assert comp_unit["required_component_branches"] == doc["branch_codes"]
        elif mtype == "single_branch":
            assert doc_id in units_by_doc
            assert len(units_by_doc[doc_id]) == 1
        elif mtype == "primary_branch_with_multi_event_intro":
            assert doc_id in units_by_doc
            assert len(units_by_doc[doc_id]) == 1
            # Must isolate the primary section after the multi-event intro (start_char > 0)
            assert units_by_doc[doc_id][0]["start_char"] > 0


def test_empty_and_non_competition_documents_excluded_and_needs_review_flagged() -> None:
    """Empty and non-competition docs must not produce branch units; ambiguous sections must be flagged needs_review."""
    units_data = json.loads(UNITS_JSON.read_text(encoding="utf-8"))
    unit_doc_ids = {u["document_id"] for u in units_data["branch_units"]}
    excluded_ids = {e["document_id"] for e in units_data["excluded_documents"]}

    # DOC-005 (Rekrutmen), DOC-014 (Bootcamp), DOC-034 (Empty), DOC-060 (Modul) must be excluded
    expected_excluded = {"DOC-005", "DOC-014", "DOC-034", "DOC-060"}
    assert excluded_ids == expected_excluded
    assert unit_doc_ids.isdisjoint(expected_excluded)

    # Check that documents whose sections are interwoven or need manual review are flagged needs_review=True
    review_units = {u["branch_unit_id"]: u for u in units_data["branch_units"] if u["needs_review"]}
    assert "DOC-008-BU-01" in review_units  # Interwoven Puisi & Cerpen rules
    assert "DOC-008-BU-02" in review_units
    assert "DOC-047-BU-04" in review_units  # Partial Pre-Event subthemes without Tahap Terpusat chapter
    assert "DOC-054-BU-01" in review_units  # Filename mismatch (HACKATHON vs PE STEM)
    assert "DOC-073-BU-01" in review_units  # Filename mismatch (STEM vs Hackathon)
    assert "DOC-066-BU-01" in review_units  # External technical specs (LKS 2024)
    assert "DOC-068-BU-01" in review_units  # External technical specs (LKS 2026)
    assert "DOC-075-BU-01" in review_units  # Socialization slides (LKS 2025)
    assert "DOC-007-BU-01" in review_units  # Finalist catalog
