#!/usr/bin/env python3
"""CLI script to run Stage 2 Inventory Audit, Validation & Competition Taxonomy Mapping."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.document_processing.inventory_validator import validate_inventory


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    raw_txt_dir = PROJECT_ROOT / "data" / "raw" / "txt"
    initial_inventory_json = PROJECT_ROOT / "data" / "processed" / "document_inventory.json"
    taxonomy_json_path = (
        PROJECT_ROOT / "knowledge_base" / "competition_requirements" / "competition_taxonomy.json"
    )
    output_processed_taxonomy_json = PROJECT_ROOT / "data" / "processed" / "competition_taxonomy.json"
    output_validated_csv = PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.csv"
    output_validated_json = PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.json"
    output_audit_report_json = PROJECT_ROOT / "data" / "processed" / "inventory_audit_report.json"

    result = validate_inventory(
        raw_txt_dir=raw_txt_dir,
        initial_inventory_json=initial_inventory_json,
        taxonomy_json_path=taxonomy_json_path,
        output_validated_csv=output_validated_csv,
        output_validated_json=output_validated_json,
        output_audit_report_json=output_audit_report_json,
        output_processed_taxonomy_json=output_processed_taxonomy_json,
    )

    summary = result["summary"]
    print("=" * 72)
    print("STAGE 2: INVENTORY AUDIT & TAXONOMY VALIDATION SUMMARY")
    print("=" * 72)
    print(f"Total Documents Audited                  : {summary['total_documents_audited']}")
    print(f"Total Classification Changes             : {summary['total_classification_changed']}")
    print(f"  - document_type changed                : {summary['document_type_changed_count']}")
    print(f"  - competition_branch changed           : {summary['competition_branch_changed_count']}")
    print(f"Multi-Branch / Composite Documents       : {summary['multi_branch_documents_count']}")
    print(f"Single-Branch Documents                  : {summary['single_branch_documents_count']}")
    print(f"Non-Competition / Empty Documents        : {summary['non_competition_or_empty_count']}")
    print(f"Documents Needing Repair / Re-conversion : {summary['documents_requiring_repair_or_reconversion']}")
    print("-" * 72)
    print("Macro Document Category Breakdown:")
    for cat, count in summary["macro_document_category_breakdown"].items():
        print(f"  - {cat:40s}: {count}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
