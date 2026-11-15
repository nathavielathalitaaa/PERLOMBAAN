"""Automated tests for Stage 4.3: Baseline Evaluation & Corpus Expansion Readiness."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from src.requirement_extraction import (
    READINESS_DECISION_STATUSES,
    evaluate_corpus_expansion_readiness,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage4_3_does_not_modify_previous_outputs_or_expand_extraction() -> None:
    """Ensure Stage 1, 2, 3, 3.1, 4.0, 4.1, and 4.2 outputs and raw TXT files remain untouched."""
    protected_files = [
        PROJECT_ROOT / "data" / "processed" / "document_inventory.json",
        PROJECT_ROOT / "data" / "processed" / "document_inventory.csv",
        PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.json",
        PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.csv",
        PROJECT_ROOT / "data" / "processed" / "competition_branch_units.json",
        PROJECT_ROOT / "data" / "processed" / "competition_branch_units.csv",
        PROJECT_ROOT / "data" / "processed" / "segmentation_validation.json",
        PROJECT_ROOT / "data" / "processed" / "segmentation_validation.csv",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "competition_requirements_stage4_0_baseline.json",
        PROJECT_ROOT
        / "data"
        / "processed"
        / "competition_requirements_stage4_0_baseline.csv",
        PROJECT_ROOT / "data" / "processed" / "requirement_extraction_audit.json",
        PROJECT_ROOT / "data" / "processed" / "competition_requirements.json",
        PROJECT_ROOT / "data" / "processed" / "competition_requirements.csv",
        PROJECT_ROOT / "data" / "processed" / "requirement_extraction_evaluation.json",
    ]
    before_hashes = {p: _sha256(p) for p in protected_files}

    payload = evaluate_corpus_expansion_readiness(PROJECT_ROOT, write_outputs=True)

    for p, digest in before_hashes.items():
        assert _sha256(p) == digest, f"Protected file was modified: {p}"

    # Verify extraction was NOT expanded beyond the 3 representative documents
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    assert req_payload["summary"]["representative_documents_processed"] == 3
    assert req_payload["summary"]["branch_units_processed"] == 8
    assert payload["1_baseline_evaluation_audit"]["evaluated_documents"] == [
        "DOC-001",
        "DOC-024",
        "DOC-009",
    ]


def test_readiness_outputs_and_separation_of_automated_vs_semantic_validation() -> None:
    """Verify readiness JSON, plan CSV, and Markdown report exist and separate automated vs semantic checks."""
    json_path = PROJECT_ROOT / "data" / "processed" / "corpus_expansion_readiness.json"
    csv_path = PROJECT_ROOT / "data" / "processed" / "corpus_expansion_plan.csv"
    report_path = (
        PROJECT_ROOT
        / "docs"
        / "research_notes"
        / "corpus_expansion_readiness_report.md"
    )

    assert json_path.exists()
    assert csv_path.exists()
    assert report_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["overall_readiness_status"] in READINESS_DECISION_STATUSES
    assert payload["overall_readiness_status"] == "NEEDS_MORE_REFINEMENT"
    assert payload["conditional_restricted_status"] == "READY_WITH_RESTRICTIONS"

    sep = payload["separation_of_automated_vs_semantic_validation"]
    auto_checks = sep["automated_integrity_checks"]
    sem_checks = sep["semantic_and_methodological_validation"]

    # All automated checks on the 3 calibrated documents pass
    assert all(auto_checks.values())

    # Semantic & methodological checks honestly flag in-sample calibration and unrepresented types
    assert sem_checks["evaluation_set_is_independent_held_out"] is False
    assert sem_checks["extractor_has_generic_unseen_document_parser"] is False
    assert sem_checks["all_corpus_multi_branch_types_represented_in_eval"] is False
    assert sem_checks["all_corpus_document_types_represented_in_eval"] is False
    assert sem_checks["record_count_equals_requirement_completeness"] is False


def test_document_variation_and_coverage_completeness() -> None:
    """Verify all 80 documents and 114 branch units are accounted for in variation analysis and expansion plan."""
    json_path = PROJECT_ROOT / "data" / "processed" / "corpus_expansion_readiness.json"
    csv_path = PROJECT_ROOT / "data" / "processed" / "corpus_expansion_plan.csv"
    inv_path = (
        PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.json"
    )
    units_path = (
        PROJECT_ROOT / "data" / "processed" / "competition_branch_units.json"
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    inv_payload = json.loads(inv_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))

    # 114 branch units + 4 unsegmented documents = 118 plan rows
    assert len(csv_rows) == 118
    assert (
        len(payload["6_staged_expansion_strategy"]["expansion_plan_rows"]) == 118
    )

    all_doc_ids = {d["document_id"] for d in inv_payload["documents"]}
    planned_doc_ids = {r["document_id"] for r in csv_rows}
    assert planned_doc_ids == all_doc_ids

    all_unit_ids = {u["branch_unit_id"] for u in units_payload["branch_units"]}
    planned_unit_ids = {
        r["branch_unit_id"] for r in csv_rows if r["branch_unit_id"] != "NONE"
    }
    assert planned_unit_ids == all_unit_ids

    # Check coverage metrics
    cov = payload["4_extraction_coverage_evaluation"]["unit_evaluation_coverage"]
    assert cov["total_branch_units_in_corpus"] == 114
    assert cov["evaluated_branch_units_count"] == 8
    assert cov["unevaluated_branch_units_count"] == 106

    # Check unrepresented groups are explicitly identified
    var_eval = payload["2_document_variation_evaluation"]
    assert (
        var_eval["by_multi_branch_type_units"]["composite_branch_competition"][
            "evaluated_count"
        ]
        == 0
    )
    assert (
        var_eval["by_multi_branch_type_units"][
            "primary_branch_with_multi_event_intro"
        ]["evaluated_count"]
        == 0
    )
    assert (
        var_eval["by_macro_document_category_documents"][
            "dokumen_ketentuan_dan_petunjuk_teknis"
        ]["evaluated_count"]
        == 0
    )


def test_idempotent_readiness_rerun() -> None:
    """Verify running evaluate_corpus_expansion_readiness multiple times produces identical output."""
    first = evaluate_corpus_expansion_readiness(PROJECT_ROOT, write_outputs=True)
    second = evaluate_corpus_expansion_readiness(PROJECT_ROOT, write_outputs=True)
    assert first == second
