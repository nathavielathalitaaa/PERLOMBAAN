"""Tests for Stage 4.4 Generic Requirement Parser & Blind Held-Out Evaluation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERIC_PARSER_PATH = PROJECT_ROOT / "src" / "requirement_extraction" / "generic_parser.py"
HELD_OUT_GT_PATH = PROJECT_ROOT / "data" / "processed" / "held_out_ground_truth.json"
EVAL_JSON_PATH = PROJECT_ROOT / "data" / "processed" / "generic_parser_evaluation.json"
EVAL_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "generic_parser_evaluation.csv"
REPORT_PATH = PROJECT_ROOT / "docs" / "research_notes" / "generic_parser_evaluation_report.md"
RAW_TXT_DIR = PROJECT_ROOT / "data" / "raw" / "txt"

REQUIRED_GT_FIELDS = {
    "document_id",
    "branch_unit_id",
    "requirement_category",
    "requirement_name",
    "requirement_description",
    "evidence_text",
    "source_char_start",
    "source_char_end",
    "source_page",
    "statement_nature",
    "evidence_type",
}


def test_generic_parser_has_no_document_id_hardcoding() -> None:
    src = GENERIC_PARSER_PATH.read_text(encoding="utf-8")
    assert not re.search(r"\bDOC-\d{3}\b", src), "generic_parser.py must not hardcode DOC-XXX identifiers"
    assert not re.search(r"_extract_doc\d+", src, re.IGNORECASE), "generic_parser.py must not use doc-specific extractors"


def test_held_out_ground_truth_frozen_and_verbatim() -> None:
    assert HELD_OUT_GT_PATH.exists()
    data = json.loads(HELD_OUT_GT_PATH.read_text(encoding="utf-8"))
    assert data["frozen_before_parser_development"] is True

    anns = data["ground_truth_requirements"]
    assert len(anns) == 53
    recomputed = hashlib.sha256(json.dumps(anns, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    assert recomputed == data["freeze_sha256"]

    doc_files = {
        d["document_id"]: d["file_name"]
        for d in data["dataset_split_manifest"]["blind_held_out_test_dataset"]["documents"]
    }
    assert set(doc_files.keys()) == {"DOC-002", "DOC-003", "DOC-016", "DOC-054", "DOC-063"}

    text_cache = {
        doc_id: (RAW_TXT_DIR / fname).read_text(encoding="utf-8")
        for doc_id, fname in doc_files.items()
    }
    for ann in anns:
        assert REQUIRED_GT_FIELDS.issubset(ann.keys())
        raw = text_cache[ann["document_id"]]
        s = int(ann["source_char_start"])
        e = int(ann["source_char_end"])
        assert 0 <= s < e <= len(raw)
        assert raw[s:e] == ann["evidence_text"]


def test_generic_parser_evaluation_outputs_and_provenance() -> None:
    assert EVAL_JSON_PATH.exists()
    assert EVAL_CSV_PATH.exists()
    assert REPORT_PATH.exists()

    ev_data = json.loads(EVAL_JSON_PATH.read_text(encoding="utf-8"))
    gt_data = json.loads(HELD_OUT_GT_PATH.read_text(encoding="utf-8"))
    assert ev_data["held_out_freeze_sha256"] == gt_data["freeze_sha256"]

    overall = ev_data["blind_held_out_evaluation"]["overall"]
    assert overall["tp"] + overall["fn"] == 53
    assert overall["tp"] + overall["fp"] == ev_data["held_out_extracted_requirements_count"]
    assert 0.0 <= overall["precision"] <= 1.0
    assert 0.0 <= overall["recall"] <= 1.0
    assert 0.0 <= overall["f1_score"] <= 1.0

    doc_files = {
        d["document_id"]: d["file_name"]
        for d in gt_data["dataset_split_manifest"]["blind_held_out_test_dataset"]["documents"]
    }
    text_cache = {
        doc_id: (RAW_TXT_DIR / fname).read_text(encoding="utf-8")
        for doc_id, fname in doc_files.items()
    }
    for req in ev_data["held_out_extracted_requirements"]:
        raw = text_cache[req["document_id"]]
        s = int(req["source_char_start"])
        e = int(req["source_char_end"])
        assert raw[s:e] == req["evidence_text"]
