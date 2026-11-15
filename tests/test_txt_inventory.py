"""Automated tests for Stage 1 TXT Document Inventory (`txt_inventory.py`)."""

import csv
import json
from pathlib import Path

from src.document_processing.txt_inventory import (
    DEFAULT_TXT_DIR,
    TxtDocumentInventorizer,
)


def test_all_80_raw_txt_files_processed():
    """Verify all 80 TXT files in data/raw/txt/ are read and inventoried without error."""
    txt_files_on_disk = sorted(DEFAULT_TXT_DIR.glob("*.txt"))
    assert len(txt_files_on_disk) == 80

    items, summary = TxtDocumentInventorizer.build_inventory(DEFAULT_TXT_DIR)

    assert len(items) == 80
    assert summary.total_documents == 80
    assert summary.unreadable_or_error_documents == 0

    # Verify required fields are populated on every item
    required_keys = {
        "document_id",
        "file_name",
        "document_name",
        "character_count",
        "word_count",
        "readability_status",
        "document_type",
        "competition_branch",
        "classification_status",
        "notes",
    }
    for item in items:
        item_dict = item.to_dict()
        assert required_keys.issubset(item_dict.keys())
        assert item.document_id.startswith("DOC-")
        assert item.file_name.endswith(".txt")


def test_empty_file_not_guessed_from_filename():
    """Verify empty file 'Guidebook BPC TSF 2026.txt' is marked unknown/empty, not guessed from filename."""
    items, summary = TxtDocumentInventorizer.build_inventory(DEFAULT_TXT_DIR)
    empty_items = [i for i in items if i.file_name == "Guidebook BPC TSF 2026.txt"]
    assert len(empty_items) == 1

    empty_doc = empty_items[0]
    assert empty_doc.character_count == 0
    assert empty_doc.word_count == 0
    assert empty_doc.readability_status == "empty"
    assert empty_doc.document_name == "unknown"
    assert empty_doc.document_type == "unknown"
    assert empty_doc.competition_branch == "unknown"
    assert empty_doc.classification_status == "unclassified"
    assert summary.empty_documents == 1


def test_filename_vs_content_discrepancy_flagged():
    """Verify swapped filenames ('HACKATHON GUIDEBOOK.txt' & 'STEM GUIDEBOOK.txt') are detected via content."""
    items, _ = TxtDocumentInventorizer.build_inventory(DEFAULT_TXT_DIR)
    by_name = {i.file_name: i for i in items}

    hack_file = by_name["HACKATHON GUIDEBOOK.txt"]
    assert "STEM" in hack_file.competition_branch
    assert hack_file.classification_status == "needs_review"

    stem_file = by_name["STEM GUIDEBOOK.txt"]
    assert "Hackathon" in stem_file.competition_branch
    assert stem_file.classification_status == "needs_review"


def test_idempotent_rerun_does_not_duplicate_data(tmp_path: Path):
    """Verify running the inventory process multiple times overwrites cleanly without duplicating rows."""
    csv_out = tmp_path / "document_inventory.csv"
    json_out = tmp_path / "document_inventory.json"

    # Run 1
    TxtDocumentInventorizer.run(
        txt_dir=DEFAULT_TXT_DIR, csv_path=csv_out, json_path=json_out
    )
    # Run 2 (Re-run on same output paths)
    TxtDocumentInventorizer.run(
        txt_dir=DEFAULT_TXT_DIR, csv_path=csv_out, json_path=json_out
    )

    with open(csv_out, "r", encoding="utf-8") as f_csv:
        rows = list(csv.DictReader(f_csv))
    assert len(rows) == 80
    assert len({r["document_id"] for r in rows}) == 80
    assert len({r["file_name"] for r in rows}) == 80

    with open(json_out, "r", encoding="utf-8") as f_json:
        payload = json.load(f_json)
    assert payload["summary"]["total_documents"] == 80
    assert len(payload["documents"]) == 80
