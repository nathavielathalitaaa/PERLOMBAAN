#!/usr/bin/env python3
"""CLI runner for Stage 3 Semantic & Methodological Segmentation Validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.document_processing.segmentation_validator import run_segmentation_validation


def main() -> None:
    payload = run_segmentation_validation(PROJECT_ROOT, write_outputs=True)
    summary = payload["summary"]
    print("=== Stage 3 Segmentation Validation Summary ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
