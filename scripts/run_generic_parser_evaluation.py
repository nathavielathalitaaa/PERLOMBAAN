"""Stage 4.4 Parts C & D: Evaluate Generic Parser on Development & Blind Held-Out Datasets.

Outputs:
- data/processed/generic_parser_evaluation.json
- data/processed/generic_parser_evaluation.csv
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.requirement_extraction.generic_parser import ParsedRequirement, parse_documents_by_ids
from src.requirement_extraction.rules import REQUIREMENT_CATEGORIES

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
HELD_OUT_GT_PATH = PROCESSED_DIR / "held_out_ground_truth.json"
DEV_BASELINE_PATH = PROCESSED_DIR / "competition_requirements.json"
EVAL_JSON_PATH = PROCESSED_DIR / "generic_parser_evaluation.json"
EVAL_CSV_PATH = PROCESSED_DIR / "generic_parser_evaluation.csv"


def _norm_tokens(text: str) -> set[str]:
    cleaned = re.sub(r"[\u200b\u00a0\u2028\r]+", " ", text).lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return {t for t in cleaned.split() if len(t) >= 3}


def _span_overlap_ratio(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    if inter <= 0:
        return 0.0
    min_len = max(1, min(a_end - a_start, b_end - b_start))
    return inter / min_len


def _compute_match_score(pred: Dict[str, Any], gt: Dict[str, Any]) -> Tuple[bool, float, str]:
    """Check whether predicted requirement matches ground truth on category + provenance/semantics."""
    if pred["branch_unit_id"] != gt["branch_unit_id"]:
        return False, 0.0, "unit_mismatch"
    if pred["requirement_category"] != gt["requirement_category"]:
        return False, 0.0, "category_mismatch"

    span_ov = _span_overlap_ratio(
        int(pred["source_char_start"]),
        int(pred["source_char_end"]),
        int(gt["source_char_start"]),
        int(gt["source_char_end"]),
    )
    p_toks = _norm_tokens(pred["evidence_text"])
    g_toks = _norm_tokens(gt["evidence_text"])
    tok_jaccard = (len(p_toks & g_toks) / len(p_toks | g_toks)) if (p_toks and g_toks) else 0.0
    tok_recall = (len(p_toks & g_toks) / len(g_toks)) if g_toks else 0.0

    p_topics = set(pred.get("canonical_topics", []))
    g_topics = set(gt.get("canonical_topics", []))
    topic_ov = (len(p_topics & g_topics) / len(g_topics)) if g_topics else 0.0

    combined = max(span_ov, tok_jaccard, 0.7 * tok_recall, 0.65 * topic_ov)
    if span_ov >= 0.15 or tok_jaccard >= 0.22 or tok_recall >= 0.35 or (topic_ov >= 0.50 and tok_recall >= 0.18):
        reason = "span_overlap" if span_ov >= 0.15 else ("text_similarity" if tok_jaccard >= 0.22 or tok_recall >= 0.35 else "topic_overlap")
        return True, round(combined, 4), reason
    return False, round(combined, 4), "no_semantic_or_span_overlap"


def _prf(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    prec = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    rec = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
    }


def evaluate_predictions(
    preds: List[Dict[str, Any]],
    gts: List[Dict[str, Any]],
    doc_meta: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Run optimal greedy 1-to-1 matching between predictions and ground truth."""
    candidate_pairs: List[Tuple[float, int, int, str]] = []
    for pi, pred in enumerate(preds):
        for gi, gt in enumerate(gts):
            matched, score, reason = _compute_match_score(pred, gt)
            if matched:
                candidate_pairs.append((score, pi, gi, reason))

    candidate_pairs.sort(key=lambda x: x[0], reverse=True)
    matched_preds: Dict[int, Tuple[int, float, str]] = {}
    matched_gts: Dict[int, Tuple[int, float, str]] = {}

    for score, pi, gi, reason in candidate_pairs:
        if pi in matched_preds or gi in matched_gts:
            continue
        matched_preds[pi] = (gi, score, reason)
        matched_gts[gi] = (pi, score, reason)

    tp_records = []
    for pi, (gi, score, reason) in sorted(matched_preds.items()):
        tp_records.append(
            {
                "pred_id": preds[pi].get("requirement_id"),
                "gt_id": gts[gi].get("gt_id"),
                "document_id": gts[gi]["document_id"],
                "requirement_category": gts[gi]["requirement_category"],
                "gt_name": gts[gi].get("requirement_name"),
                "pred_name": preds[pi].get("requirement_name"),
                "match_score": score,
                "match_reason": reason,
            }
        )

    fp_records = [
        {
            "pred_id": preds[pi].get("requirement_id"),
            "document_id": preds[pi]["document_id"],
            "branch_unit_id": preds[pi]["branch_unit_id"],
            "requirement_category": preds[pi]["requirement_category"],
            "pred_name": preds[pi].get("requirement_name"),
            "source_section": preds[pi].get("source_section"),
            "evidence_preview": preds[pi]["evidence_text"][:200],
        }
        for pi in range(len(preds))
        if pi not in matched_preds
    ]

    fn_records = [
        {
            "gt_id": gts[gi].get("gt_id"),
            "document_id": gts[gi]["document_id"],
            "branch_unit_id": gts[gi]["branch_unit_id"],
            "requirement_category": gts[gi]["requirement_category"],
            "gt_name": gts[gi].get("requirement_name"),
            "source_section": gts[gi].get("source_section"),
            "evidence_preview": gts[gi]["evidence_text"][:200],
        }
        for gi in range(len(gts))
        if gi not in matched_gts
    ]

    overall = _prf(len(tp_records), len(fp_records), len(fn_records))

    # Per category
    by_category: Dict[str, Any] = {}
    for cat in REQUIREMENT_CATEGORIES:
        c_tp = sum(1 for r in tp_records if r["requirement_category"] == cat)
        c_fp = sum(1 for r in fp_records if r["requirement_category"] == cat)
        c_fn = sum(1 for r in fn_records if r["requirement_category"] == cat)
        by_category[cat] = _prf(c_tp, c_fp, c_fn)

    macro_f1 = round(sum(v["f1_score"] for v in by_category.values()) / len(REQUIREMENT_CATEGORIES), 4)
    overall["macro_f1_score"] = macro_f1

    # Per document
    by_document: Dict[str, Any] = {}
    all_docs = sorted({g["document_id"] for g in gts} | {p["document_id"] for p in preds})
    for doc_id in all_docs:
        d_tp = sum(1 for r in tp_records if r["document_id"] == doc_id)
        d_fp = sum(1 for r in fp_records if r["document_id"] == doc_id)
        d_fn = sum(1 for r in fn_records if r["document_id"] == doc_id)
        metrics = _prf(d_tp, d_fp, d_fn)
        metrics.update(doc_meta.get(doc_id, {}))
        by_document[doc_id] = metrics

    # Per document type
    by_doc_type: Dict[str, Any] = {}
    doc_types = sorted({m.get("document_structure_type", "unknown") for m in doc_meta.values()})
    for dt in doc_types:
        dt_docs = {d for d, m in doc_meta.items() if m.get("document_structure_type") == dt}
        dt_tp = sum(1 for r in tp_records if r["document_id"] in dt_docs)
        dt_fp = sum(1 for r in fp_records if r["document_id"] in dt_docs)
        dt_fn = sum(1 for r in fn_records if r["document_id"] in dt_docs)
        by_doc_type[dt] = _prf(dt_tp, dt_fp, dt_fn)

    return {
        "overall": overall,
        "by_category": by_category,
        "by_document": by_document,
        "by_document_type": by_doc_type,
        "true_positives": tp_records,
        "false_positives": fp_records,
        "false_negatives": fn_records,
    }


def _parsed_to_dict(r: ParsedRequirement) -> Dict[str, Any]:
    return {
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
        "evidence_type": r.evidence_type,
        "scope_level": r.scope_level,
        "canonical_topics": r.canonical_topics,
    }


def main() -> None:
    gt_payload = json.loads(HELD_OUT_GT_PATH.read_text(encoding="utf-8"))
    gt_list = gt_payload["ground_truth_requirements"]

    # Verify freeze integrity
    recomputed_sha = hashlib.sha256(
        json.dumps(gt_list, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert recomputed_sha == gt_payload["freeze_sha256"], "Held-out ground truth freeze digest mismatch!"

    held_out_docs_meta = {
        d["document_id"]: {
            "file_name": d["file_name"],
            "document_structure_type": d["document_structure_type"],
            "document_category": d["document_category"],
            "selection_criterion": d["selection_criterion"],
        }
        for d in gt_payload["dataset_split_manifest"]["blind_held_out_test_dataset"]["documents"]
    }
    held_out_doc_ids = list(held_out_docs_meta.keys())

    # 1. Run Generic Parser on Blind Held-Out Dataset
    held_out_parsed = [_parsed_to_dict(r) for r in parse_documents_by_ids(held_out_doc_ids)]
    held_out_eval = evaluate_predictions(held_out_parsed, gt_list, held_out_docs_meta)

    # 2. Run Generic Parser on Development Dataset (DOC-001, DOC-024, DOC-009) vs Stage 4.2 Curated Baseline
    dev_baseline = json.loads(DEV_BASELINE_PATH.read_text(encoding="utf-8"))
    dev_reqs = [r for r in dev_baseline["requirements"] if r["document_id"] in {"DOC-001", "DOC-024", "DOC-009"}]
    # Convert Stage 4.2 curated requirements into pseudo-GT format for development comparison
    dev_gt_proxy = [
        {
            "gt_id": r["requirement_id"],
            "document_id": r["document_id"],
            "branch_unit_id": r["branch_unit_id"],
            "requirement_category": r["requirement_category"],
            "requirement_name": r["requirement_name"],
            "evidence_text": r["evidence_text"],
            "source_char_start": r["source_char_start"],
            "source_char_end": r["source_char_end"],
            "source_section": r["source_section"],
            "canonical_topics": [],
        }
        for r in dev_reqs
    ]
    dev_meta = {
        "DOC-001": {"file_name": "Panduan Gemastik 2025.txt", "document_structure_type": "single_branch"},
        "DOC-024": {"file_name": "PEDOMAN-GEMASTIK-2024.txt", "document_structure_type": "multi_branch_event"},
        "DOC-009": {"file_name": "GUIDE BOOK LOMBA.txt", "document_structure_type": "multi_branch_event"},
    }
    dev_parsed = [_parsed_to_dict(r) for r in parse_documents_by_ids(["DOC-001", "DOC-024", "DOC-009"])]
    dev_generic_eval = evaluate_predictions(dev_parsed, dev_gt_proxy, dev_meta)

    output = {
        "stage": "stage_4_4_generic_parser_evaluation",
        "held_out_freeze_sha256": recomputed_sha,
        "dataset_split": gt_payload["dataset_split_manifest"],
        "blind_held_out_evaluation": held_out_eval,
        "development_comparison": {
            "stage_4_2_curated_baseline_record_count": len(dev_reqs),
            "stage_4_4_generic_parser_record_count": len(dev_parsed),
            "generic_parser_against_stage_4_2_curated_reference": dev_generic_eval["overall"],
            "by_document": dev_generic_eval["by_document"],
        },
        "held_out_extracted_requirements_count": len(held_out_parsed),
        "held_out_extracted_requirements": held_out_parsed,
    }

    EVAL_JSON_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Write CSV summary table
    rows: List[Dict[str, Any]] = []
    rows.append(
        {
            "scope": "held_out_overall",
            "key": "ALL_HELD_OUT",
            **held_out_eval["overall"],
        }
    )
    for doc_id, m in held_out_eval["by_document"].items():
        rows.append({"scope": "held_out_document", "key": doc_id, **m})
    for cat, m in held_out_eval["by_category"].items():
        rows.append({"scope": "held_out_category", "key": cat, **m})
    for dt, m in held_out_eval["by_document_type"].items():
        rows.append({"scope": "held_out_doc_type", "key": dt, **m})
    rows.append(
        {
            "scope": "dev_vs_stage4_2_ref",
            "key": "ALL_DEV",
            **dev_generic_eval["overall"],
        }
    )

    fieldnames = [
        "scope",
        "key",
        "tp",
        "fp",
        "fn",
        "precision",
        "recall",
        "f1_score",
        "macro_f1_score",
        "file_name",
        "document_structure_type",
        "document_category",
        "selection_criterion",
    ]
    with EVAL_CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    print("=== BLIND HELD-OUT EVALUATION (5 UNSEEN DOCS) ===")
    print("Overall:", held_out_eval["overall"])
    print("By Document:")
    for d, m in held_out_eval["by_document"].items():
        print(f"  {d} ({m.get('document_structure_type')}): P={m['precision']} R={m['recall']} F1={m['f1_score']} (TP={m['tp']} FP={m['fp']} FN={m['fn']})")
    print("By Category:")
    for c, m in held_out_eval["by_category"].items():
        print(f"  {c}: P={m['precision']} R={m['recall']} F1={m['f1_score']} (TP={m['tp']} FP={m['fp']} FN={m['fn']})")
    print("=== DEVELOPMENT COMPARISON (vs Stage 4.2 Curated) ===")
    print("Dev Overall:", dev_generic_eval["overall"])


if __name__ == "__main__":
    main()
