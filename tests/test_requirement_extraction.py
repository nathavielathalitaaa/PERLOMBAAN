"""Automated semantic, regression, and integrity tests for Stage 4.2 Requirement Extraction."""

from __future__ import annotations

import csv
import hashlib
import json
import pytest
from pathlib import Path

from src.requirement_extraction import (
    CONFIDENCE_LEVELS,
    EVIDENCE_TYPES,
    REQUIREMENT_CATEGORIES,
    REQUIREMENT_SUBCATEGORIES,
    STATEMENT_NATURES,
    VALIDATION_STATUSES,
    apply_term_normalization,
    classify_requirement_clause,
    evaluate_requirement_extraction,
    extract_exception_or_condition,
    extract_representative_requirements,
    is_non_requirement_background,
    verify_description_grounded_in_evidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_previous_stage_outputs_and_raw_files_untouched() -> None:
    """Ensure Stage 1, 2, 3, Stage 4.0 baseline, Stage 4.1 audit, and raw TXT files are not modified."""
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
    ]
    before_hashes = {p: _sha256(p) for p in protected_files}

    extract_representative_requirements(PROJECT_ROOT, write_outputs=True)
    evaluate_requirement_extraction(PROJECT_ROOT, write_output=True)

    for p, digest in before_hashes.items():
        assert _sha256(p) == digest, f"Protected file was modified: {p}"


def test_document_and_branch_unit_referential_integrity() -> None:
    """Verify valid linkage between extracted entities, documents, branch units, and Stage 3 validation."""
    req_path = PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
    units_path = PROJECT_ROOT / "data" / "processed" / "competition_branch_units.json"
    seg_val_path = PROJECT_ROOT / "data" / "processed" / "segmentation_validation.json"

    req_payload = json.loads(req_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    seg_val_payload = json.loads(seg_val_path.read_text(encoding="utf-8"))

    units_by_id = {u["branch_unit_id"]: u for u in units_payload["branch_units"]}
    vals_by_id = {u["branch_unit_id"]: u for u in seg_val_payload["unit_validations"]}

    rep_docs = req_payload["representative_documents"]
    assert len(rep_docs) == 3
    assert [d["document_id"] for d in rep_docs] == ["DOC-001", "DOC-024", "DOC-009"]

    requirements = req_payload["requirements"]
    assert len(requirements) == 145

    for r in requirements:
        uid = r["branch_unit_id"]
        doc_id = r["document_id"]
        assert uid in units_by_id, f"Unknown branch_unit_id: {uid}"
        assert units_by_id[uid]["document_id"] == doc_id
        assert uid in vals_by_id
        assert r["unit_segmentation_status"] == vals_by_id[uid]["validation_status"]
        assert r["record_type"] == "requirement"


def test_evidence_text_presence_and_verbatim_match() -> None:
    """Verify every requirement, information item, and review item has verbatim evidence matching raw_text."""
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    inv_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.json"
        ).read_text(encoding="utf-8")
    )
    docs_by_id = {d["document_id"]: d for d in inv_payload["documents"]}
    raw_dir = PROJECT_ROOT / "data" / "raw" / "txt"
    raw_texts = {
        doc_id: (raw_dir / docs_by_id[doc_id]["file_name"]).read_text(encoding="utf-8")
        for doc_id in ("DOC-001", "DOC-024", "DOC-009")
    }

    for collection_key, id_key in (
        ("requirements", "requirement_id"),
        ("information_items", "info_id"),
        ("review_items", "review_id"),
    ):
        for r in req_payload[collection_key]:
            ev = r["evidence_text"]
            assert isinstance(ev, str) and len(ev.strip()) > 0
            raw_text = raw_texts[r["document_id"]]
            s = r["source_char_start"]
            e = r["source_char_end"]
            assert raw_text[s:e] == ev, (
                f"Verbatim mismatch on {r[id_key]}: expected {ev!r}, got {raw_text[s:e]!r}"
            )


def test_character_range_validity_and_unit_boundary_compliance() -> None:
    """Verify character ranges are valid and enforce strict branch unit isolation."""
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    units_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_branch_units.json"
        ).read_text(encoding="utf-8")
    )
    units_by_id = {u["branch_unit_id"]: u for u in units_payload["branch_units"]}

    for r in req_payload["requirements"]:
        s = r["source_char_start"]
        e = r["source_char_end"]
        assert isinstance(s, int) and isinstance(e, int)
        assert 0 <= s < e
        assert isinstance(r["source_page"], int) and r["source_page"] >= 1

        u = units_by_id[r["branch_unit_id"]]
        u_start, u_end = int(u["start_char"]), int(u["end_char"])

        if r["within_strict_unit_bounds"]:
            assert u_start <= s and e <= u_end, (
                f"Requirement {r['requirement_id']} claims within_strict_unit_bounds "
                f"but {s}..{e} is outside {u_start}..{u_end}"
            )
        else:
            # Only DOC-009 audited uncovered spans (3157..3765 or 46547..48658) are allowed outside strict unit bounds
            assert r["document_id"] == "DOC-009"
            assert (3050 <= s < e <= 3800) or (46547 <= s < e <= 48658)
            assert r["validation_status"] in (
                "VALIDATED_WITH_SEGMENTATION_LIMITATION",
                "NEEDS_REVIEW",
            )


def _load_raw_text(doc_id: str) -> str:
    inv_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.json"
        ).read_text(encoding="utf-8")
    )
    docs_by_id = {d["document_id"]: d for d in inv_payload["documents"]}
    return (
        PROJECT_ROOT / "data" / "raw" / "txt" / docs_by_id[doc_id]["file_name"]
    ).read_text(encoding="utf-8")


def test_1_false_positive_filtering_with_real_doc009_example() -> None:
    """Test Scenario 1: False positive filtering (WHO 74% mortality & Pharmacopeia background in DOC-009)."""
    raw_009 = _load_raw_text("DOC-009")
    who_background_span = raw_009[153:856]

    # 1. Verify rule-based background detector flags the real DOC-009 intro narrative as non-requirement
    assert is_non_requirement_background(
        who_background_span, "Latar Belakang Pharmacopeia 2026"
    )
    # Verify real requirement in DOC-009 is NOT flagged as background
    real_rule_span = raw_009[3769:3956]
    assert not is_non_requirement_background(
        real_rule_span, "Ketentuan Umum Essay Competition"
    )

    # 2. Verify in competition_requirements.json that WHO 74% mortality is in information_items, NOT in requirements
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    for r in req_payload["requirements"]:
        assert "74% kematian" not in r["evidence_text"]
        assert r["statement_nature"] in STATEMENT_NATURES

    info_ids = {i["info_id"]: i for i in req_payload["information_items"]}
    assert "INFO-DOC009-BU01-001" in info_ids
    assert "74% kematian" in info_ids["INFO-DOC009-BU01-001"]["evidence_text"]
    assert info_ids["INFO-DOC009-BU01-001"]["record_type"] == "information"


def test_2_known_false_negatives_resolved_across_doc001_doc024_doc009() -> None:
    """Test Scenario 2: Verify all 7 false-negative groups identified in Stage 4.1 Audit are now extracted."""
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    reqs_by_unit_and_name = {
        (r["branch_unit_id"], r["requirement_name"]): r
        for r in req_payload["requirements"]
    }

    # FN-001 & FN-002 (DOC-001): Coaching Program (Section 7) and Verified Participant criteria (Section 10)
    assert (
        "DOC-001-BU-01",
        "structured_coaching_program_and_checkins",
    ) in reqs_by_unit_and_name
    assert ("DOC-001-BU-01", "verified_participant_criteria") in reqs_by_unit_and_name

    # FN-003, FN-004, FN-005 (DOC-024): Multiple submissions & non-refundable fee, Subthemes across all 3 branches, Copyright/publication rights
    assert (
        "DOC-024-BU-01",
        "non_refundable_fee_and_multiple_submission_payment",
    ) in reqs_by_unit_and_name
    assert (
        "DOC-024-BU-02",
        "multiple_bmc_submissions_and_non_refundable_fee",
    ) in reqs_by_unit_and_name
    assert (
        "DOC-024-BU-01",
        "essay_main_theme_and_seven_subthemes",
    ) in reqs_by_unit_and_name
    assert (
        "DOC-024-BU-02",
        "bmc_main_theme_and_six_subthemes",
    ) in reqs_by_unit_and_name
    assert (
        "DOC-024-BU-03",
        "poster_main_theme_and_six_subthemes",
    ) in reqs_by_unit_and_name
    assert (
        "DOC-024-BU-03",
        "poster_copyright_ownership_and_publication_authority",
    ) in reqs_by_unit_and_name

    # FN-006 & FN-007 (DOC-009): School delegation quota, Cross-branch participation rule, and Offline Final quarantine/dress-code/no-school-logo
    assert (
        "DOC-009-BU-01",
        "multiple_teams_per_school_allowed",
    ) in reqs_by_unit_and_name
    for uid in ("DOC-009-BU-01", "DOC-009-BU-02", "DOC-009-BU-03"):
        assert (
            uid,
            "cross_branch_participation_restriction_with_video_exception",
        ) in reqs_by_unit_and_name
    assert (
        "DOC-009-BU-04",
        "allowed_one_other_branch_participation",
    ) in reqs_by_unit_and_name
    assert (
        "DOC-009-BU-01",
        "offline_final_quarantine_dress_code_seminar_and_attendance_rules",
    ) in reqs_by_unit_and_name
    assert (
        "DOC-009-BU-02",
        "offline_final_quarantine_dress_code_and_school_attribute_prohibition",
    ) in reqs_by_unit_and_name
    assert (
        "DOC-009-BU-03",
        "offline_final_quarantine_dress_code_and_school_attribute_prohibition",
    ) in reqs_by_unit_and_name


def test_3_category_classification_accuracy_with_real_doc024_poster_specs() -> None:
    """Test Scenario 3: Prevent category misclassification (e.g., poster format/resolution specs in DOC-024-BU-03)."""
    raw_024 = _load_raw_text("DOC-024")

    # Real span from DOC-024-BU-03 (20277..20550): JPG, JPEG, PNG, 300 ppi, A4, RGB
    poster_format_span = raw_024[20277:20550]
    cat, subcat, nature = classify_requirement_clause(
        poster_format_span, "Ketentuan Desain Karya Cabang Poster"
    )
    assert cat == "technical_and_general_rules"
    assert subcat == "media_and_file_specification"
    assert nature == "official_rule"

    # Real deliverable span from DOC-024-BU-03 (18222..19418): sending digital poster via registration form
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    bu03_reqs = {
        r["requirement_name"]: r
        for r in req_payload["requirements"]
        if r["branch_unit_id"] == "DOC-024-BU-03"
    }
    assert (
        bu03_reqs["digital_poster_submission_and_no_ig_upload_rule"][
            "requirement_category"
        ]
        == "deliverables"
    )
    assert (
        bu03_reqs["poster_file_format_resolution_dimensions_and_color_mode"][
            "requirement_category"
        ]
        == "technical_and_general_rules"
    )


def test_4_multi_sentence_requirements_preserved_intact() -> None:
    """Test Scenario 4: Verify multi-sentence requirements in DOC-001, DOC-024, and DOC-009 are preserved intact."""
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    reqs_by_id = {r["requirement_id"]: r for r in req_payload["requirements"]}

    # DOC-001-BU-01: Live demo requirement consists of 3 connected sentences ("Live demo requirement. Your prototype must actually run... Without a working demo, a team is not eligible for prizes.")
    live_demo_req = reqs_by_id["REQ-DOC001-BU01-014"]
    assert "Live demo requirement." in live_demo_req["evidence_text"]
    assert "Slides, \nmockups, or recorded videos alone do not qualify." in live_demo_req["evidence_text"]
    assert "Without a working demo, a team is not \neligible for prizes." in live_demo_req["evidence_text"]

    # DOC-024-BU-01: Full 6-part essay structure (7125..7535) is preserved intact instead of truncated at line 1
    essay_struct_req = reqs_by_id["REQ-DOC024-BU01-010"]
    assert "1.Cover" in essay_struct_req["evidence_text"]
    assert "6.Lampiran" in essay_struct_req["evidence_text"]
    assert "Lembar Orisinalitas Karya" in essay_struct_req["evidence_text"]

    # DOC-009-BU-01: Full 3-file preliminary submission rule (12079..12971) is preserved intact
    doc009_sub_req = reqs_by_id["REQ-DOC009-BU01-011"]
    assert "5.File dikirim melalui Google Forms" in doc009_sub_req["evidence_text"]
    assert "SuratOrisinalitasPharmacopeia2026" in doc009_sub_req["evidence_text"]
    assert "maksimal 25%" in doc009_sub_req["evidence_text"]


def test_5_requirements_with_exceptions_and_conditions() -> None:
    """Test Scenario 5: Verify exception and conditional clauses are accurately extracted and preserved."""
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    reqs_with_exc = [
        r
        for r in req_payload["requirements"]
        if r["exception_or_condition"] != "NONE"
    ]
    assert len(reqs_with_exc) >= 15

    reqs_by_id = {r["requirement_id"]: r for r in req_payload["requirements"]}

    # DOC-009-BU-01: Cross-branch restriction with explicit Video Campaign exception
    r_cross = reqs_by_id["REQ-DOC009-BU01-004"]
    assert "kecuali Video Campaign Competition" in r_cross["exception_or_condition"]

    # DOC-001-BU-01: Live demo requirement with prize ineligibility condition
    r_demo = reqs_by_id["REQ-DOC001-BU01-014"]
    assert "Without a working demo" in r_demo["exception_or_condition"]

    # DOC-024-BU-01: Page limit excluding cover, references, originality sheet, and attachments
    r_fmt = reqs_by_id["REQ-DOC024-BU01-016"]
    assert "tidak termasuk cover" in r_fmt["exception_or_condition"].lower()


def test_6_interrelated_requirements_and_review_linkage() -> None:
    """Test Scenario 6: Verify interrelated requirements (`related_requirement_ids`) resolve cleanly."""
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    req_ids = {r["requirement_id"] for r in req_payload["requirements"]}
    rev_ids = {rv["review_id"] for rv in req_payload["review_items"]}
    valid_target_ids = req_ids | rev_ids

    linked_reqs = [
        r for r in req_payload["requirements"] if len(r["related_requirement_ids"]) > 0
    ]
    assert len(linked_reqs) >= 35

    for r in linked_reqs:
        for target_id in r["related_requirement_ids"]:
            assert target_id in valid_target_ids, (
                f"Broken related_requirement_ids link on {r['requirement_id']}: {target_id}"
            )
            assert target_id != r["requirement_id"]

    # Verify bidirectional/semantic linkage in DOC-001: Two-step registration Steps 1 & 2 and Review Item REV-DOC001-BU01-001
    reqs_by_id = {r["requirement_id"]: r for r in req_payload["requirements"]}
    assert "REQ-DOC001-BU01-007" in reqs_by_id["REQ-DOC001-BU01-006"]["related_requirement_ids"]
    assert "REV-DOC001-BU01-001" in reqs_by_id["REQ-DOC001-BU01-006"]["related_requirement_ids"]


def test_7_description_to_evidence_grounding_verification() -> None:
    """Test Scenario 7: Verify 100% of extracted requirements pass grounding check and ungrounded claims are rejected."""
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    for r in req_payload["requirements"]:
        ok, ungrounded = verify_description_grounded_in_evidence(
            r["requirement_description"],
            r["evidence_text"],
            r["evidence_type"],
        )
        assert ok, (
            f"Requirement {r['requirement_id']} has ungrounded claims {ungrounded}: "
            f"desc={r['requirement_description']!r} vs ev={r['evidence_text']!r}"
        )

    # Negative regression test: Stage 4.0 truncated evidence vs multi-claim description MUST fail grounding check
    truncated_ev = "Ketentuan Penulisan Karya Cabang BMC\n\nCustomer Segments\n\nSiapa saja yang menjadi konsumen bisnis kamu"
    ungrounded_desc = "Karya BMC wajib memuat 9 elemen dan biaya pendaftaran Rp 45.000 dengan bobot 25% di https://bit.ly/fake"
    ok_neg, missing_claims = verify_description_grounded_in_evidence(
        ungrounded_desc, truncated_ev, "explicit"
    )
    assert not ok_neg
    assert "PERCENTAGE:25%" in missing_claims
    assert "CURRENCY:Rp45.000" in missing_claims
    assert "URL:https://bit.ly/fake" in missing_claims
    assert "NUMBER:9" in missing_claims


def test_8_missing_information_handled_in_extraction_gaps_only() -> None:
    """Test Scenario 8: Verify missing attributes (`NOT_STATED`) are stored in `extraction_gaps` and NEVER in `requirements`."""
    req_payload = json.loads(
        (
            PROJECT_ROOT / "data" / "processed" / "competition_requirements.json"
        ).read_text(encoding="utf-8")
    )
    reqs = req_payload["requirements"]
    gaps = req_payload["extraction_gaps"]

    # Zero NOT_STATED records inside active `requirements`
    for r in reqs:
        assert r["validation_status"] != "NOT_STATED"
        assert r["requirement_description"] != "NOT_STATED"
        assert r["evidence_type"] != "not_stated"

    # Verify all 14 expected extraction gaps are recorded in `extraction_gaps`
    assert len(gaps) == 14
    age_gaps = [g for g in gaps if g["missing_attribute_name"] == "age_limit"]
    assert len(age_gaps) == 8
    for g in age_gaps:
        assert g["gap_status"] == "NOT_STATED"
        assert g["record_type"] == "extraction_gap"
        assert len(g["inspected_sections"]) >= 1

    # Verify unstated rubric percentage weights in DOC-009 (BU-01, BU-03, BU-04) are recorded in extraction_gaps
    weight_gaps = [
        g
        for g in gaps
        if g["missing_attribute_name"] == "rubric_aspect_percentage_weights"
    ]
    assert len(weight_gaps) == 3


def test_9_idempotent_rerun_and_quality_evaluation_metrics() -> None:
    """Test Scenario 9: Verify idempotent re-execution and validate Precision/Recall/F1 quality evaluation output."""
    first_payload = extract_representative_requirements(PROJECT_ROOT, write_outputs=True)
    second_payload = extract_representative_requirements(
        PROJECT_ROOT, write_outputs=True
    )
    assert first_payload == second_payload

    first_eval = evaluate_requirement_extraction(PROJECT_ROOT, write_output=True)
    second_eval = evaluate_requirement_extraction(PROJECT_ROOT, write_output=True)
    assert first_eval == second_eval

    # Check schema completeness across JSON, CSV, and evaluation artifact
    csv_path = PROJECT_ROOT / "data" / "processed" / "competition_requirements.csv"
    eval_path = (
        PROJECT_ROOT / "data" / "processed" / "requirement_extraction_evaluation.json"
    )
    refinement_report_path = (
        PROJECT_ROOT
        / "docs"
        / "research_notes"
        / "requirement_extraction_refinement_report.md"
    )
    assert csv_path.exists()
    assert eval_path.exists()
    assert refinement_report_path.exists()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    assert len(csv_rows) == len(first_payload["requirements"])

    # Verify Stage 4.2 evaluation metrics per category and overall
    s42_eval = first_eval["stage4_2_refined_evaluation"]
    assert s42_eval["overall_micro"]["precision"] == 1.0
    assert s42_eval["overall_micro"]["recall"] >= 0.98
    assert s42_eval["overall_micro"]["f1_score"] >= 0.99
    assert (
        first_eval["before_vs_after_comparison"]["overall_micro"][
            "strict_f1_improvement"
        ]
        > 0.60
    )
    for cat in REQUIREMENT_CATEGORIES:
        cat_metrics = s42_eval["per_category"][cat]
        assert cat_metrics["precision"] == 1.0
        assert cat_metrics["f1_score"] >= 0.94
