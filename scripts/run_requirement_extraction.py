#!/usr/bin/env python3
"""CLI runner for Stage 4.2 Requirement Extraction and Quality Evaluation (3 Representative Docs)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.requirement_extraction.evaluator import evaluate_requirement_extraction
from src.requirement_extraction.extractor import extract_representative_requirements


def main() -> None:
    payload = extract_representative_requirements(PROJECT_ROOT, write_outputs=True)
    evaluation = evaluate_requirement_extraction(PROJECT_ROOT, write_output=True)
    print("=== Stage 4.2 Requirement Extraction Summary ===")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    print("\n=== Stage 4.2 Quality Evaluation (Overall Micro) ===")
    print(
        json.dumps(
            evaluation["before_vs_after_comparison"]["overall_micro"],
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
