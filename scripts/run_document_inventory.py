"""Execution script for Stage 1 TXT Document Inventory.

Scans `data/raw/txt/`, builds a content-verified inventory without modifying
any source TXT files, saves idempotent outputs to:
- `data/processed/document_inventory.csv`
- `data/processed/document_inventory.json`
and prints a statistical summary report.
"""

import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import LOG_FORMAT, LOG_LEVEL
from src.document_processing.txt_inventory import (
    DEFAULT_CSV_OUTPUT,
    DEFAULT_JSON_OUTPUT,
    DEFAULT_TXT_DIR,
    TxtDocumentInventorizer,
)


def configure_logging() -> None:
    """Configure standard logging for inventory execution."""
    logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format=LOG_FORMAT)


def main() -> None:
    configure_logging()
    print("=" * 78)
    print("AI COMPETITION MENTOR - STAGE 1: TXT DOCUMENT INVENTORY")
    print("=" * 78)

    items, summary = TxtDocumentInventorizer.run(
        txt_dir=DEFAULT_TXT_DIR,
        csv_path=DEFAULT_CSV_OUTPUT,
        json_path=DEFAULT_JSON_OUTPUT,
    )

    print(f"\n[1] RINGKASAN STATISTIK DOKUMEN")
    print(f"    Total dokumen diproses             : {summary.total_documents}")
    print(f"    Dokumen terbaca bersih (readable)  : {summary.readable_documents}")
    print(f"    Dokumen terbaca dengan derau OCR   : {summary.readable_with_ocr_noise_documents}")
    print(f"    Dokumen kosong (empty)             : {summary.empty_documents}")
    print(f"    Dokumen gagal baca (error)         : {summary.unreadable_or_error_documents}")
    print(f"    Total karakter keseluruhan         : {summary.total_characters:,}")
    print(f"    Total kata keseluruhan             : {summary.total_words:,}")
    print(f"    Jumlah kata minimum (non-kosong)   : {summary.min_word_count_non_empty:,}")
    print(f"    Jumlah kata maksimum               : {summary.max_word_count:,}")
    print(f"    Rata-rata kata (non-kosong)        : {summary.avg_word_count_non_empty:,.2f}")

    print("\n[2] DISTRIBUSI STATUS KLASIFIKASI")
    for status, count in sorted(summary.classification_status_breakdown.items()):
        print(f"    - {status:<26}: {count}")

    print("\n[3] DISTRIBUSI JENIS DOKUMEN")
    for dtype, count in sorted(
        summary.document_type_breakdown.items(), key=lambda x: (-x[1], x[0])
    ):
        print(f"    - {dtype:<26}: {count}")

    print(f"\n[4] DOKUMEN KOSONG ATAU BERMASALAH / PERLU TINJAUAN ({len(summary.flagged_documents)} Dokumen)")
    for fdoc in summary.flagged_documents:
        print(
            f"    * [{fdoc['document_id']}] {fdoc['file_name']}\n"
            f"      Status Baca: {fdoc['readability_status']} | Klasifikasi: {fdoc['classification_status']} | "
            f"Kata: {fdoc['word_count']}\n"
            f"      Cabang     : {fdoc['competition_branch']}\n"
            f"      Catatan    : {fdoc['notes']}"
        )

    print("\n[5] OUTPUT FILE INVENTARIS")
    print(f"    CSV  : {DEFAULT_CSV_OUTPUT}")
    print(f"    JSON : {DEFAULT_JSON_OUTPUT}")
    print("=" * 78)


if __name__ == "__main__":
    main()
