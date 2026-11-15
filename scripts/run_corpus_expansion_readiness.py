#!/usr/bin/env python3
"""CLI runner for Stage 4.3: Baseline Evaluation & Corpus Expansion Readiness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.requirement_extraction.readiness import evaluate_corpus_expansion_readiness


def main() -> None:
    payload = evaluate_corpus_expansion_readiness(PROJECT_ROOT, write_outputs=True)
    print("=== Stage 4.3 Corpus Expansion Readiness Summary ===")
    print("Overall Readiness Status:", payload["overall_readiness_status"])
    print("Conditional Status:", payload["conditional_restricted_status"])
    print(
        "\nAutomated vs Semantic Validation:",
        json.dumps(
            payload["separation_of_automated_vs_semantic_validation"],
            indent=2,
            ensure_ascii=False,
        ),
    )
    print(
        "\nWave Summary:",
        json.dumps(
            payload["6_staged_expansion_strategy"]["wave_summary"],
            indent=2,
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()
