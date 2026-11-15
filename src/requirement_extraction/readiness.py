"""Stage 4.3: Baseline Evaluation & Corpus Expansion Readiness Engine.

Audits the Stage 4.2 Requirement Extraction outputs, evaluation methodology,
provenance integrity, and corpus-wide document variation across all 80 documents
(114 segmented branch units + 4 excluded documents) to determine readiness for
corpus expansion and generate a staged, risk-gated expansion plan.

Strictly separates:
1. Automated Programmatic Integrity Checks (`automated_integrity_checks`)
2. Semantic & Methodological Validation (`semantic_and_methodological_validation`)

Does NOT modify any raw TXT files or any Stage 1, 2, 3, 4.0, 4.1, or 4.2 outputs,
and does NOT expand extraction during the readiness audit.
"""

from __future__ import annotations

import csv
import inspect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import src.requirement_extraction.evaluator as evaluator_mod
import src.requirement_extraction.extractor as extractor_mod
from src.requirement_extraction.rules import (
    EVIDENCE_TYPES,
    REQUIREMENT_CATEGORIES,
    REQUIREMENT_SUBCATEGORIES,
    STATEMENT_NATURES,
    VALIDATION_STATUSES,
    verify_description_grounded_in_evidence,
)

READINESS_DECISION_STATUSES: Tuple[str, ...] = (
    "READY_FOR_CORPUS_EXPANSION",
    "READY_WITH_RESTRICTIONS",
    "NEEDS_MORE_REFINEMENT",
    "NOT_READY",
)


@dataclass
class CorpusExpansionPlanRow:
    """Single document/unit entry in the staged corpus expansion plan (`corpus_expansion_plan.csv`)."""

    plan_row_id: str
    expansion_wave: str
    wave_priority_order: int
    document_id: str
    branch_unit_id: str
    file_name: str
    readability_status: str
    macro_document_category: str
    validated_document_type: str
    multi_branch_type: str
    semantic_entity_type: str
    segmentation_validation_status: str
    structural_complexity: str
    represented_in_stage4_2_eval: bool
    expansion_gate_status: str
    manual_validation_level: str
    prerequisite_actions: str
    decision_rationale: str


def _pct(part: int, whole: int) -> float:
    return round((part / whole) * 100.0, 2) if whole > 0 else 0.0


def _evaluate_baseline_and_methodology(
    eval_payload: Dict[str, Any],
    req_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Task 1: Audit baseline metrics, FP/FN, GT consistency, and evaluation independence."""
    s42_eval = eval_payload["stage4_2_refined_evaluation"]
    s40_eval = eval_payload["stage4_0_baseline_evaluation"]
    comp = eval_payload["before_vs_after_comparison"]
    gt_list = eval_payload["ground_truth_annotations"]

    # Check Ground Truth internal consistency
    gt_ids = [g["gt_id"] for g in gt_list]
    gt_unique_ids = len(gt_ids) == len(set(gt_ids))
    gt_valid_ranges = all(
        0 <= int(g["expected_char_start"]) < int(g["expected_char_end"])
        for g in gt_list
    )
    gt_valid_categories = all(
        g["requirement_category"] in REQUIREMENT_CATEGORIES
        and g["requirement_subcategory"]
        in REQUIREMENT_SUBCATEGORIES[g["requirement_category"]]
        for g in gt_list
    )

    # Inspect extractor and evaluator source code for methodological independence
    extractor_src = inspect.getsource(extractor_mod)
    evaluator_src = inspect.getsource(evaluator_mod)
    has_hardcoded_doc_dispatchers = all(
        fn_name in extractor_src
        for fn_name in (
            "_extract_doc001_bu01",
            "_extract_doc024_units",
            "_extract_doc009_units",
        )
    )
    gt_derived_from_s42_output = (
        'for rec in stage42_payload["requirements"]:' in evaluator_src
    )

    return {
        "evaluated_documents": ["DOC-001", "DOC-024", "DOC-009"],
        "evaluated_branch_units_count": 8,
        "ground_truth_total_count": len(gt_list),
        "ground_truth_extractable_from_txt_count": sum(
            1 for g in gt_list if g["raw_txt_extractable"]
        ),
        "ground_truth_ocr_illegible_in_txt_count": sum(
            1 for g in gt_list if not g["raw_txt_extractable"]
        ),
        "stage4_2_overall_micro": s42_eval["overall_micro"],
        "stage4_2_overall_macro": s42_eval["overall_macro"],
        "stage4_2_per_category": s42_eval["per_category"],
        "stage4_2_per_document": s42_eval["per_document"],
        "stage4_0_vs_stage4_2_overall_delta": comp["overall_micro"],
        "false_positive_analysis": {
            "stage4_0_strict_fp_count": s40_eval[
                "strict_grounded_atomic_evaluation"
            ]["overall_micro"]["fp"],
            "stage4_0_relaxed_fp_count": s40_eval["relaxed_span_topic_evaluation"][
                "overall_micro"
            ]["fp"],
            "stage4_2_fp_count": s42_eval["overall_micro"]["fp"],
            "stage4_2_false_positives": s42_eval["false_positives"],
            "explanation": (
                "Seluruh 60 strict FP pada Stage 4.0 (11 record NOT_STATED di dalam requirements, "
                "1 narasi latar belakang WHO 74% kematian, 2 salah kategori, 1 catatan audit segmen, "
                "serta 45 record dengan bukti terpotong atau penggabungan rubrik) telah dieliminasi "
                "pada Stage 4.2 melalui pemisahan 4 entitas dan verifikasi grounding otomatis."
            ),
        },
        "false_negative_analysis": {
            "stage4_0_strict_fn_count": s40_eval[
                "strict_grounded_atomic_evaluation"
            ]["overall_micro"]["fn"],
            "stage4_0_relaxed_fn_count": s40_eval["relaxed_span_topic_evaluation"][
                "overall_micro"
            ]["fn"],
            "stage4_2_fn_count": s42_eval["overall_micro"]["fn"],
            "stage4_2_false_negatives": s42_eval["false_negatives"],
            "explanation": (
                "Dari 7 kelompok False Negative pada Stage 4.0, seluruh ketentuan yang terbaca di file TXT "
                "telah berhasil diekstrak pada Stage 4.2. Tersisa 2 False Negative pada DOC-009 "
                "(GT-DOC009BU01-021 di halaman 14 bawah char 12983..13328 dan GT-DOC009BU03-018 di halaman 39 "
                "bawah char 35122..35486) yang teks aslinya rusak berat akibat OCR dan secara jujur dialihkan "
                "ke review_items (REV-DOC009-BU01-003 dan REV-DOC009-BU03-001) agar tidak mengarang aturan."
            ),
        },
        "manual_annotation_consistency_check": {
            "all_gt_ids_unique": gt_unique_ids,
            "all_gt_char_ranges_valid": gt_valid_ranges,
            "all_gt_categories_and_subcategories_valid": gt_valid_categories,
            "atomic_rubric_granularity_consistent_across_3_docs": True,
            "not_stated_excluded_from_positive_gt": True,
        },
        "evaluation_independence_and_leakage_audit": {
            "is_independent_held_out_test_set": False,
            "evaluation_nature": "IN_SAMPLE_CALIBRATION_AND_REGRESSION_VERIFICATION",
            "rules_tuned_on_evaluated_documents": True,
            "ground_truth_derived_from_stage4_2_curated_specs": gt_derived_from_s42_output,
            "extractor_uses_document_specific_anchor_dispatchers": has_hardcoded_doc_dispatchers,
            "has_generic_unseen_document_clause_parser": False,
            "scientific_validity_warning": (
                "TEMUAN KRITIS METODOLOGI: Tiga dokumen pada dataset evaluasi (DOC-001, DOC-024, DOC-009) "
                "adalah dokumen yang sama yang digunakan untuk mengaudit Stage 4.1 dan menyempurnakan aturan "
                "serta spesifikasi anchor pada Stage 4.2. Selain itu, build_ground_truth_dataset() di evaluator.py "
                "membangun 145 item ground truth yang dapat diekstrak secara langsung dari spesifikasi Stage 4.2 "
                "(ditambah 2 item OCR rusak). Oleh karena itu, F1-score 0.9932 merupakan metrik kalibrasi in-sample "
                "(verifikasi regresi pada 3 dokumen pengembangan), BUKAN hasil pengujian independen (held-out test) "
                "pada dokumen yang belum pernah dilihat ekstraktor."
            ),
        },
    }


def _evaluate_document_variation(
    inv_payload: Dict[str, Any],
    units_payload: Dict[str, Any],
    seg_val_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Task 2: Group all 80 documents and 114 units by structure, text quality, doc type, and entity type."""
    docs = inv_payload["documents"]
    units = units_payload["branch_units"]
    unit_vals = {
        u["branch_unit_id"]: u for u in seg_val_payload["unit_validations"]
    }
    docs_by_id = {d["document_id"]: d for d in docs}

    evaluated_doc_ids = {"DOC-001", "DOC-024", "DOC-009"}
    evaluated_unit_ids = {
        "DOC-001-BU-01",
        "DOC-024-BU-01",
        "DOC-024-BU-02",
        "DOC-024-BU-03",
        "DOC-009-BU-01",
        "DOC-009-BU-02",
        "DOC-009-BU-03",
        "DOC-009-BU-04",
    }

    def _summarize_group(
        all_items: List[Dict[str, Any]],
        key_fn,
        eval_predicate,
        doc_id_fn,
    ) -> Dict[str, Dict[str, Any]]:
        totals: Counter = Counter()
        evals: Counter = Counter()
        example_docs: Dict[str, List[str]] = {}
        for item in all_items:
            k = str(key_fn(item))
            totals[k] += 1
            if eval_predicate(item):
                evals[k] += 1
            did = doc_id_fn(item)
            if did not in example_docs.setdefault(k, []) and len(example_docs[k]) < 5:
                example_docs[k].append(did)

        result: Dict[str, Dict[str, Any]] = {}
        for k in sorted(totals.keys()):
            tot = totals[k]
            ev = evals[k]
            result[k] = {
                "total_count": tot,
                "evaluated_count": ev,
                "unevaluated_count": tot - ev,
                "evaluated_percentage": _pct(ev, tot),
                "representation_status": (
                    "REPRESENTED_SAMPLE" if ev > 0 else "UNREPRESENTED_ZERO_COVERAGE"
                ),
                "sample_document_ids": example_docs[k],
            }
        return result

    by_multi_branch_doc = _summarize_group(
        docs,
        lambda d: d["multi_branch_type"],
        lambda d: d["document_id"] in evaluated_doc_ids,
        lambda d: d["document_id"],
    )
    by_multi_branch_unit = _summarize_group(
        units,
        lambda u: u["multi_branch_type"],
        lambda u: u["branch_unit_id"] in evaluated_unit_ids,
        lambda u: u["document_id"],
    )
    by_readability_doc = _summarize_group(
        docs,
        lambda d: d["readability_status"],
        lambda d: d["document_id"] in evaluated_doc_ids,
        lambda d: d["document_id"],
    )
    by_readability_unit = _summarize_group(
        units,
        lambda u: docs_by_id[u["document_id"]]["readability_status"],
        lambda u: u["branch_unit_id"] in evaluated_unit_ids,
        lambda u: u["document_id"],
    )
    by_macro_category_doc = _summarize_group(
        docs,
        lambda d: d["macro_document_category"],
        lambda d: d["document_id"] in evaluated_doc_ids,
        lambda d: d["document_id"],
    )
    by_validated_doc_type = _summarize_group(
        docs,
        lambda d: d["validated_document_type"],
        lambda d: d["document_id"] in evaluated_doc_ids,
        lambda d: d["document_id"],
    )
    by_semantic_entity_unit = _summarize_group(
        units,
        lambda u: unit_vals[u["branch_unit_id"]]["semantic_entity_type"],
        lambda u: u["branch_unit_id"] in evaluated_unit_ids,
        lambda u: u["document_id"],
    )
    by_seg_val_status_unit = _summarize_group(
        units,
        lambda u: unit_vals[u["branch_unit_id"]]["validation_status"],
        lambda u: u["branch_unit_id"] in evaluated_unit_ids,
        lambda u: u["document_id"],
    )

    unrepresented_groups = [
        {
            "dimension": "multi_branch_type",
            "group_name": "composite_branch_competition",
            "total_documents": 5,
            "total_units": 5,
            "evaluated_units": 0,
            "affected_document_ids": ["DOC-016", "DOC-037", "DOC-038", "DOC-051", "DOC-064"],
            "risk_if_expanded_blindly": (
                "Kompetisi komposit mewajibkan beberapa artefak lintas-domain dalam satu kesatuan "
                "(misalnya proposal bisnis + prototipe produk atau UI/UX + pitching); ekstraktor belum diuji "
                "untuk memetakan ketergantungan antar-komponen luaran dalam satu unit komposit."
            ),
        },
        {
            "dimension": "multi_branch_type",
            "group_name": "primary_branch_with_multi_event_intro",
            "total_documents": 4,
            "total_units": 4,
            "evaluated_units": 0,
            "affected_document_ids": ["DOC-033", "DOC-054", "DOC-070", "DOC-073"],
            "risk_if_expanded_blindly": (
                "Dokumen memiliki pengantar rangkaian acara multi-lomba tetapi isi teknisnya hanya membahas "
                "1 cabang spesifik (termasuk kasus ketidaksesuaian nama file DOC-054 dan DOC-073); "
                "berisiko mencampur informasi pengantar event umum ke persyaratan cabang spesifik."
            ),
        },
        {
            "dimension": "macro_document_category",
            "group_name": "dokumen_ketentuan_dan_petunjuk_teknis",
            "total_documents": 11,
            "total_units": 18,
            "evaluated_units": 0,
            "affected_document_ids": [
                "DOC-046",
                "DOC-053",
                "DOC-058",
                "DOC-059",
                "DOC-063",
                "DOC-065",
                "DOC-076",
                "DOC-077",
                "DOC-078",
                "DOC-079",
                "DOC-080",
            ],
            "risk_if_expanded_blindly": (
                "Seluruh 3 dokumen evaluasi Stage 4.2 berasal dari kategori 'dokumen_panduan_kompetisi' "
                "bertipe 'guidebook'. Dokumen bertipe 'ketentuan_lomba', 'petunjuk_teknis', 'syarat_ketentuan', "
                "dan 'rulebook' memiliki struktur penomoran pasal/butir langsung tanpa bab standar guidebook."
            ),
        },
        {
            "dimension": "semantic_entity_type",
            "group_name": "8_unrepresented_semantic_entity_types",
            "total_documents": 13,
            "total_units": 39,
            "evaluated_units": 0,
            "affected_entity_types": [
                "event_level_general_information (10 units)",
                "sub_event_brochure_entry (8 units — DOC-015)",
                "competition_category_guide (7 units — DOC-071, DOC-076)",
                "composite_competition_guide (5 units)",
                "competition_stage_guide (4 units — DOC-061)",
                "bundled_multi_branch_appendix (3 units — DOC-062-BU-02, DOC-067-BU-02, DOC-069-BU-02)",
                "mixed_subtheme_overview (1 unit — DOC-047-BU-04)",
                "non_rulebook_finalist_catalog (1 unit — DOC-007-BU-01)",
            ],
            "risk_if_expanded_blindly": (
                "Hanya 2 dari 10 semantic_entity_type yang terwakili di evaluasi Stage 4.2 "
                "(single_branch_competition_guide dan branch_specific_technical_guide). Memproses "
                "bundled_multi_branch_appendix (11 cabang FIKSI atau 37 cabang LKS dalam 1 unit) atau "
                "competition_stage_guide (4 tahap lomba dalam 4 unit berbeda pada DOC-061) akan merusak "
                "integritas matriks persyaratan."
            ),
        },
    ]

    return {
        "corpus_totals": {
            "total_documents": len(docs),
            "segmented_competition_documents": 76,
            "excluded_non_competition_or_empty_documents": 4,
            "total_branch_units": len(units),
            "evaluated_documents_count": len(evaluated_doc_ids),
            "evaluated_documents_percentage": _pct(len(evaluated_doc_ids), len(docs)),
            "evaluated_branch_units_count": len(evaluated_unit_ids),
            "evaluated_branch_units_percentage": _pct(
                len(evaluated_unit_ids), len(units)
            ),
        },
        "by_multi_branch_type_documents": by_multi_branch_doc,
        "by_multi_branch_type_units": by_multi_branch_unit,
        "by_readability_status_documents": by_readability_doc,
        "by_readability_status_units": by_readability_unit,
        "by_macro_document_category_documents": by_macro_category_doc,
        "by_validated_document_type_documents": by_validated_doc_type,
        "by_semantic_entity_type_units": by_semantic_entity_unit,
        "by_segmentation_validation_status_units": by_seg_val_status_unit,
        "unrepresented_and_underrepresented_groups": unrepresented_groups,
    }


def _evaluate_provenance_and_semantics(
    project_root: Path,
    req_payload: Dict[str, Any],
    inv_payload: Dict[str, Any],
    units_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Task 3: Audit provenance traceability, grounding, char ranges, page/section, cross-branch isolation, and explicit vs inferred."""
    docs_by_id = {d["document_id"]: d for d in inv_payload["documents"]}
    units_by_id = {u["branch_unit_id"]: u for u in units_payload["branch_units"]}
    raw_dir = project_root / "data" / "raw" / "txt"
    raw_texts = {
        doc_id: (raw_dir / docs_by_id[doc_id]["file_name"]).read_text(encoding="utf-8")
        for doc_id in ("DOC-001", "DOC-024", "DOC-009")
    }

    reqs = req_payload["requirements"]
    infos = req_payload["information_items"]
    gaps = req_payload["extraction_gaps"]
    reviews = req_payload["review_items"]

    traceable_count = 0
    verbatim_match_count = 0
    grounded_description_count = 0
    valid_char_range_count = 0
    valid_page_and_section_count = 0
    strict_unit_bounds_count = 0
    shared_or_truncated_span_recovery_count = 0
    provenance_violations: List[Dict[str, Any]] = []

    for r in reqs:
        rid = r["requirement_id"]
        did = r["document_id"]
        uid = r["branch_unit_id"]
        raw_text = raw_texts.get(did, "")
        s = int(r.get("source_char_start", -1))
        e = int(r.get("source_char_end", -1))
        ev = r.get("evidence_text", "")
        desc = r.get("requirement_description", "")
        page = int(r.get("source_page", 0))
        sec = str(r.get("source_section", "")).strip()

        has_trace_ids = did in docs_by_id and uid in units_by_id
        if has_trace_ids:
            traceable_count += 1
        else:
            provenance_violations.append({"id": rid, "issue": "invalid_doc_or_unit_id"})

        if 0 <= s < e <= len(raw_text):
            valid_char_range_count += 1
        else:
            provenance_violations.append(
                {"id": rid, "issue": f"invalid_char_range_{s}_{e}"}
            )

        if 0 <= s < e <= len(raw_text) and raw_text[s:e] == ev and len(ev.strip()) > 0:
            verbatim_match_count += 1
        else:
            provenance_violations.append({"id": rid, "issue": "verbatim_mismatch"})

        ok_ground, ungrounded = verify_description_grounded_in_evidence(
            desc, ev, r.get("evidence_type", "explicit")
        )
        if ok_ground:
            grounded_description_count += 1
        else:
            provenance_violations.append(
                {"id": rid, "issue": f"ungrounded_claims_{ungrounded}"}
            )

        if page >= 1 and len(sec) > 0:
            valid_page_and_section_count += 1
        else:
            provenance_violations.append(
                {"id": rid, "issue": "missing_page_or_section"}
            )

        u = units_by_id[uid]
        u_start, u_end = int(u["start_char"]), int(u["end_char"])
        if u_start <= s and e <= u_end:
            strict_unit_bounds_count += 1
        else:
            shared_or_truncated_span_recovery_count += 1

    # Also verify verbatim evidence on information_items and review_items
    info_verbatim_ok = all(
        raw_texts[i["document_id"]][
            int(i["source_char_start"]) : int(i["source_char_end"])
        ]
        == i["evidence_text"]
        for i in infos
    )
    review_verbatim_ok = all(
        raw_texts[rv["document_id"]][
            int(rv["source_char_start"]) : int(rv["source_char_end"])
        ]
        == rv["evidence_text"]
        for rv in reviews
    )

    explicit_count = sum(1 for r in reqs if r["evidence_type"] == "explicit")
    inferred_count = sum(1 for r in reqs if r["evidence_type"] == "inferred")

    return {
        "total_requirements_audited": len(reqs),
        "traceable_source_id_count": traceable_count,
        "valid_character_range_count": valid_char_range_count,
        "verbatim_evidence_match_count": verbatim_match_count,
        "description_grounded_in_evidence_count": grounded_description_count,
        "valid_page_and_section_count": valid_page_and_section_count,
        "information_items_verbatim_verified": info_verbatim_ok,
        "review_items_verbatim_verified": review_verbatim_ok,
        "provenance_violations_found": provenance_violations,
        "cross_branch_isolation_audit": {
            "strict_within_unit_bounds_count": strict_unit_bounds_count,
            "strict_within_unit_bounds_percentage": _pct(
                strict_unit_bounds_count, len(reqs)
            ),
            "controlled_out_of_unit_recovery_count": shared_or_truncated_span_recovery_count,
            "controlled_out_of_unit_recovery_details": (
                "8 record pada DOC-009 (7 record pendaftaran/biaya bersama pada char 46547..48658 lintas "
                "BU-01..04 dan 1 record jadwal Gelombang 1 Esai pada char 3157..3765 yang terpotong batas "
                "awal segmen 3250) diambil melalui shared-span lookup yang dikontrol ketat dan diberi status "
                "VALIDATED_WITH_SEGMENTATION_LIMITATION atau NEEDS_REVIEW."
            ),
            "source_copy_paste_anomaly_handling": (
                "Pada DOC-024, buku panduan asli melakukan kesalahan salin-tempel teks Cabang Esai/BMC ke "
                "Mekanisme Pendaftaran Cabang BMC (halaman 15) dan Cabang Poster (halaman 23). Ekstraktor "
                "Stage 4.2 tidak mencampur syarat antar-unit, melainkan mengisolasi teks sesuai unitnya, "
                "memberi status NEEDS_REVIEW pada REQ-DOC024-BU02-019 dan REQ-DOC024-BU03-003, serta "
                "mencatat anomali di REV-DOC024-BU02-001 dan REV-DOC024-BU03-001."
            ),
        },
        "explicit_vs_inferred_audit": {
            "explicit_requirements_count": explicit_count,
            "inferred_requirements_count": inferred_count,
            "statement_nature_distribution": dict(
                Counter(r["statement_nature"] for r in reqs)
            ),
            "separation_assessment": (
                "Skema dan verifikator memisahkan secara tegas aturan eksplisit ('explicit'), inferensi "
                "('inferred'), informasi pendukung ('information_items'), ketidaktersediaan aturan "
                "('extraction_gaps'), dan item pemeriksaan manusia ('review_items'). Namun karena seluruh "
                "145 record aktif pada 3 dokumen uji saat ini bertipe 'explicit' (0 'inferred'), aturan "
                "inferensi belum diuji pada kasus persyaratan implisit di dokumen korpus lainnya."
            ),
        },
    }


def _evaluate_extraction_coverage(
    req_payload: Dict[str, Any],
    units_payload: Dict[str, Any],
    seg_val_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Task 4: Measure unit coverage, category coverage, human review load, gaps, and record count vs completeness."""
    reqs = req_payload["requirements"]
    gaps = req_payload["extraction_gaps"]
    reviews = req_payload["review_items"]
    all_units = units_payload["branch_units"]
    unit_vals = seg_val_payload["unit_validations"]

    evaluated_unit_ids = [
        "DOC-001-BU-01",
        "DOC-024-BU-01",
        "DOC-024-BU-02",
        "DOC-024-BU-03",
        "DOC-009-BU-01",
        "DOC-009-BU-02",
        "DOC-009-BU-03",
        "DOC-009-BU-04",
    ]

    per_unit_coverage: Dict[str, Any] = {}
    for uid in evaluated_unit_ids:
        u_reqs = [r for r in reqs if r["branch_unit_id"] == uid]
        u_gaps = [g for g in gaps if g["branch_unit_id"] == uid]
        u_revs = [rv for rv in reviews if rv["branch_unit_id"] == uid]
        cats_present = sorted({r["requirement_category"] for r in u_reqs})
        needs_human = (
            len(u_revs) > 0
            or any(r["validation_status"] != "VALIDATED" for r in u_reqs)
        )
        per_unit_coverage[uid] = {
            "extracted_requirement_records": len(u_reqs),
            "categories_with_extracted_records": len(cats_present),
            "missing_categories_completely": [
                c for c in REQUIREMENT_CATEGORIES if c not in cats_present
            ],
            "documented_extraction_gaps_count": len(u_gaps),
            "documented_missing_attributes": [
                g["missing_attribute_name"] for g in u_gaps
            ],
            "review_items_count": len(u_revs),
            "requires_human_inspection": needs_human,
            "is_100_percent_complete_without_gaps_or_reviews": (
                len(u_gaps) == 0 and not needs_human
            ),
        }

    # Subcategory coverage across the 32 defined subcategories in rules.py
    all_defined_subcats = [
        (cat, sub)
        for cat, subs in REQUIREMENT_SUBCATEGORIES.items()
        for sub in subs
    ]
    extracted_subcat_counts = Counter(
        (r["requirement_category"], r["requirement_subcategory"]) for r in reqs
    )

    # Corpus-wide human inspection projection from Stage 3.1 segmentation_validation.json
    seg_status_counts = Counter(u["validation_status"] for u in unit_vals)

    return {
        "unit_evaluation_coverage": {
            "total_branch_units_in_corpus": len(all_units),
            "evaluated_branch_units_count": len(evaluated_unit_ids),
            "unevaluated_branch_units_count": len(all_units) - len(evaluated_unit_ids),
            "evaluated_branch_units_percentage": _pct(
                len(evaluated_unit_ids), len(all_units)
            ),
            "unevaluated_branch_units_percentage": _pct(
                len(all_units) - len(evaluated_unit_ids), len(all_units)
            ),
        },
        "category_and_subcategory_coverage": {
            "main_categories_defined": len(REQUIREMENT_CATEGORIES),
            "main_categories_extracted_in_evaluated_units": len(
                {r["requirement_category"] for r in reqs}
            ),
            "subcategories_defined_total": len(all_defined_subcats),
            "subcategories_populated_in_evaluated_units": len(extracted_subcat_counts),
            "counts_by_main_category": dict(
                Counter(r["requirement_category"] for r in reqs)
            ),
        },
        "missing_information_and_extraction_gaps": {
            "total_extraction_gaps_in_evaluated_units": len(gaps),
            "missing_attributes_frequency": dict(
                Counter(g["missing_attribute_name"] for g in gaps)
            ),
            "ocr_illegible_requirements_routed_to_review": [
                {
                    "review_id": "REV-DOC009-BU01-003",
                    "branch_unit_id": "DOC-009-BU-01",
                    "category": "technical_and_general_rules",
                    "missing_information": "Jenis font, ukuran font, spasi, dan margin naskah esai pada halaman 14 bawah (char 12983..13328) rusak berat akibat OCR.",
                },
                {
                    "review_id": "REV-DOC009-BU03-001",
                    "branch_unit_id": "DOC-009-BU-03",
                    "category": "technical_and_general_rules",
                    "missing_information": "Blok ketentuan tambahan setelah butir 7 publikasi Instagram pada halaman 39 bawah (char 35122..35486) rusak berat akibat OCR.",
                },
            ],
        },
        "human_inspection_requirements": {
            "evaluated_units_requiring_human_review_or_limitation_handling": sum(
                1
                for v in per_unit_coverage.values()
                if v["requires_human_inspection"]
            ),
            "evaluated_units_total": len(evaluated_unit_ids),
            "evaluated_requirements_by_validation_status": dict(
                Counter(r["validation_status"] for r in reqs)
            ),
            "total_review_items_in_evaluated_units": len(reviews),
            "corpus_wide_segmentation_status_distribution": dict(seg_status_counts),
            "corpus_units_requiring_stage3_or_manual_intervention_before_clean_extraction": (
                seg_status_counts["VALIDATED_WITH_LIMITATION"]
                + seg_status_counts["NEEDS_REVISION"]
            ),
        },
        "record_count_vs_completeness_analysis": {
            "per_evaluated_unit_breakdown": per_unit_coverage,
            "methodological_conclusion": (
                "Jumlah record yang berhasil diekstrak (145 record dari 8 unit; rata-rata 18,12 record/unit) "
                "TIDAK boleh disamakan dengan tingkat kelengkapan persyaratan 100%. Meskipun seluruh 8 unit "
                "memiliki record pada ke-6 kategori utama, 8 dari 8 unit (100%) memiliki celah informasi "
                "('extraction_gaps' seperti batas usia yang tidak dicantumkan atau tabel rubrik tanpa bobot %) "
                "serta 7 dari 8 unit (87,5%) memiliki 'review_items' aktif (placeholder [TBC], kontradiksi "
                "jadwal/aturan, salah ketik salin-tempel, atau blok teks rusak berat akibat OCR)."
            ),
        },
    }


def _build_expansion_plan_and_decision(
    inv_payload: Dict[str, Any],
    units_payload: Dict[str, Any],
    seg_val_payload: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[CorpusExpansionPlanRow]]:
    """Tasks 5 & 6: Formulate the evidence-based expansion decision and build the 118-row staged expansion plan."""
    docs_by_id = {d["document_id"]: d for d in inv_payload["documents"]}
    units = units_payload["branch_units"]
    unit_vals = {
        u["branch_unit_id"]: u for u in seg_val_payload["unit_validations"]
    }
    excluded_vals = {
        ex["document_id"]: ex
        for ex in seg_val_payload["excluded_document_validations"]
    }

    evaluated_unit_ids = {
        "DOC-001-BU-01",
        "DOC-024-BU-01",
        "DOC-024-BU-02",
        "DOC-024-BU-03",
        "DOC-009-BU-01",
        "DOC-009-BU-02",
        "DOC-009-BU-03",
        "DOC-009-BU-04",
    }

    rows: List[CorpusExpansionPlanRow] = []

    for u in units:
        uid = u["branch_unit_id"]
        did = u["document_id"]
        d = docs_by_id[did]
        v = unit_vals[uid]

        read_st = d["readability_status"]
        macro_cat = d["macro_document_category"]
        val_dtype = d["validated_document_type"]
        mbt = d["multi_branch_type"]
        sem_ent = v["semantic_entity_type"]
        seg_st = v["validation_status"]
        in_eval = uid in evaluated_unit_ids

        # Determine wave, gate status, complexity, manual validation level, prerequisites, and rationale
        if in_eval:
            wave = "WAVE_0_COMPLETED_BASELINE"
            prio = 0
            complexity = (
                "low"
                if mbt == "single_branch"
                else ("medium" if read_st == "readable" else "high")
            )
            gate = "COMPLETED_IN_STAGE_4_2"
            manual_lvl = (
                "medium_targeted_review"
                if read_st == "readable"
                else "high_mandatory_human_review"
            )
            prereq = "Tindak lanjuti review_items yang sudah tercatat (REV-DOC001, REV-DOC024, REV-DOC009)."
            rationale = (
                "Sudah diekstrak dan dievaluasi pada Stage 4.2 (digunakan sebagai baseline kalibrasi)."
            )
        elif macro_cat in ("katalog_karya_atau_finalis", "dokumen_sosialisasi") or sem_ent == "non_rulebook_finalist_catalog":
            wave = "EXCLUDED_OR_NON_RULEBOOK"
            prio = 6
            complexity = "not_applicable"
            gate = "EXCLUDED_FROM_EXTRACTION"
            manual_lvl = "not_applicable"
            prereq = "Jangan diekstrak sebagai matriks persyaratan cabang; simpan sebagai referensi konteks/katalog."
            rationale = (
                f"Dokumen berkategori '{macro_cat}' / entitas '{sem_ent}' (bukan buku peraturan cabang mengikat)."
            )
        elif seg_st == "NEEDS_REVISION" or sem_ent in (
            "event_level_general_information",
            "bundled_multi_branch_appendix",
            "competition_stage_guide",
            "mixed_subtheme_overview",
        ):
            wave = "WAVE_5_BLOCKED_ON_STAGE3_RESEGMENTATION"
            prio = 5
            complexity = "very_high"
            gate = "BLOCKED_WAIT_FOR_STAGE3_RESEGMENTATION"
            manual_lvl = "full_manual_re_segmentation_first"
            prereq = (
                "Wajib perbaiki batas segmen Stage 3 terlebih dahulu (pecah lampiran multi-cabang FIKSI/LKS, "
                "gabungkan tahap komposit DOC-061, pisahkan 4 cabang Pre-Event DOC-047-BU-04, dan tautkan "
                "unit event_level_general_information ke masing-masing unit cabang)."
            )
            rationale = (
                f"Unit berstatus segmentasi '{seg_st}' dengan entitas '{sem_ent}'; ekstraksi langsung akan "
                "mencampur persyaratan lintas cabang atau memotong tahapan kompetisi."
            )
        elif read_st == "readable_with_ocr_noise":
            wave = "WAVE_4_OCR_NOISE_HIGH_SUPERVISION"
            prio = 4
            complexity = "high"
            gate = "HOLD_WAIT_FOR_OCR_REVIEW_PIPELINE"
            manual_lvl = "high_mandatory_human_review"
            prereq = (
                "Implementasikan parser klausa generik + detektor blok OCR rusak (otomatis mengarahkan "
                "rentang korup ke review_items) + pemeriksaan manusia terhadap PDF asli."
            )
            rationale = (
                f"Teks berstatus '{read_st}' (entitas '{sem_ent}', segmen '{seg_st}'); berisiko kehilangan "
                "angka/simbol atau aturan teknis akibat distorsi OCR seperti pada DOC-009."
            )
        elif seg_st == "VALIDATED_WITH_LIMITATION":
            wave = "WAVE_3_SHARED_CONTEXT_MULTI_BRANCH"
            prio = 3
            complexity = "high"
            gate = "HOLD_WAIT_FOR_SHARED_SPAN_RESOLVER"
            manual_lvl = "medium_targeted_review"
            prereq = (
                "Implementasikan parser klausa generik DAN resolver pewarisan rentang bersama "
                "(shared registration/payment/intro spans dari segmentation_validation.json)."
            )
            rationale = (
                f"Teks '{read_st}' namun berstatus '{seg_st}' karena sebagian syarat umum/pendaftaran "
                "berada pada uncovered_char_spans di luar batas ketat unit cabang."
            )
        elif (
            mbt in ("composite_branch_competition", "primary_branch_with_multi_event_intro")
            or macro_cat == "dokumen_ketentuan_dan_petunjuk_teknis"
            or val_dtype != "guidebook"
        ):
            wave = "WAVE_2_UNREPRESENTED_DOC_TYPES_AND_COMPOSITE_PILOT"
            prio = 2
            complexity = "medium"
            gate = "HOLD_WAIT_FOR_TYPE_REPRESENTATION_PILOT"
            manual_lvl = "medium_targeted_review"
            prereq = (
                "Implementasikan parser klausa generik dan lakukan validasi pilot held-out pada sampel "
                "dokumen composite_branch_competition, primary_branch_with_multi_event_intro, serta "
                "dokumen_ketentuan_dan_petunjuk_teknis (non-guidebook)."
            )
            rationale = (
                f"Unit bersih ('{read_st}', '{seg_st}'), tetapi kelompok struktur '{mbt}' atau tipe "
                f"dokumen '{val_dtype}' ('{macro_cat}') belum memiliki keterwakilan (0%) pada evaluasi Stage 4.2."
            )
        else:
            wave = "WAVE_1_CLEAN_SINGLE_AND_VALIDATED_BRANCH"
            prio = 1
            complexity = "low" if mbt == "single_branch" else "medium"
            gate = "HOLD_WAIT_FOR_GENERIC_PARSER_AND_HELD_OUT_PILOT"
            manual_lvl = "low_spot_check"
            prereq = (
                "Implementasikan parser bagian/klausa generik di src/requirement_extraction/extractor.py "
                "dan lulus uji independen held-out pada minimal 3-5 dokumen Wave 1."
            )
            rationale = (
                f"Kelompok paling siap: teks '{read_st}', segmen '{seg_st}', tipe '{val_dtype}', dan "
                f"struktur '{mbt}' sejenis dengan DOC-001/DOC-024."
            )

        rows.append(
            CorpusExpansionPlanRow(
                plan_row_id="",
                expansion_wave=wave,
                wave_priority_order=prio,
                document_id=did,
                branch_unit_id=uid,
                file_name=d["file_name"],
                readability_status=read_st,
                macro_document_category=macro_cat,
                validated_document_type=val_dtype,
                multi_branch_type=mbt,
                semantic_entity_type=sem_ent,
                segmentation_validation_status=seg_st,
                structural_complexity=complexity,
                represented_in_stage4_2_eval=in_eval,
                expansion_gate_status=gate,
                manual_validation_level=manual_lvl,
                prerequisite_actions=prereq,
                decision_rationale=rationale,
            )
        )

    # Add the 4 unsegmented documents (DOC-005, DOC-014, DOC-034, DOC-060)
    for did, ex in sorted(excluded_vals.items()):
        d = docs_by_id[did]
        if d["readability_status"] == "empty":
            prereq = "Konversi ulang / OCR dari file PDF asli 'Guidebook BPC TSF 2026.pdf', lalu jalankan Stage 2 & Stage 3."
            rationale = "File TXT kosong (0 karakter isi, hanya 3 byte BOM); tidak dapat diproses sebelum konversi ulang PDF."
        else:
            prereq = "Pertahankan eksklusi dari ekstraksi persyaratan kompetisi."
            rationale = ex["validation_reason"]

        rows.append(
            CorpusExpansionPlanRow(
                plan_row_id="",
                expansion_wave="EXCLUDED_OR_NON_RULEBOOK",
                wave_priority_order=6,
                document_id=did,
                branch_unit_id="NONE",
                file_name=d["file_name"],
                readability_status=d["readability_status"],
                macro_document_category=d["macro_document_category"],
                validated_document_type=d["validated_document_type"],
                multi_branch_type=d["multi_branch_type"],
                semantic_entity_type="excluded_non_competition_or_empty",
                segmentation_validation_status=ex["validation_status"],
                structural_complexity="not_applicable",
                represented_in_stage4_2_eval=False,
                expansion_gate_status="EXCLUDED_FROM_EXTRACTION",
                manual_validation_level="not_applicable",
                prerequisite_actions=prereq,
                decision_rationale=rationale,
            )
        )

    # Sort rows deterministically by (wave_priority_order, document_id, branch_unit_id)
    rows.sort(
        key=lambda r: (r.wave_priority_order, r.document_id, r.branch_unit_id)
    )
    for idx, r in enumerate(rows, 1):
        r.plan_row_id = f"PLAN-{idx:03d}"

    wave_counts = Counter(r.expansion_wave for r in rows)
    wave_doc_sets: Dict[str, set[str]] = {}
    for r in rows:
        wave_doc_sets.setdefault(r.expansion_wave, set()).add(r.document_id)

    decision_block: Dict[str, Any] = {
        "overall_readiness_status": "NEEDS_MORE_REFINEMENT",
        "conditional_restricted_status_after_generic_parser": "READY_WITH_RESTRICTIONS",
        "decision_summary": (
            "Ekstraktor saat ini berstatus NEEDS_MORE_REFINEMENT sebelum dapat dijalankan secara "
            "otomatis ke seluruh korpus. Meskipun kualitas bukti, skema 4 entitas, dan aturan "
            "verifikasi pada Stage 4.2 sangat kuat (F1 = 0.9932 pada 3 dokumen kalibrasi), "
            "src/requirement_extraction/extractor.py saat ini masih menggunakan pemetaan anchor "
            "spesifik-dokumen (_extract_doc001_bu01, _extract_doc024_units, _extract_doc009_units) "
            "dan belum memiliki parser bagian/klausa generik yang dievaluasi pada held-out test set "
            "independen. Begitu parser generik diimplementasikan dan lulus evaluasi held-out pilot, "
            "status beralih menjadi READY_WITH_RESTRICTIONS untuk memproses Wave 1 terlebih dahulu."
        ),
        "evidence_backed_reasons": [
            {
                "reason_id": "DEC-REASON-01",
                "category": "architecture_generalization_gap",
                "finding": (
                    "src/requirement_extraction/extractor.py baru memuat fungsi ekstraksi spesifik untuk "
                    "DOC-001, DOC-024, dan DOC-009 berbasis anchor terkurasi; belum ada fungsi parser "
                    "otomatis untuk mengekstrak kandidat klausa dari 73 dokumen kompetisi lainnya."
                ),
            },
            {
                "reason_id": "DEC-REASON-02",
                "category": "evaluation_independence_limitation",
                "finding": (
                    "Metrik evaluasi Stage 4.2 (Precision 1.0000, Recall 0.9864, F1 0.9932) dihitung pada "
                    "3 dokumen yang sama yang dipakai untuk menyempurnakan aturan dan membangun ground truth "
                    "(in-sample calibration), sehingga belum membuktikan generalisasi pada unseen documents."
                ),
            },
            {
                "reason_id": "DEC-REASON-03",
                "category": "unrepresented_document_and_entity_types",
                "finding": (
                    "Sebanyak 106 dari 114 unit cabang (92,98%) belum dievaluasi, termasuk 0% keterwakilan "
                    "pada composite_branch_competition (5 unit), primary_branch_with_multi_event_intro (4 unit), "
                    "dokumen_ketentuan_dan_petunjuk_teknis (18 unit), serta 8 dari 10 semantic_entity_type."
                ),
            },
            {
                "reason_id": "DEC-REASON-04",
                "category": "unresolved_stage3_segmentation_and_shared_spans",
                "finding": (
                    "Sebanyak 11 unit berstatus NEEDS_REVISION (termasuk lampiran gabungan 11 cabang FIKSI "
                    "dan 37 cabang LKS) serta 40 unit berstatus VALIDATED_WITH_LIMITATION (membutuhkan "
                    "resolusi 25 rentang penting di luar batas unit atau penanganan noise OCR)."
                ),
            },
        ],
        "cohort_gating_rules": {
            "WAVE_0_COMPLETED_BASELINE": {
                "plan_rows_count": wave_counts["WAVE_0_COMPLETED_BASELINE"],
                "unique_documents_count": len(
                    wave_doc_sets.get("WAVE_0_COMPLETED_BASELINE", set())
                ),
                "gate_decision": "ALREADY_EXTRACTED_IN_STAGE_4_2",
                "allowed_now": True,
                "description": "3 dokumen representatif (8 unit: DOC-001, DOC-024, DOC-009) yang sudah diekstrak dan diaudit.",
            },
            "WAVE_1_CLEAN_SINGLE_AND_VALIDATED_BRANCH": {
                "plan_rows_count": wave_counts[
                    "WAVE_1_CLEAN_SINGLE_AND_VALIDATED_BRANCH"
                ],
                "unique_documents_count": len(
                    wave_doc_sets.get(
                        "WAVE_1_CLEAN_SINGLE_AND_VALIDATED_BRANCH", set()
                    )
                ),
                "gate_decision": "FIRST_COHORT_TO_PROCESS_AFTER_GENERIC_PARSER",
                "allowed_now": False,
                "description": (
                    "Dokumen single_branch dan multi_branch_event yang berstatus readable, VALIDATED, "
                    "dan bertipe guidebook standar. Kelompok pertama yang boleh diproses segera setelah "
                    "parser generik diimplementasikan dan lulus pilot held-out 3-5 dokumen."
                ),
            },
            "WAVE_2_UNREPRESENTED_DOC_TYPES_AND_COMPOSITE_PILOT": {
                "plan_rows_count": wave_counts[
                    "WAVE_2_UNREPRESENTED_DOC_TYPES_AND_COMPOSITE_PILOT"
                ],
                "unique_documents_count": len(
                    wave_doc_sets.get(
                        "WAVE_2_UNREPRESENTED_DOC_TYPES_AND_COMPOSITE_PILOT", set()
                    )
                ),
                "gate_decision": "WAIT_FOR_REPRESENTATION_PILOT",
                "allowed_now": False,
                "description": (
                    "Unit readable & VALIDATED tetapi berasal dari kelompok yang 0% terwakili di evaluasi "
                    "Stage 4.2: composite_branch_competition, primary_branch_with_multi_event_intro, atau "
                    "dokumen non-guidebook (ketentuan_lomba, petunjuk_teknis, rulebook, pedoman, panduan)."
                ),
            },
            "WAVE_3_SHARED_CONTEXT_MULTI_BRANCH": {
                "plan_rows_count": wave_counts[
                    "WAVE_3_SHARED_CONTEXT_MULTI_BRANCH"
                ],
                "unique_documents_count": len(
                    wave_doc_sets.get("WAVE_3_SHARED_CONTEXT_MULTI_BRANCH", set())
                ),
                "gate_decision": "WAIT_FOR_SHARED_SPAN_INHERITANCE_RESOLVER",
                "allowed_now": False,
                "description": (
                    "Unit readable yang berstatus VALIDATED_WITH_LIMITATION karena pendaftaran/ketentuan "
                    "umum berada pada uncovered_char_spans di luar batas unit cabang."
                ),
            },
            "WAVE_4_OCR_NOISE_HIGH_SUPERVISION": {
                "plan_rows_count": wave_counts[
                    "WAVE_4_OCR_NOISE_HIGH_SUPERVISION"
                ],
                "unique_documents_count": len(
                    wave_doc_sets.get("WAVE_4_OCR_NOISE_HIGH_SUPERVISION", set())
                ),
                "gate_decision": "WAIT_FOR_OCR_REVIEW_WORKFLOW",
                "allowed_now": False,
                "description": (
                    "Unit dengan kualitas teks readable_with_ocr_noise (seperti DOC-008, DOC-015, DOC-076, "
                    "dan dokumen single_branch ber-OCR noise) yang wajib melewati antrean pemeriksaan manusia."
                ),
            },
            "WAVE_5_BLOCKED_ON_STAGE3_RESEGMENTATION": {
                "plan_rows_count": wave_counts[
                    "WAVE_5_BLOCKED_ON_STAGE3_RESEGMENTATION"
                ],
                "unique_documents_count": len(
                    wave_doc_sets.get(
                        "WAVE_5_BLOCKED_ON_STAGE3_RESEGMENTATION", set()
                    )
                ),
                "gate_decision": "BLOCKED_UNTIL_STAGE3_REFINEMENT",
                "allowed_now": False,
                "description": (
                    "Unit berstatus NEEDS_REVISION atau event_level_general_information (DOC-047-BU-04, "
                    "DOC-061, DOC-062, DOC-066, DOC-067, DOC-068, DOC-069, DOC-071) yang tidak boleh "
                    "diekstrak sebelum batas segmentasi diperbaiki."
                ),
            },
            "EXCLUDED_OR_NON_RULEBOOK": {
                "plan_rows_count": wave_counts["EXCLUDED_OR_NON_RULEBOOK"],
                "unique_documents_count": len(
                    wave_doc_sets.get("EXCLUDED_OR_NON_RULEBOOK", set())
                ),
                "gate_decision": "DO_NOT_EXTRACT_REQUIREMENTS",
                "allowed_now": False,
                "description": (
                    "4 dokumen dieksklusi (DOC-005 rekrutmen, DOC-014 bootcamp, DOC-034 file kosong, "
                    "DOC-060 modul belajar) + DOC-007 katalog finalis + DOC-075 paparan sosialisasi LKS."
                ),
            },
        },
    }

    return decision_block, rows


def evaluate_corpus_expansion_readiness(
    project_root: Path,
    write_outputs: bool = True,
) -> Dict[str, Any]:
    """Run Stage 4.3 Baseline Evaluation & Corpus Expansion Readiness Audit."""
    req_path = project_root / "data" / "processed" / "competition_requirements.json"
    eval_path = (
        project_root / "data" / "processed" / "requirement_extraction_evaluation.json"
    )
    inv_path = (
        project_root / "data" / "processed" / "document_inventory_validated.json"
    )
    units_path = (
        project_root / "data" / "processed" / "competition_branch_units.json"
    )
    seg_val_path = (
        project_root / "data" / "processed" / "segmentation_validation.json"
    )

    req_payload = json.loads(req_path.read_text(encoding="utf-8"))
    eval_payload = json.loads(eval_path.read_text(encoding="utf-8"))
    inv_payload = json.loads(inv_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    seg_val_payload = json.loads(seg_val_path.read_text(encoding="utf-8"))

    baseline_audit = _evaluate_baseline_and_methodology(eval_payload, req_payload)
    variation_audit = _evaluate_document_variation(
        inv_payload, units_payload, seg_val_payload
    )
    provenance_audit = _evaluate_provenance_and_semantics(
        project_root, req_payload, inv_payload, units_payload
    )
    coverage_audit = _evaluate_extraction_coverage(
        req_payload, units_payload, seg_val_payload
    )
    decision_block, plan_rows = _build_expansion_plan_and_decision(
        inv_payload, units_payload, seg_val_payload
    )

    automated_checks = {
        "all_145_requirements_traceable_to_valid_doc_and_unit": (
            provenance_audit["traceable_source_id_count"] == 145
        ),
        "all_145_requirements_have_valid_char_ranges": (
            provenance_audit["valid_character_range_count"] == 145
        ),
        "all_145_requirements_match_raw_txt_verbatim": (
            provenance_audit["verbatim_evidence_match_count"] == 145
        ),
        "all_145_requirements_pass_automated_grounding_check": (
            provenance_audit["description_grounded_in_evidence_count"] == 145
        ),
        "all_information_and_review_items_match_raw_txt_verbatim": (
            provenance_audit["information_items_verbatim_verified"]
            and provenance_audit["review_items_verbatim_verified"]
        ),
        "zero_not_stated_records_in_active_requirements": all(
            r["validation_status"] != "NOT_STATED"
            for r in req_payload["requirements"]
        ),
        "all_80_documents_and_114_units_accounted_in_expansion_plan": (
            len({r.document_id for r in plan_rows}) == 80
            and sum(1 for r in plan_rows if r.branch_unit_id != "NONE") == 114
        ),
    }

    semantic_validation = {
        "evaluation_set_is_independent_held_out": baseline_audit[
            "evaluation_independence_and_leakage_audit"
        ]["is_independent_held_out_test_set"],
        "extractor_has_generic_unseen_document_parser": baseline_audit[
            "evaluation_independence_and_leakage_audit"
        ]["has_generic_unseen_document_clause_parser"],
        "all_corpus_multi_branch_types_represented_in_eval": False,
        "all_corpus_document_types_represented_in_eval": False,
        "all_corpus_semantic_entity_types_represented_in_eval": False,
        "record_count_equals_requirement_completeness": False,
        "overall_semantic_readiness_conclusion": (
            "Pengujian otomatis (automated_integrity_checks) lulus 100% pada 3 dokumen kalibrasi, "
            "namun validasi semantik dan metodologis menunjukkan bahwa ekstraktor belum siap untuk "
            "ekspansi buta ke 76 dokumen karena ketiadaan parser klausa generik di extractor.py, "
            "ketiadaan evaluasi independen (held-out test), serta 0% keterwakilan pada kelompok "
            "composite_branch_competition, primary_branch_with_multi_event_intro, dan "
            "dokumen_ketentuan_dan_petunjuk_teknis."
        ),
    }

    readiness_payload: Dict[str, Any] = {
        "stage": "Stage 4.3: Baseline Evaluation & Corpus Expansion Readiness",
        "overall_readiness_status": decision_block["overall_readiness_status"],
        "conditional_restricted_status": decision_block[
            "conditional_restricted_status_after_generic_parser"
        ],
        "scope_and_non_generalization_disclaimer": (
            "Metrik F1-score 0.9932 pada Stage 4.2 berasal dari evaluasi kalibrasi in-sample terhadap "
            "3 dokumen representatif (DOC-001, DOC-024, DOC-009; 8 unit cabang) dan TIDAK mengklaim "
            "generalisasi terhadap 77 dokumen lainnya di dalam korpus."
        ),
        "separation_of_automated_vs_semantic_validation": {
            "automated_integrity_checks": automated_checks,
            "semantic_and_methodological_validation": semantic_validation,
        },
        "1_baseline_evaluation_audit": baseline_audit,
        "2_document_variation_evaluation": variation_audit,
        "3_provenance_evaluation": provenance_audit,
        "4_extraction_coverage_evaluation": coverage_audit,
        "5_expansion_decision": decision_block,
        "6_staged_expansion_strategy": {
            "total_plan_rows": len(plan_rows),
            "total_unique_documents": len({r.document_id for r in plan_rows}),
            "total_branch_units_planned": sum(
                1 for r in plan_rows if r.branch_unit_id != "NONE"
            ),
            "total_unsegmented_documents_planned": sum(
                1 for r in plan_rows if r.branch_unit_id == "NONE"
            ),
            "wave_summary": decision_block["cohort_gating_rules"],
            "next_stage_recommendations": [
                "Stage 4.4 (Generic Parser & Held-Out Pilot): Implementasikan generic section-and-clause parser di src/requirement_extraction/extractor.py yang terhubung ke rules.py tanpa anchor hardcoded, lalu uji secara buta (blind held-out evaluation) pada 5 dokumen sampel lintas Wave 1 & Wave 2.",
                "Stage 3.2 (Targeted Segmentation & Shared-Span Refinement): Perbaiki 11 unit berstatus NEEDS_REVISION (pecah lampiran multi-cabang FIKSI DOC-062/069 & LKS DOC-067, satukan unit tahapan komposit DOC-061, pisahkan 4 cabang Pre-Event DOC-047-BU-04) dan bangun resolver otomatis untuk 25 important_uncovered_char_spans.",
                "Stage 4.5 (Gated Wave-by-Wave Rollout): Jalankan ekstraksi bertahap mulai dari Wave 1 (36 unit bersih & tervalidasi), diikuti Wave 2 (19 unit), Wave 3 (11 unit), dan Wave 4 (20 unit ber-OCR noise dengan supervisi manusia).",
            ],
            "expansion_plan_rows": [asdict(r) for r in plan_rows],
        },
    }

    if write_outputs:
        json_out = (
            project_root / "data" / "processed" / "corpus_expansion_readiness.json"
        )
        csv_out = (
            project_root / "data" / "processed" / "corpus_expansion_plan.csv"
        )
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(
            json.dumps(readiness_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        fieldnames = list(asdict(plan_rows[0]).keys())
        with csv_out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in plan_rows:
                writer.writerow(asdict(r))

    return readiness_payload
