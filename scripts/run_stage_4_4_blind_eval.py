#!/usr/bin/env python3
"""Stage 4.4: Blind Held-Out Evaluation of generic_parser against frozen GT v1.0."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path("/home/lalita/Projects/perlombaan")
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.requirement_extraction.generic_parser import parse_documents_by_ids  # noqa: E402
from src.requirement_extraction.rules import REQUIREMENT_CATEGORIES  # noqa: E402

RAW_TXT_DIR = BASE_DIR / "data" / "raw" / "txt"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

HELD_OUT_DOCS = ["DOC-011", "DOC-017", "DOC-051", "DOC-070", "DOC-053"]

FROZEN_CODE_AND_DATA_FILES = {
    "generic_parser": BASE_DIR / "src" / "requirement_extraction" / "generic_parser.py",
    "extractor": BASE_DIR / "src" / "requirement_extraction" / "extractor.py",
    "rules": BASE_DIR / "src" / "requirement_extraction" / "rules.py",
    "evaluator": BASE_DIR / "src" / "requirement_extraction" / "evaluator.py",
    "ground_truth_v1_0": PROCESSED_DIR / "stage_4_4_blind_held_out_ground_truth.json",
    "ground_truth_freeze_manifest": PROCESSED_DIR / "stage_4_4_ground_truth_freeze.json",
    "branch_units": PROCESSED_DIR / "competition_branch_units.json",
    "segmentation_validation": PROCESSED_DIR / "segmentation_validation.json",
}

DOC_053_HACKATHON_RANGES = [
    (11139, 17235),  # PETUNJUK TEKNIS PERLOMBAAN HACKATHON (A..H)
    (18757, 19394),  # TECHNICAL MEETING & BABAK FINAL HACKATHON rundowns
]

MATCHING_CONFIG = {
    "matching_strategy": "one_to_one_greedy_best_score",
    "text_normalization": "lowercase, strip zero-width chars, collapse whitespace, strip non-alphanumeric punctuation",
    "exact_match_rule": "same category AND (char_iou >= 0.85 OR normalized_text_identical)",
    "semantic_match_rule": "same category AND (char_iou >= 0.40 OR gt_token_coverage >= 0.60 OR (overlap_chars > 0 AND pred_token_coverage >= 0.70 AND token_jaccard >= 0.35))",
    "partial_match_rule": "same category AND (overlap_chars > 0 OR token_jaccard >= 0.25) AND below semantic_match threshold",
    "category_error_rule": "cross-category AND (overlap_chars > 0 OR token_jaccard >= 0.25)",
    "primary_tp_definition": ["exact_match", "semantic_match"],
    "partial_match_in_primary_tp": False,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_git_info() -> dict[str, Any]:
    info: dict[str, Any] = {"head_commit": None, "status_short": [], "note": None}
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=BASE_DIR, capture_output=True, text=True
    )
    if head.returncode == 0:
        info["head_commit"] = head.stdout.strip()
    else:
        info["note"] = head.stderr.strip() or "No git HEAD commit (unborn branch)"
    st = subprocess.run(
        ["git", "status", "--short"], cwd=BASE_DIR, capture_output=True, text=True
    )
    if st.returncode == 0:
        info["status_short"] = [line for line in st.stdout.splitlines() if line.strip()]
    return info


def get_dependencies() -> dict[str, str]:
    pkgs = {}
    for dist in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        pkgs[dist.metadata["Name"]] = dist.version
    return pkgs


def normalize_text(text: str) -> str:
    cleaned = text.replace("\u200b", " ").lower()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def token_set(text: str) -> set[str]:
    norm = normalize_text(text)
    return set(norm.split()) if norm else set()


def overlap_chars(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def char_iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    ov = overlap_chars(a_start, a_end, b_start, b_end)
    if ov == 0:
        return 0.0
    union = max(a_end, b_end) - min(a_start, b_start)
    return ov / union if union > 0 else 0.0


def prf1(tp: int, fp: int, fn: int) -> dict[str, Any]:
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
    }


def in_doc053_hackathon_region(start: int, end: int) -> bool:
    return any(overlap_chars(start, end, r_s, r_e) > 0 for r_s, r_e in DOC_053_HACKATHON_RANGES)


def classify_pair(pred: dict[str, Any], gt: dict[str, Any]) -> tuple[str, dict[str, float]]:
    p_s, p_e = pred["source_char_start"], pred["source_char_end"]
    g_s, g_e = gt["source_char_start"], gt["source_char_end"]
    ov = overlap_chars(p_s, p_e, g_s, g_e)
    iou = char_iou(p_s, p_e, g_s, g_e)

    p_toks = token_set(pred["evidence_text"])
    g_toks = token_set(gt["evidence_text"])
    inter = len(p_toks & g_toks)
    union = len(p_toks | g_toks)
    jaccard = inter / union if union > 0 else 0.0
    gt_cov = inter / len(g_toks) if g_toks else 0.0
    pred_cov = inter / len(p_toks) if p_toks else 0.0

    metrics = {
        "overlap_chars": ov,
        "char_iou": round(iou, 4),
        "token_jaccard": round(jaccard, 4),
        "gt_token_coverage": round(gt_cov, 4),
        "pred_token_coverage": round(pred_cov, 4),
    }

    same_cat = pred["requirement_category"] == gt["requirement_category"]
    p_norm = normalize_text(pred["evidence_text"])
    g_norm = normalize_text(gt["evidence_text"])

    if same_cat:
        if iou >= 0.85 or (p_norm and p_norm == g_norm):
            return "exact_match", metrics
        if iou >= 0.40 or gt_cov >= 0.60 or (ov > 0 and pred_cov >= 0.70 and jaccard >= 0.35):
            return "semantic_match", metrics
        if ov > 0 or jaccard >= 0.25:
            return "partial_match", metrics
        return "no_match", metrics
    else:
        if ov > 0 or jaccard >= 0.25:
            return "category_error", metrics
        return "no_match", metrics


def main() -> None:
    # 1. Pre-evaluation freeze & hash verification
    gt_path = FROZEN_CODE_AND_DATA_FILES["ground_truth_v1_0"]
    freeze_path = FROZEN_CODE_AND_DATA_FILES["ground_truth_freeze_manifest"]

    gt_data = json.loads(gt_path.read_text(encoding="utf-8"))
    freeze_data = json.loads(freeze_path.read_text(encoding="utf-8"))

    pre_hashes = {name: sha256_file(p) for name, p in FROZEN_CODE_AND_DATA_FILES.items()}
    input_doc_hashes = {}
    for doc_id, meta in gt_data["documents"].items():
        p = RAW_TXT_DIR / meta["filename"]
        input_doc_hashes[doc_id] = {"filename": meta["filename"], "sha256": sha256_file(p)}

    canon_gt_sha = hashlib.sha256(
        json.dumps(gt_data["annotations"], sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    assert pre_hashes["ground_truth_v1_0"] == freeze_data["ground_truth_file_sha256"], (
        "Ground truth file SHA-256 mismatch before evaluation!"
    )
    assert canon_gt_sha == freeze_data["annotations_canonical_sha256"], (
        "Ground truth canonical annotations SHA-256 mismatch before evaluation!"
    )

    # 2. Partition GT per policy (Ketentuan 3)
    all_gt = gt_data["annotations"]
    ambiguous_ids = {a["annotation_id"] for a in all_gt if a["annotation_status"] == "ambiguous_needs_review"}
    scope_mismatch_ids = {"GT-DOC-053-004", "GT-DOC-053-009", "GT-DOC-053-011", "GT-DOC-053-013"}
    intersection_ids = ambiguous_ids & scope_mismatch_ids
    excluded_union_ids = ambiguous_ids | scope_mismatch_ids

    primary_gt = [a for a in all_gt if a["annotation_id"] not in excluded_union_ids]
    excluded_gt = [a for a in all_gt if a["annotation_id"] in excluded_union_ids]

    # 3. Run generic_parser on held-out docs (without modifying parser)
    raw_texts = {
        doc_id: (RAW_TXT_DIR / meta["filename"]).read_text(encoding="utf-8")
        for doc_id, meta in gt_data["documents"].items()
    }
    parsed_objs = parse_documents_by_ids(HELD_OUT_DOCS)
    predictions: list[dict[str, Any]] = []
    for r in parsed_objs:
        raw_t = raw_texts[r.document_id]
        provenance_ok = raw_t[r.source_char_start:r.source_char_end] == r.evidence_text
        predictions.append(
            {
                "requirement_id": r.requirement_id,
                "document_id": r.document_id,
                "branch_unit_id": r.branch_unit_id,
                "requirement_category": r.requirement_category,
                "requirement_subcategory": r.requirement_subcategory,
                "requirement_name": r.requirement_name,
                "requirement_description": r.requirement_description,
                "evidence_text": r.evidence_text,
                "source_char_start": r.source_char_start,
                "source_char_end": r.source_char_end,
                "source_page": r.source_page,
                "source_section": r.source_section,
                "statement_nature": r.statement_nature,
                "scope_level": r.scope_level,
                "provenance_valid": provenance_ok,
            }
        )

    # Separate predictions falling into excluded regions (ambiguous GT spans or DOC-053 Hackathon)
    excluded_gt_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for g in excluded_gt:
        excluded_gt_by_doc[g["document_id"]].append(g)

    in_scope_preds: list[dict[str, Any]] = []
    excluded_region_preds: list[dict[str, Any]] = []
    for p in predictions:
        doc_id = p["document_id"]
        is_hack = doc_id == "DOC-053" and in_doc053_hackathon_region(
            p["source_char_start"], p["source_char_end"]
        )
        overlaps_ambig = any(
            overlap_chars(
                p["source_char_start"], p["source_char_end"], g["source_char_start"], g["source_char_end"]
            )
            > 0
            and g["annotation_id"] in ambiguous_ids
            for g in excluded_gt_by_doc[doc_id]
        )
        if is_hack or overlaps_ambig:
            p_copy = dict(p)
            p_copy["excluded_reason"] = (
                "doc_053_hackathon_scope_mismatch" if is_hack else "overlaps_ambiguous_gt"
            )
            excluded_region_preds.append(p_copy)
        else:
            in_scope_preds.append(p)

    # 4. One-to-one greedy matching on in_scope_preds vs primary_gt
    tier_priority = {"exact_match": 3, "semantic_match": 2, "partial_match": 1}

    same_cat_candidates: list[tuple[tuple[int, float, float], dict[str, Any], dict[str, Any], str, dict[str, float]]] = []
    for p in in_scope_preds:
        if not p["provenance_valid"]:
            continue
        for g in primary_gt:
            if p["document_id"] != g["document_id"]:
                continue
            label, m = classify_pair(p, g)
            if label in tier_priority:
                score = (tier_priority[label], m["char_iou"], m["token_jaccard"])
                same_cat_candidates.append((score, p, g, label, m))

    same_cat_candidates.sort(key=lambda x: x[0], reverse=True)

    matched_pred_ids: set[str] = set()
    matched_gt_ids: set[str] = set()
    matched_pairs: list[dict[str, Any]] = []

    for _, p, g, label, m in same_cat_candidates:
        if p["requirement_id"] in matched_pred_ids or g["annotation_id"] in matched_gt_ids:
            continue
        matched_pred_ids.add(p["requirement_id"])
        matched_gt_ids.add(g["annotation_id"])
        matched_pairs.append(
            {
                "match_type": label,
                "document_id": p["document_id"],
                "prediction_id": p["requirement_id"],
                "annotation_id": g["annotation_id"],
                "predicted_category": p["requirement_category"],
                "gt_category": g["requirement_category"],
                "predicted_scope": p["scope_level"],
                "gt_scope": g["scope_level"],
                "scope_match": p["scope_level"] == g["scope_level"],
                "pred_span": [p["source_char_start"], p["source_char_end"]],
                "gt_span": [g["source_char_start"], g["source_char_end"]],
                "metrics": m,
                "gt_name": g["requirement_name"],
                "pred_name": p["requirement_name"],
            }
        )

    # Cross-category matching (category_error) on remaining unmatched
    cross_cat_candidates: list[tuple[tuple[float, float], dict[str, Any], dict[str, Any], dict[str, float]]] = []
    for p in in_scope_preds:
        if p["requirement_id"] in matched_pred_ids or not p["provenance_valid"]:
            continue
        for g in primary_gt:
            if g["annotation_id"] in matched_gt_ids or p["document_id"] != g["document_id"]:
                continue
            label, m = classify_pair(p, g)
            if label == "category_error":
                score = (m["char_iou"], m["token_jaccard"])
                cross_cat_candidates.append((score, p, g, m))

    cross_cat_candidates.sort(key=lambda x: x[0], reverse=True)
    category_errors: list[dict[str, Any]] = []
    for _, p, g, m in cross_cat_candidates:
        if p["requirement_id"] in matched_pred_ids or g["annotation_id"] in matched_gt_ids:
            continue
        matched_pred_ids.add(p["requirement_id"])
        matched_gt_ids.add(g["annotation_id"])
        category_errors.append(
            {
                "match_type": "category_error",
                "document_id": p["document_id"],
                "prediction_id": p["requirement_id"],
                "annotation_id": g["annotation_id"],
                "predicted_category": p["requirement_category"],
                "gt_category": g["requirement_category"],
                "predicted_scope": p["scope_level"],
                "gt_scope": g["scope_level"],
                "pred_span": [p["source_char_start"], p["source_char_end"]],
                "gt_span": [g["source_char_start"], g["source_char_end"]],
                "metrics": m,
                "gt_name": g["requirement_name"],
                "pred_evidence_preview": p["evidence_text"][:160],
            }
        )

    # Remaining unmatched in-scope predictions -> FP
    # Note: partial_match predictions are NOT TP in strict primary metrics, so they count as FP in strict mode
    # while being reported separately as partial_matches.
    primary_gt_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for g in primary_gt:
        primary_gt_by_doc[g["document_id"]].append(g)

    unmatched_fps: list[dict[str, Any]] = []
    unsupported_preds: list[dict[str, Any]] = []
    for p in in_scope_preds:
        if p["requirement_id"] in matched_pred_ids:
            continue
        if not p["provenance_valid"]:
            reason = "unsupported_by_evidence"
            unsupported_preds.append(p)
        else:
            overlaps_any_gt = any(
                overlap_chars(
                    p["source_char_start"], p["source_char_end"], g["source_char_start"], g["source_char_end"]
                )
                > 0
                for g in primary_gt_by_doc[p["document_id"]]
            )
            reason = "duplicate_or_fragment_of_gt" if overlaps_any_gt else "over_extracted_or_non_requirement"
        unmatched_fps.append(
            {
                "prediction_id": p["requirement_id"],
                "document_id": p["document_id"],
                "predicted_category": p["requirement_category"],
                "source_section": p["source_section"],
                "source_span": [p["source_char_start"], p["source_char_end"]],
                "fp_reason": reason,
                "evidence_preview": p["evidence_text"][:180],
            }
        )

    missed_gt = [
        {
            "annotation_id": g["annotation_id"],
            "document_id": g["document_id"],
            "requirement_category": g["requirement_category"],
            "requirement_name": g["requirement_name"],
            "scope_level": g["scope_level"],
            "source_span": [g["source_char_start"], g["source_char_end"]],
        }
        for g in primary_gt
        if g["annotation_id"] not in matched_gt_ids
    ]

    # Scope errors among all matched pairs (exact, semantic, partial, category_error)
    scope_errors = [
        m
        for m in matched_pairs
        if not m["scope_match"]
    ] + [
        {
            "match_type": "category_error",
            "document_id": c["document_id"],
            "prediction_id": c["prediction_id"],
            "annotation_id": c["annotation_id"],
            "predicted_scope": c["predicted_scope"],
            "gt_scope": c["gt_scope"],
        }
        for c in category_errors
        if c["predicted_scope"] != c["gt_scope"]
    ]

    # 5. Compute Metrics (Strict Primary: TP = exact_match + semantic_match)
    exact_matches = [m for m in matched_pairs if m["match_type"] == "exact_match"]
    semantic_matches = [m for m in matched_pairs if m["match_type"] == "semantic_match"]
    partial_matches = [m for m in matched_pairs if m["match_type"] == "partial_match"]

    tp_strict = len(exact_matches) + len(semantic_matches)
    fp_strict = len(in_scope_preds) - tp_strict
    fn_strict = len(primary_gt) - tp_strict
    overall_strict = prf1(tp_strict, fp_strict, fn_strict)

    tp_with_partial = tp_strict + len(partial_matches)
    fp_with_partial = len(in_scope_preds) - tp_with_partial
    fn_with_partial = len(primary_gt) - tp_with_partial
    overall_with_partial = prf1(tp_with_partial, fp_with_partial, fn_with_partial)

    # Per-category strict metrics
    per_category: dict[str, Any] = {}
    for cat in REQUIREMENT_CATEGORIES:
        c_exact = sum(1 for m in exact_matches if m["gt_category"] == cat)
        c_sem = sum(1 for m in semantic_matches if m["gt_category"] == cat)
        c_part = sum(1 for m in partial_matches if m["gt_category"] == cat)
        c_tp = c_exact + c_sem
        c_pred_total = sum(1 for p in in_scope_preds if p["requirement_category"] == cat)
        c_gt_total = sum(1 for g in primary_gt if g["requirement_category"] == cat)
        c_fp = c_pred_total - c_tp
        c_fn = c_gt_total - c_tp
        per_category[cat] = {
            **prf1(c_tp, c_fp, c_fn),
            "gt_count": c_gt_total,
            "in_scope_pred_count": c_pred_total,
            "exact_match": c_exact,
            "semantic_match": c_sem,
            "partial_match": c_part,
            "category_errors_missed_from_gt": sum(1 for c in category_errors if c["gt_category"] == cat),
            "category_errors_predicted_into": sum(1 for c in category_errors if c["predicted_category"] == cat),
        }

    # Per-document strict metrics
    per_document: dict[str, Any] = {}
    for doc_id in HELD_OUT_DOCS:
        d_exact = sum(1 for m in exact_matches if m["document_id"] == doc_id)
        d_sem = sum(1 for m in semantic_matches if m["document_id"] == doc_id)
        d_part = sum(1 for m in partial_matches if m["document_id"] == doc_id)
        d_tp = d_exact + d_sem
        d_pred_total = sum(1 for p in in_scope_preds if p["document_id"] == doc_id)
        d_gt_total = sum(1 for g in primary_gt if g["document_id"] == doc_id)
        d_fp = d_pred_total - d_tp
        d_fn = d_gt_total - d_tp
        per_document[doc_id] = {
            **prf1(d_tp, d_fp, d_fn),
            "gt_primary_count": d_gt_total,
            "total_raw_predictions": sum(1 for p in predictions if p["document_id"] == doc_id),
            "excluded_region_predictions": sum(1 for p in excluded_region_preds if p["document_id"] == doc_id),
            "in_scope_pred_count": d_pred_total,
            "exact_match": d_exact,
            "semantic_match": d_sem,
            "partial_match": d_part,
            "category_errors": sum(1 for c in category_errors if c["document_id"] == doc_id),
        }

    # 6. Post-evaluation hash verification
    post_hashes = {name: sha256_file(p) for name, p in FROZEN_CODE_AND_DATA_FILES.items()}
    assert pre_hashes == post_hashes, "Frozen code or ground truth changed during evaluation!"

    eval_payload = {
        "stage": "4.4",
        "artifact_type": "blind_held_out_evaluation",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_status": "BLIND_EVALUATION_COMPLETED_WITH_LIMITATIONS",
        "matching_config": MATCHING_CONFIG,
        "ground_truth_partition": {
            "total_gt_v1_0": len(all_gt),
            "ambiguous_needs_review_count": len(ambiguous_ids),
            "ambiguous_needs_review_ids": sorted(ambiguous_ids),
            "doc_053_hackathon_scope_mismatch_count": len(scope_mismatch_ids),
            "doc_053_hackathon_scope_mismatch_ids": sorted(scope_mismatch_ids),
            "intersection_count": len(intersection_ids),
            "intersection_ids": sorted(intersection_ids),
            "total_excluded_union_count": len(excluded_union_ids),
            "primary_evaluation_gt_count": len(primary_gt),
        },
        "prediction_partition": {
            "total_raw_predictions": len(predictions),
            "excluded_region_predictions_count": len(excluded_region_preds),
            "in_scope_predictions_count": len(in_scope_preds),
            "provenance_valid_count": sum(1 for p in predictions if p["provenance_valid"]),
            "unsupported_by_evidence_count": len(unsupported_preds),
        },
        "overall_metrics_strict_primary": {
            **overall_strict,
            "exact_match": len(exact_matches),
            "semantic_match": len(semantic_matches),
            "partial_match_excluded_from_tp": len(partial_matches),
            "category_errors": len(category_errors),
            "scope_errors_among_matched": len(scope_errors),
        },
        "overall_metrics_sensitivity_including_partial": overall_with_partial,
        "per_category_metrics": per_category,
        "per_document_metrics": per_document,
        "fp_reason_breakdown": dict(Counter(fp["fp_reason"] for fp in unmatched_fps)),
        "matched_pairs": matched_pairs,
        "category_errors": category_errors,
        "scope_errors": scope_errors,
        "missed_requirements": missed_gt,
        "unmatched_false_positives": unmatched_fps,
        "excluded_gt_records": [
            {
                "annotation_id": g["annotation_id"],
                "document_id": g["document_id"],
                "requirement_category": g["requirement_category"],
                "requirement_name": g["requirement_name"],
                "in_ambiguous": g["annotation_id"] in ambiguous_ids,
                "in_scope_mismatch": g["annotation_id"] in scope_mismatch_ids,
            }
            for g in excluded_gt
        ],
        "excluded_region_predictions": [
            {
                "requirement_id": p["requirement_id"],
                "document_id": p["document_id"],
                "requirement_category": p["requirement_category"],
                "excluded_reason": p["excluded_reason"],
                "source_span": [p["source_char_start"], p["source_char_end"]],
            }
            for p in excluded_region_preds
        ],
    }

    eval_json_path = PROCESSED_DIR / "stage_4_4_blind_evaluation.json"
    eval_json_path.write_text(
        json.dumps(eval_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Write CSV summary (overall + per_category + per_document)
    eval_csv_path = PROCESSED_DIR / "stage_4_4_blind_evaluation.csv"
    with eval_csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "group_type",
                "group_name",
                "gt_count",
                "in_scope_pred_count",
                "tp",
                "fp",
                "fn",
                "precision",
                "recall",
                "f1",
                "exact_match",
                "semantic_match",
                "partial_match",
                "category_errors",
            ]
        )
        writer.writerow(
            [
                "overall",
                "strict_primary",
                len(primary_gt),
                len(in_scope_preds),
                overall_strict["tp"],
                overall_strict["fp"],
                overall_strict["fn"],
                overall_strict["precision"],
                overall_strict["recall"],
                overall_strict["f1"],
                len(exact_matches),
                len(semantic_matches),
                len(partial_matches),
                len(category_errors),
            ]
        )
        for cat, m in per_category.items():
            writer.writerow(
                [
                    "category",
                    cat,
                    m["gt_count"],
                    m["in_scope_pred_count"],
                    m["tp"],
                    m["fp"],
                    m["fn"],
                    m["precision"],
                    m["recall"],
                    m["f1"],
                    m["exact_match"],
                    m["semantic_match"],
                    m["partial_match"],
                    m["category_errors_missed_from_gt"],
                ]
            )
        for doc_id, m in per_document.items():
            writer.writerow(
                [
                    "document",
                    doc_id,
                    m["gt_primary_count"],
                    m["in_scope_pred_count"],
                    m["tp"],
                    m["fp"],
                    m["fn"],
                    m["precision"],
                    m["recall"],
                    m["f1"],
                    m["exact_match"],
                    m["semantic_match"],
                    m["partial_match"],
                    m["category_errors"],
                ]
            )

    # Write parser freeze manifest
    manifest_payload = {
        "stage": "4.4",
        "artifact_type": "parser_and_evaluation_freeze_manifest",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_info": get_git_info(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": get_dependencies(),
        "frozen_file_sha256_pre": pre_hashes,
        "frozen_file_sha256_post": post_hashes,
        "all_frozen_files_unchanged": pre_hashes == post_hashes,
        "ground_truth_canonical_sha256_verified": canon_gt_sha,
        "input_documents_sha256": input_doc_hashes,
        "evaluation_config_snapshot": {
            "held_out_documents": HELD_OUT_DOCS,
            "matching_config": MATCHING_CONFIG,
            "excluded_gt_union_count": len(excluded_union_ids),
            "primary_gt_count": len(primary_gt),
        },
    }
    manifest_path = PROCESSED_DIR / "stage_4_4_parser_freeze_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("Overall Strict Primary:", overall_strict)
    print("Exact / Semantic / Partial / CatErr:", len(exact_matches), len(semantic_matches), len(partial_matches), len(category_errors))
    print("Sensitivity (+Partial):", overall_with_partial)
    print("Scope errors:", len(scope_errors))
    print("FP reasons:", dict(Counter(fp["fp_reason"] for fp in unmatched_fps)))
    print("Unsupported preds:", len(unsupported_preds))
    for cat, m in per_category.items():
        print(f"  CAT {cat}: P={m['precision']} R={m['recall']} F1={m['f1']} (TP={m['tp']} FP={m['fp']} FN={m['fn']} part={m['partial_match']})")
    for doc_id, m in per_document.items():
        print(f"  DOC {doc_id}: P={m['precision']} R={m['recall']} F1={m['f1']} (TP={m['tp']} FP={m['fp']} FN={m['fn']} part={m['partial_match']} excl={m['excluded_region_predictions']})")


if __name__ == "__main__":
    main()
