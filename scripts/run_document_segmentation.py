#!/usr/bin/env python3
"""CLI script to run Stage 3 Document Segmentation into Competition Branch Units."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.document_processing.document_segmenter import segment_documents


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    raw_txt_dir = PROJECT_ROOT / "data" / "raw" / "txt"
    validated_inventory_json = PROJECT_ROOT / "data" / "processed" / "document_inventory_validated.json"
    taxonomy_json_path = PROJECT_ROOT / "data" / "processed" / "competition_taxonomy.json"
    output_units_json = PROJECT_ROOT / "data" / "processed" / "competition_branch_units.json"
    output_units_csv = PROJECT_ROOT / "data" / "processed" / "competition_branch_units.csv"

    result = segment_documents(
        raw_txt_dir=raw_txt_dir,
        validated_inventory_json=validated_inventory_json,
        taxonomy_json_path=taxonomy_json_path,
        output_units_json=output_units_json,
        output_units_csv=output_units_csv,
    )

    summary = result["summary"]
    print("=" * 72)
    print("STAGE 3: DOCUMENT SEGMENTATION SUMMARY")
    print("=" * 72)
    print(f"Total Parent Documents Inspected       : {summary['total_parent_documents_inspected']}")
    print(f"Segmented Competition Documents        : {summary['segmented_competition_documents_count']}")
    print(f"Excluded Non-Competition / Empty Docs  : {summary['excluded_non_competition_or_empty_documents_count']}")
    print(f"Total Branch Units Created             : {summary['total_branch_units_created']}")
    print(f"Branch Units with Explicit Page Range  : {summary['branch_units_with_explicit_page_range']}")
    print(f"Branch Units Flagged needs_review      : {summary['branch_units_needs_review_count']}")
    print("-" * 72)
    print("Branch Units by Parent multi_branch_type:")
    for mtype, count in summary["branch_units_by_multi_branch_type"].items():
        print(f"  - {mtype:40s}: {count}")
    print("-" * 72)
    print("Branch Units by segmentation_status:")
    for status, count in summary["branch_units_by_segmentation_status"].items():
        print(f"  - {status:40s}: {count}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
