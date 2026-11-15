"""Automated tests for Stage 2 Inventory Audit, Validation, and Competition Taxonomy."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from src.document_processing.inventory_validator import (
    BRANCH_TO_DOMAIN,
    DOCUMENT_TYPE_TO_MACRO_CATEGORY,
    get_recommended_stage3_metadata_schema,
    validate_inventory,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_TXT_DIR = PROJECT_ROOT / "data" / "raw" / "txt"
INITIAL_CSV = PROJECT_ROOT / "data" / "processed" / "document_inventory.csv"
INITIAL_JSON = PROJECT_ROOT / "data" / "processed" / "document_inventory.json"
TAXONOMY_KB_JSON = (
    PROJECT_ROOT / "knowledge_base" / "competition_requirements" / "competition_taxonomy.json"
)
TAXONOMY_PROC_JSON = PROJECT_ROOT / "data" / "processed" / "competition_taxonomy.json"
VALIDATED_CSV = PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.csv"
VALIDATED_JSON = PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.json"
AUDIT_REPORT_JSON = PROJECT_ROOT / "data" / "processed" / "inventory_audit_report.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_original_inventory_files_preserved_and_not_overwritten(tmp_path: Path) -> None:
    """Running validate_inventory must never modify or overwrite initial Stage 1 files."""
    csv_hash_before = _sha256(INITIAL_CSV)
    json_hash_before = _sha256(INITIAL_JSON)

    out_csv = tmp_path / "validated.csv"
    out_json = tmp_path / "validated.json"
    out_audit = tmp_path / "audit.json"

    validate_inventory(
        raw_txt_dir=RAW_TXT_DIR,
        initial_inventory_json=INITIAL_JSON,
        taxonomy_json_path=TAXONOMY_KB_JSON,
        output_validated_csv=out_csv,
        output_validated_json=out_json,
        output_audit_report_json=out_audit,
    )

    assert _sha256(INITIAL_CSV) == csv_hash_before
    assert _sha256(INITIAL_JSON) == json_hash_before


def test_validated_inventory_covers_all_80_documents_and_preserves_original_fields() -> None:
    """All 80 documents must be present and preserve Stage 1 fields intact."""
    assert VALIDATED_CSV.exists()
    assert VALIDATED_JSON.exists()
    assert AUDIT_REPORT_JSON.exists()

    initial_data = json.loads(INITIAL_JSON.read_text(encoding="utf-8"))
    validated_data = json.loads(VALIDATED_JSON.read_text(encoding="utf-8"))

    assert validated_data["summary"]["total_documents_audited"] == 80
    assert len(validated_data["documents"]) == 80

    with VALIDATED_CSV.open("r", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    assert len(csv_rows) == 80

    # Verify original fields are preserved identically for every single document
    initial_by_id = {d["document_id"]: d for d in initial_data["documents"]}
    for doc in validated_data["documents"]:
        orig = initial_by_id[doc["document_id"]]
        assert doc["file_name"] == orig["file_name"]
        assert doc["document_name"] == orig["document_name"]
        assert doc["character_count"] == orig["character_count"]
        assert doc["word_count"] == orig["word_count"]
        assert doc["readability_status"] == orig["readability_status"]
        assert doc["document_type"] == orig["document_type"]
        assert doc["competition_branch"] == orig["competition_branch"]
        assert doc["classification_status"] == orig["classification_status"]
        assert doc["original_document_type"] == orig["document_type"]
        assert doc["original_competition_branch"] == orig["competition_branch"]
        assert doc["original_classification_status"] == orig["classification_status"]


def test_macro_document_categories_distinguished() -> None:
    """All 6 required macro document categories (+ unknown for empty) must be distinguished."""
    validated_data = json.loads(VALIDATED_JSON.read_text(encoding="utf-8"))
    breakdown = validated_data["summary"]["macro_document_category_breakdown"]

    expected_categories = {
        "dokumen_panduan_kompetisi",
        "dokumen_ketentuan_dan_petunjuk_teknis",
        "modul_pembelajaran",
        "katalog_karya_atau_finalis",
        "dokumen_sosialisasi",
        "dokumen_lainnya",
        "unknown",
    }
    assert set(breakdown.keys()) == expected_categories
    assert sum(breakdown.values()) == 80


def test_taxonomy_json_structure_and_referential_integrity() -> None:
    """Every branch_code and domain_code in validated records must exist in competition_taxonomy.json."""
    assert TAXONOMY_KB_JSON.exists()
    assert TAXONOMY_PROC_JSON.exists()

    taxonomy = json.loads(TAXONOMY_KB_JSON.read_text(encoding="utf-8"))
    valid_domains = set()
    valid_branches = set()

    for dom in taxonomy["competition_domains"]:
        valid_domains.add(dom["domain_code"])
        for br in dom["branches"]:
            valid_branches.add(br["branch_code"])

    assert len(valid_domains) == 6
    assert len(valid_branches) >= 30

    validated_data = json.loads(VALIDATED_JSON.read_text(encoding="utf-8"))
    for doc in validated_data["documents"]:
        for dom_code in doc["domain_codes"]:
            assert dom_code in valid_domains, f"Unknown domain {dom_code} in {doc['document_id']}"
        for br_code in doc["branch_codes"]:
            assert br_code in valid_branches, f"Unknown branch {br_code} in {doc['document_id']}"
        for sec_code in doc["secondary_event_branch_codes"]:
            assert sec_code in valid_branches, f"Unknown secondary branch {sec_code} in {doc['document_id']}"


def test_every_classification_change_has_reason_and_verbatim_evidence() -> None:
    """Every document with classification_changed=True must have reason and verbatim text evidence."""
    audit_report = json.loads(AUDIT_REPORT_JSON.read_text(encoding="utf-8"))
    changes = audit_report["classification_changes"]
    assert len(changes) == 26

    for item in changes:
        assert item["classification_changed"] is True
        assert item["audit_reason"] and len(item["audit_reason"].strip()) > 20
        assert item["content_evidence"] and len(item["content_evidence"].strip()) > 15


def test_key_audit_corrections_and_multi_branch_support() -> None:
    """Verify specific high-impact audit findings (DOC-027, DOC-034, DOC-054, DOC-060, DOC-073, DOC-079)."""
    validated_data = json.loads(VALIDATED_JSON.read_text(encoding="utf-8"))
    by_id = {d["document_id"]: d for d in validated_data["documents"]}

    # DOC-027: GUIDEBOOK IT FEST 2026.txt -> corrected from single branch to 4 branches & guidebook
    doc27 = by_id["DOC-027"]
    assert doc27["original_document_type"] == "petunjuk_teknis"
    assert doc27["validated_document_type"] == "guidebook"
    assert doc27["is_multi_branch"] is True
    assert doc27["branch_codes"] == [
        "BR_SOFTWARE_DEV",
        "BR_NETWORK_ADMIN",
        "BR_CYBERSECURITY_CTF",
        "BR_VIDEO_FILM_PHOTO",
    ]

    # DOC-034: Guidebook BPC TSF 2026.txt -> empty file must remain unknown/unclassified
    doc34 = by_id["DOC-034"]
    assert doc34["readability_status"] == "empty"
    assert doc34["validated_document_type"] == "unknown"
    assert doc34["validated_competition_branch"] == "unknown"
    assert doc34["branch_codes"] == []
    assert doc34["reconversion_status"] == "needs_reextraction_empty"

    # DOC-054 & DOC-073: Swapped filenames vs internal content
    doc54 = by_id["DOC-054"]
    assert doc54["file_name"] == "HACKATHON GUIDEBOOK.txt"
    assert "BR_STEM_PROJECT" in doc54["branch_codes"]
    assert doc54["reconversion_status"] == "needs_filename_swap_fix"

    doc73 = by_id["DOC-073"]
    assert doc73["file_name"] == "STEM GUIDEBOOK.txt"
    assert "BR_HACKATHON" in doc73["branch_codes"]
    assert doc73["reconversion_status"] == "needs_filename_swap_fix"

    # DOC-060: Modul Pembelajaran
    doc60 = by_id["DOC-060"]
    assert doc60["macro_document_category"] == "modul_pembelajaran"
    assert doc60["branch_codes"] == []

    # DOC-007: Katalog Karya atau Finalis
    doc07 = by_id["DOC-007"]
    assert doc07["macro_document_category"] == "katalog_karya_atau_finalis"

    # DOC-079: essay.txt -> corrected from pedoman to ketentuan_lomba
    doc79 = by_id["DOC-079"]
    assert doc79["original_document_type"] == "pedoman"
    assert doc79["validated_document_type"] == "ketentuan_lomba"
    assert doc79["macro_document_category"] == "dokumen_ketentuan_dan_petunjuk_teknis"


def test_reconversion_list_and_stage3_metadata_schema() -> None:
    """Verify the 16 documents needing repair/reconversion and Stage 3 metadata schema."""
    audit_report = json.loads(AUDIT_REPORT_JSON.read_text(encoding="utf-8"))
    reconversion_docs = audit_report["documents_needing_repair_or_reconversion"]
    assert len(reconversion_docs) == 16

    statuses = {d["reconversion_status"] for d in reconversion_docs}
    assert statuses == {
        "needs_reextraction_empty",
        "needs_filename_swap_fix",
        "needs_font_encoding_fix",
        "needs_ocr_cleanup",
    }

    schema = get_recommended_stage3_metadata_schema()
    assert "document_metadata" in schema["entities"]
    assert "competition_event_metadata" in schema["entities"]
    assert "competition_branch_unit" in schema["entities"]
