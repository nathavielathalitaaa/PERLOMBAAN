"""Unit tests for Stage 3 Semantic & Methodological Segmentation Validator."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from src.document_processing.segmentation_validator import (
    ENTITY_DISTINCTION_FRAMEWORK,
    SEMANTIC_ENTITY_TYPES,
    SPAN_CLASSIFICATIONS,
    VALID_STATUSES,
    run_segmentation_validation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage1_stage2_stage3_and_raw_files_untouched() -> None:
    """Ensure running segmentation validation does not modify raw TXT or Stage 1/2/3 files."""
    protected_files = [
        PROJECT_ROOT / "data" / "processed" / "document_inventory.json",
        PROJECT_ROOT / "data" / "processed" / "document_inventory.csv",
        PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.json",
        PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.csv",
        PROJECT_ROOT / "data" / "processed" / "competition_branch_units.json",
        PROJECT_ROOT / "data" / "processed" / "competition_branch_units.csv",
        PROJECT_ROOT / "docs" / "research_notes" / "document_segmentation_report.md",
    ]
    before_hashes = {p: _sha256(p) for p in protected_files}
    raw_txt_files = sorted((PROJECT_ROOT / "data" / "raw" / "txt").glob("*.txt"))
    assert len(raw_txt_files) == 80
    raw_before = {p: _sha256(p) for p in raw_txt_files}

    run_segmentation_validation(PROJECT_ROOT, write_outputs=True)

    for p, digest in before_hashes.items():
        assert _sha256(p) == digest, f"Protected file was modified: {p}"
    for p, digest in raw_before.items():
        assert _sha256(p) == digest, f"Raw TXT file was modified: {p}"


def test_validation_outputs_exist_and_cover_all_114_units() -> None:
    """Verify JSON, CSV, and Markdown report exist and cover all 114 units."""
    json_path = PROJECT_ROOT / "data" / "processed" / "segmentation_validation.json"
    csv_path = PROJECT_ROOT / "data" / "processed" / "segmentation_validation.csv"
    report_path = (
        PROJECT_ROOT / "docs" / "research_notes" / "segmentation_validation_report.md"
    )

    assert json_path.exists()
    assert csv_path.exists()
    assert report_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    unit_validations = payload["unit_validations"]
    assert len(unit_validations) == 114

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 114

    # Verify status sum equals 114
    counts = payload["summary"]["validation_status_counts"]
    assert sum(counts.values()) == 114
    assert counts["VALIDATED"] == 63
    assert counts["VALIDATED_WITH_LIMITATION"] == 40
    assert counts["NEEDS_REVISION"] == 11
    assert counts["UNRESOLVED"] == 0

    # Verify automated structural checks are separated and complete
    auto_checks = payload["automated_structural_checks"]
    assert auto_checks["all_80_documents_accounted_for"] is True
    assert auto_checks["no_duplicate_unit_ids"] is True
    assert auto_checks["all_units_within_char_bounds"] is True
    assert auto_checks["all_units_have_valid_taxonomy_code"] is True

    # Verify excluded documents include DOC-034 as UNRESOLVED
    excluded_by_id = {
        d["document_id"]: d for d in payload["excluded_document_validations"]
    }
    assert excluded_by_id["DOC-034"]["validation_status"] == "UNRESOLVED"
    assert excluded_by_id["DOC-005"]["validation_status"] == "VALIDATED"


def test_entity_distinction_framework_and_special_audit_cases() -> None:
    """Verify the 6 semantic entity definitions and 6 special audit cases are complete."""
    payload = json.loads(
        (PROJECT_ROOT / "data" / "processed" / "segmentation_validation.json").read_text(
            encoding="utf-8"
        )
    )
    framework = payload["entity_distinction_framework"]
    expected_entities = {
        "competition_event",
        "competition_branch",
        "competition_category",
        "competition_unit",
        "event_level_general_information",
        "branch_specific_technical_guide",
    }
    assert set(framework.keys()) == expected_entities
    for key, val in framework.items():
        assert val["definition"]
        assert len(val["corpus_examples"]) >= 2

    special = payload["special_audit_cases"]
    expected_cases = {
        "DOC-047",
        "DOC-015",
        "DOC-009",
        "FIKSI_AND_LKS",
        "DOC-008",
        "DOC-054_AND_DOC-073",
    }
    assert expected_cases.issubset(set(special.keys()))


def test_unit_validation_fields_and_targeted_statuses() -> None:
    """Check that every unit has valid status, entity type, evidence, and expected targeted audit status."""
    payload = json.loads(
        (PROJECT_ROOT / "data" / "processed" / "segmentation_validation.json").read_text(
            encoding="utf-8"
        )
    )
    by_uid = {u["branch_unit_id"]: u for u in payload["unit_validations"]}

    for uid, u in by_uid.items():
        assert u["validation_status"] in VALID_STATUSES
        assert u["semantic_entity_type"] in SEMANTIC_ENTITY_TYPES
        assert isinstance(u["has_accurate_identity"], bool)
        assert isinstance(u["has_relevant_content"], bool)
        assert isinstance(u["no_lost_requirements_from_truncation"], bool)
        assert isinstance(u["no_cross_branch_contamination"], bool)
        assert isinstance(u["has_explainable_structural_boundary"], bool)
        assert len(u["validation_reason"].strip()) > 20
        assert len(u["evidence_text"].strip()) > 5
        assert len(u["recommended_correction"].strip()) > 10

    # Targeted audit assertions
    assert by_uid["DOC-047-BU-04"]["validation_status"] == "NEEDS_REVISION"
    assert by_uid["DOC-047-BU-01"]["validation_status"] == "VALIDATED_WITH_LIMITATION"
    assert by_uid["DOC-009-BU-01"]["validation_status"] == "NEEDS_REVISION"
    assert by_uid["DOC-009-BU-02"]["validation_status"] == "VALIDATED_WITH_LIMITATION"
    assert by_uid["DOC-015-BU-01"]["validation_status"] == "VALIDATED_WITH_LIMITATION"
    assert by_uid["DOC-008-BU-01"]["validation_status"] == "VALIDATED_WITH_LIMITATION"
    assert by_uid["DOC-008-BU-02"]["validation_status"] == "VALIDATED_WITH_LIMITATION"
    assert by_uid["DOC-054-BU-01"]["validation_status"] == "VALIDATED_WITH_LIMITATION"
    assert by_uid["DOC-073-BU-01"]["validation_status"] == "VALIDATED_WITH_LIMITATION"
    assert by_uid["DOC-062-BU-01"]["validation_status"] == "VALIDATED_WITH_LIMITATION"
    assert by_uid["DOC-062-BU-02"]["validation_status"] == "NEEDS_REVISION"
    assert by_uid["DOC-067-BU-02"]["validation_status"] == "NEEDS_REVISION"
    assert by_uid["DOC-061-BU-01"]["validation_status"] == "NEEDS_REVISION"


def test_uncovered_char_spans_completeness_and_classifications() -> None:
    """Verify uncovered spans are accurately classified and capture critical uncovered content."""
    payload = json.loads(
        (PROJECT_ROOT / "data" / "processed" / "segmentation_validation.json").read_text(
            encoding="utf-8"
        )
    )
    spans = payload["uncovered_char_spans"]
    assert len(spans) == 40

    for sp in spans:
        assert sp["span_classification"] in SPAN_CLASSIFICATIONS
        assert 0 <= sp["start_char"] < sp["end_char"]
        assert sp["char_length"] == sp["end_char"] - sp["start_char"]
        assert isinstance(sp["contains_important_info"], bool)
        assert sp["description"]

    doc009_spans = [s for s in spans if s["document_id"] == "DOC-009"]
    # Verify DOC-009 truncated branch content (3050..3135) and shared registration (46547..48658)
    assert any(
        s["start_char"] == 3050
        and s["end_char"] == 3135
        and s["span_classification"] == "truncated_branch_content"
        and s["contains_important_info"] is True
        for s in doc009_spans
    )
    assert any(
        s["start_char"] == 46547
        and s["end_char"] == 48658
        and s["span_classification"] == "shared_registration_or_payment_rules"
        and s["contains_important_info"] is True
        for s in doc009_spans
    )
