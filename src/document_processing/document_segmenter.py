"""Stage 3: Document Segmentation into Competition Branch Units.

This module segments validated competition documents into discrete
`CompetitionBranchUnit` records so that requirements, stages, and evaluation
criteria from different branches in a multi-branch guidebook never mix during
subsequent information extraction.

Rules enforced:
- Raw TXT files (`data/raw/txt/`) and Stage 1/2 inventory files are never modified.
- Supports all 5 `multi_branch_type` classifications:
  1. `single_branch` -> 1 branch unit covering the competition document.
  2. `multi_branch_event` -> N separate branch units identified by Table of Contents,
     section headers, and structural boundaries (never by naive keyword occurrence).
  3. `composite_branch_competition` -> 1 unified composite competition unit that
     explicitly records all required component branches (`required_component_branches`)
     plus component deliverable breakdown.
  4. `primary_branch_with_multi_event_intro` -> 1 primary branch unit isolated to the
     specific branch section (excluding the general multi-event intro so other event
     branches do not pollute extraction).
  5. `non_competition_or_unclassified` -> Excluded from competition branch units
     (0 branch units created; logged in `excluded_documents`).
- Page ranges (`start_page`, `end_page`) are only populated when explicitly present
  in the document text or Table of Contents; never fabricated.
- Documents whose branch rules are interwoven or rely on external technical appendices
  are flagged with `needs_review = True`.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CompetitionBranchUnit:
    """Represents a segmented competition branch unit linked to a parent document."""

    branch_unit_id: str
    document_id: str
    file_name: str
    multi_branch_type: str
    branch_code: str
    required_component_branches: List[str] = field(default_factory=list)
    section_title: str = ""
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    start_char: int = 0
    end_char: int = 0
    char_length: int = 0
    evidence_text: str = ""
    evidence_type: str = "explicit"  # "explicit" | "inferred"
    confidence: float = 1.0
    needs_review: bool = False
    segmentation_status: str = "segmented_clean"
    segmentation_notes: str = ""

    def to_csv_dict(self) -> Dict[str, Any]:
        """Serialize unit to flat dictionary for CSV export."""
        data = asdict(self)
        data["required_component_branches"] = "|".join(self.required_component_branches)
        data["start_page"] = "" if self.start_page is None else self.start_page
        data["end_page"] = "" if self.end_page is None else self.end_page
        return data


def _clean_snippet(raw_text: str, start: int, end: int, max_len: int = 220) -> str:
    """Extract a normalized verbatim snippet from raw_text[start:end]."""
    sub = raw_text[max(0, start) : min(len(raw_text), end)].lstrip("\ufeff").strip()
    norm = re.sub(r"\s+", " ", sub)
    if len(norm) > max_len:
        return norm[:max_len].rstrip() + "..."
    return norm


def _find_anchor(raw_text: str, pattern: str, start_from: int = 0) -> Optional[int]:
    """Find character offset of a structural regex pattern in raw_text."""
    match = re.search(pattern, raw_text[start_from:], flags=re.IGNORECASE | re.MULTILINE)
    if match:
        return start_from + match.start()
    return None


def _detect_single_doc_page_span(raw_text: str) -> Tuple[Optional[int], Optional[int]]:
    """Detect explicit page numbers if present in TOC or page footers, without guessing."""
    # Check TOC style dotted page numbers: e.g. ".... 12"
    toc_pages: List[int] = []
    for m in re.finditer(r"\.{5,}\s*(\d{1,3})\b", raw_text[:6000]):
        val = int(m.group(1))
        if 1 <= val <= 250:
            toc_pages.append(val)
    if toc_pages:
        return 1, max(toc_pages)
    return None, None


# Structural segmentation definitions for the 17 `multi_branch_event` documents
# and 4 `primary_branch_with_multi_event_intro` documents.
MULTI_BRANCH_STRUCTURAL_SPECS: Dict[str, List[Dict[str, Any]]] = {
    # DOC-006: Booklet Firma Ceria 2025.txt (len=9869)
    "Booklet Firma Ceria 2025.txt": [
        {
            "branch_code": "BR_RELIGIOUS_ARTS",
            "section_title": "Lomba Tilawah Al-Qur'an — Deskripsi & Ketentuan Lomba Tilawah",
            "start_char_fixed": 5499,
            "end_char_fixed": 7430,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Dipisahkan berdasarkan subjudul bagian eksplisit 'LOMBA TILAWAH' hingga sebelum 'LOMBA PUISI ISLAMI'.",
        },
        {
            "branch_code": "BR_LITERARY_WRITING",
            "section_title": "Lomba Puisi Islami — Deskripsi & Ketentuan Lomba Puisi Islami",
            "start_char_fixed": 7430,
            "end_char_fixed": 9869,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Dipisahkan berdasarkan subjudul bagian eksplisit 'LOMBA PUISI ISLAMI' hingga akhir dokumen.",
        },
    ],
    # DOC-008: Booklet Literat Fest 2024.txt (len=9518)
    # Rules for Puisi and Cerpen are interwoven inside the same Syarat & Ketentuan section!
    "Booklet Literat Fest 2024.txt": [
        {
            "branch_code": "BR_LITERARY_WRITING",
            "section_title": "Sayembara Cipta Puisi — Syarat dan Ketentuan Terpadu (Puisi & Cerpen)",
            "start_char_fixed": 3228,
            "end_char_fixed": 9518,
            "start_page": 6,
            "end_page": 11,
            "evidence_type": "explicit",
            "confidence": 0.70,
            "needs_review": True,
            "segmentation_status": "needs_review_interwoven_sections",
            "segmentation_notes": (
                "NEEDS REVIEW: Ketentuan kategori Puisi dan Cerpen ditulis tercampur dalam satu bagian "
                "'Syarat dan Ketentuan' yang sama (contoh: 'Panjang karya puisi maksimal 16 baris dan cerpen maksimal 1200 kata'). "
                "Tidak memiliki bab terpisah sehingga memerlukan pemilahan kalimat saat ekstraksi persyaratan."
            ),
        },
        {
            "branch_code": "BR_LITERARY_WRITING",
            "section_title": "Sayembara Cipta Cerpen — Syarat dan Ketentuan Terpadu (Puisi & Cerpen)",
            "start_char_fixed": 3228,
            "end_char_fixed": 9518,
            "start_page": 6,
            "end_page": 11,
            "evidence_type": "explicit",
            "confidence": 0.70,
            "needs_review": True,
            "segmentation_status": "needs_review_interwoven_sections",
            "segmentation_notes": (
                "NEEDS REVIEW: Ketentuan kategori Cerpen dan Puisi ditulis tercampur dalam satu bagian "
                "'Syarat dan Ketentuan' yang sama (hlm. 6-11). Ditandai untuk pemeriksaan manual pada tahap ekstraksi."
            ),
        },
    ],
    # DOC-009: Booklet SMA_K Sederajat_Pharmacopeia 2026.txt (len=48658)
    "Booklet SMA_K Sederajat_Pharmacopeia 2026.txt": [
        {
            "branch_code": "BR_ESSAY",
            "section_title": "Essay Competition Pharmacopeia 2026 (SMA/K Sederajat)",
            "start_char_fixed": 3135,
            "end_char_fixed": 15328,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.94,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Bagian pertama Booklet Pharmacopeia 2026: Tabel Timeline, Ketentuan Umum, Subtema, Mekanisme, & Kriteria Penilaian Essay Competition.",
        },
        {
            "branch_code": "BR_SCIENCE_OLYMPIAD",
            "section_title": "Science Olympiad Pharmacopeia 2026 (SMA/K Sederajat)",
            "start_char_fixed": 15403,
            "end_char_fixed": 24614,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.94,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Bagian kedua Booklet Pharmacopeia 2026: Timeline, Ketentuan Peserta, Mekanisme Penyisihan/Semifinal/Final, & Silabus Science Olympiad.",
        },
        {
            "branch_code": "BR_POSTER_DESIGN",
            "section_title": "Digital Poster Competition Pharmacopeia 2026 (SMA/K Sederajat)",
            "start_char_fixed": 24640,
            "end_char_fixed": 37583,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.94,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Bagian ketiga Booklet Pharmacopeia 2026: Timeline, Ketentuan, Subtema, Mekanisme, & Kriteria Penilaian Digital Poster Competition.",
        },
        {
            "branch_code": "BR_VIDEO_FILM_PHOTO",
            "section_title": "Video Campaign Competition Pharmacopeia 2026 (SMA/K Sederajat)",
            "start_char_fixed": 37584,
            "end_char_fixed": 46547,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.94,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Bagian keempat Booklet Pharmacopeia 2026: Timeline, Ketentuan, Subtema, Mekanisme, & Kriteria Penilaian Video Campaign Competition.",
        },
    ],
    # DOC-015: FMIPA STEM Challenge.txt (len=7903)
    "FMIPA STEM Challenge.txt": [
        {
            "branch_code": "BR_SCIENTIFIC_PAPER",
            "required_component_branches": ["BR_SCIENTIFIC_PAPER", "BR_ESSAY", "BR_POSTER_DESIGN", "BR_SMART_QUIZ"],
            "section_title": "SCIENTA UGM 2026 (Esai, Karya Tulis Ilmiah/LKTI, Poster, dan Cerdas Cermat)",
            "start_char_fixed": 1005,
            "end_char_fixed": 1739,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.90,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sub-event 1 FMIPA STEM Challenge 2026: SCIENTA UGM 2026.",
        },
        {
            "branch_code": "BR_SCIENCE_OLYMPIAD",
            "section_title": "LMNas 37 UGM 2026 (Lomba Matematika Nasional ke-37)",
            "start_char_fixed": 1739,
            "end_char_fixed": 2589,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sub-event 2 FMIPA STEM Challenge 2026: LMNas 37 UGM 2026.",
        },
        {
            "branch_code": "BR_IOT_ROBOTICS",
            "section_title": "INSPIRE 2026 (Soccer Robot, Line Follower Robot, IoT Competition, Sumo Robot)",
            "start_char_fixed": 2589,
            "end_char_fixed": 3247,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sub-event 3 FMIPA STEM Challenge 2026: INSPIRE 2026.",
        },
        {
            "branch_code": "BR_DATA_SCIENCE",
            "required_component_branches": ["BR_CYBERSECURITY_CTF", "BR_COMP_PROGRAMMING_LOGIC", "BR_HACKATHON", "BR_DATA_SCIENCE"],
            "section_title": "JOINTS 2026 (Jogja Information Technology Sessions: CTF, Logic, Ideathon, Hackathon, Data Mining)",
            "start_char_fixed": 3247,
            "end_char_fixed": 4028,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.92,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sub-event 4 FMIPA STEM Challenge 2026: JOINTS 2026.",
        },
        {
            "branch_code": "BR_SCIENCE_OLYMPIAD",
            "section_title": "TOP COP (Top Challenge of Physics) UGM 2026 (Olimpiade Sains, Fisika & Astronomi)",
            "start_char_fixed": 4028,
            "end_char_fixed": 4847,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sub-event 5 FMIPA STEM Challenge 2026: TOP Challenge of Physics UGM 2026.",
        },
        {
            "branch_code": "BR_SCIENCE_OLYMPIAD",
            "section_title": "Olimpiade Kimia Nasional (OKN) 2026",
            "start_char_fixed": 4847,
            "end_char_fixed": 5851,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sub-event 6 FMIPA STEM Challenge 2026: Olimpiade Kimia Nasional (OKN) 2026.",
        },
        {
            "branch_code": "BR_ESSAY",
            "section_title": "Lomba Esai Nasional Kimia (LENK) 2026",
            "start_char_fixed": 5851,
            "end_char_fixed": 7023,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sub-event 7 FMIPA STEM Challenge 2026: Lomba Esai Nasional Kimia (LENK) 2026.",
        },
        {
            "branch_code": "BR_ACTUARIAL_CASE",
            "required_component_branches": ["BR_ACTUARIAL_CASE", "BR_INFOGRAPHIC"],
            "section_title": "ASiQ (Actuarial Science Quest) 2026 (Olimpiade Aktuaria, National Actuarial Case & Actuarial Infographics)",
            "start_char_fixed": 7023,
            "end_char_fixed": 7903,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sub-event 8 FMIPA STEM Challenge 2026: ASiQ (Actuarial Science Quest) 2026.",
        },
    ],
    # DOC-024: GUIDEBOOK IMPACTEERS UNIVERSITAS NEGERI SURABAYA.txt (len=24733)
    "GUIDEBOOK IMPACTEERS UNIVERSITAS NEGERI SURABAYA.txt": [
        {
            "branch_code": "BR_ESSAY",
            "section_title": "Cabang Lomba Esai (Essay Competition) Impacteers UNESA",
            "start_char_fixed": 4122,
            "end_char_fixed": 10785,
            "start_page": 2,
            "end_page": 10,
            "evidence_type": "explicit",
            "confidence": 0.98,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 2-10): Tema, Syarat & Ketentuan, Penulisan, Jadwal, Pendaftaran, & Skema Penilaian Cabang Esai.",
        },
        {
            "branch_code": "BR_BMC",
            "section_title": "Cabang Lomba Business Model Canvas (BMC) Impacteers UNESA",
            "start_char_fixed": 10785,
            "end_char_fixed": 17612,
            "start_page": 11,
            "end_page": 18,
            "evidence_type": "explicit",
            "confidence": 0.98,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 11-18): Tema, Syarat & Ketentuan, Penulisan, Jadwal, Pendaftaran, & Skema Penilaian Cabang BMC.",
        },
        {
            "branch_code": "BR_POSTER_DESIGN",
            "section_title": "Cabang Lomba Poster (Poster Competition) Impacteers UNESA",
            "start_char_fixed": 17612,
            "end_char_fixed": 24733,
            "start_page": 19,
            "end_page": 25,
            "evidence_type": "explicit",
            "confidence": 0.98,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 19-25): Tema, Syarat & Ketentuan, Desain Karya, Jadwal, Pendaftaran, & Skema Penilaian Cabang Poster.",
        },
    ],
    # DOC-027: GUIDEBOOK IT FEST 2026.txt (len=49430)
    "GUIDEBOOK IT FEST 2026.txt": [
        {
            "branch_code": "BR_SOFTWARE_DEV",
            "section_title": "Software Development Competition — IT Fest 2026 (A. Deskripsi Lomba s.d. M. Narahubung)",
            "start_char_fixed": 6868,
            "end_char_fixed": 15487,
            "start_page": 1,
            "end_page": 6,
            "evidence_type": "explicit",
            "confidence": 0.99,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 1-6): Bab lengkap Software Development Competition.",
        },
        {
            "branch_code": "BR_NETWORK_ADMIN",
            "section_title": "IT Network System Administration (ITNSA) — IT Fest 2026 (A. Deskripsi Lomba s.d. P. Narahubung)",
            "start_char_fixed": 15487,
            "end_char_fixed": 29905,
            "start_page": 7,
            "end_page": 18,
            "evidence_type": "explicit",
            "confidence": 0.99,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 7-18): Bab lengkap IT Network System Administration (ITNSA).",
        },
        {
            "branch_code": "BR_CYBERSECURITY_CTF",
            "section_title": "Capture The Flag (CTF) — IT Fest 2026 (A. Deskripsi Lomba s.d. J. Narahubung)",
            "start_char_fixed": 29905,
            "end_char_fixed": 43550,
            "start_page": 19,
            "end_page": 26,
            "evidence_type": "explicit",
            "confidence": 0.99,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 19-26): Bab lengkap Capture The Flag (CTF).",
        },
        {
            "branch_code": "BR_VIDEO_FILM_PHOTO",
            "section_title": "Short Movie Competition — IT Fest 2026 (A. Deskripsi Lomba s.d. M. Narahubung)",
            "start_char_fixed": 43550,
            "end_char_fixed": 49430,
            "start_page": 27,
            "end_page": 31,
            "evidence_type": "explicit",
            "confidence": 0.99,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 27-31): Bab lengkap Short Movie Competition.",
        },
    ],
    # DOC-046: Guidebook PJJ CHALLENGE Chapter II.txt (len=9943)
    "Guidebook PJJ CHALLENGE Chapter II.txt": [
        {
            "branch_code": "BR_SMART_QUIZ",
            "section_title": "Petunjuk Teknis 1: Brain Challenge Week — PJJ Challenge Chapter II",
            "start_char_fixed": 2776,
            "end_char_fixed": 3767,
            "start_page": 3,
            "end_page": 3,
            "evidence_type": "explicit",
            "confidence": 0.98,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 3): Petunjuk Teknis 1 Brain Challenge Week.",
        },
        {
            "branch_code": "BR_SCIENTIFIC_PAPER",
            "section_title": "Petunjuk Teknis 2: Short Paper — PJJ Challenge Chapter II",
            "start_char_fixed": 3767,
            "end_char_fixed": 6029,
            "start_page": 4,
            "end_page": 5,
            "evidence_type": "explicit",
            "confidence": 0.98,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 4-5): Petunjuk Teknis 2 Short Paper.",
        },
        {
            "branch_code": "BR_ESSAY",
            "section_title": "Petunjuk Teknis 3: Essay — PJJ Challenge Chapter II",
            "start_char_fixed": 6029,
            "end_char_fixed": 7881,
            "start_page": 6,
            "end_page": 7,
            "evidence_type": "explicit",
            "confidence": 0.98,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 6-7): Petunjuk Teknis 3 Essay.",
        },
        {
            "branch_code": "BR_VIDEO_FILM_PHOTO",
            "section_title": "Petunjuk Teknis 4: Catch the Moment — PJJ Challenge Chapter II",
            "start_char_fixed": 7881,
            "end_char_fixed": 9460,
            "start_page": 8,
            "end_page": 9,
            "evidence_type": "explicit",
            "confidence": 0.98,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 8-9): Petunjuk Teknis 4 Catch the Moment.",
        },
    ],
    # DOC-047: Guidebook Tahap Terpusat Pre-Event OGG FITB ITB 2026.txt (len=36745)
    "Guidebook Tahap Terpusat Pre-Event OGG FITB ITB 2026.txt": [
        {
            "branch_code": "BR_SMART_QUIZ",
            "section_title": "Rincian Perlombaan Tahap Terpusat: Smart Competition — Pre-Event OGG FITB ITB 2026",
            "start_char_fixed": 12046,
            "end_char_fixed": 22487,
            "start_page": 10,
            "end_page": 20,
            "evidence_type": "explicit",
            "confidence": 0.99,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 10-20): Ketentuan Partisipasi & Mekanisme Tahap Terpusat Smart Competition.",
        },
        {
            "branch_code": "BR_STEM_PROJECT",
            "section_title": "Rincian Perlombaan Tahap Terpusat: Science Project Competition — Pre-Event OGG FITB ITB 2026",
            "start_char_fixed": 22487,
            "end_char_fixed": 27475,
            "start_page": 21,
            "end_page": 25,
            "evidence_type": "explicit",
            "confidence": 0.99,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 21-25): Ketentuan Partisipasi & Mekanisme Tahap Terpusat Science Project Competition.",
        },
        {
            "branch_code": "BR_DEBATE_SPEECH",
            "section_title": "Rincian Perlombaan Tahap Terpusat: Geo Debate Competition — Pre-Event OGG FITB ITB 2026",
            "start_char_fixed": 27475,
            "end_char_fixed": 34477,
            "start_page": 26,
            "end_page": 32,
            "evidence_type": "explicit",
            "confidence": 0.99,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Sesuai Daftar Isi (hlm. 26-32): Ketentuan Partisipasi & Mekanisme Tahap Terpusat Geo Debate Competition.",
        },
        {
            "branch_code": "BR_POSTER_DESIGN",
            "required_component_branches": ["BR_POSTER_DESIGN", "BR_VIDEO_FILM_PHOTO", "BR_ESSAY", "BR_DEBATE_SPEECH"],
            "section_title": "Subtema Pre-Event OGG FITB ITB 2026 (Poster, Geo Video, Essay, English Speech — Tanpa Bab Tahap Terpusat)",
            "start_char_fixed": 4709,
            "end_char_fixed": 12037,
            "start_page": 5,
            "end_page": 9,
            "evidence_type": "explicit",
            "confidence": 0.75,
            "needs_review": True,
            "segmentation_status": "needs_review_partial_branch_info",
            "segmentation_notes": (
                "NEEDS REVIEW: Dokumen ini adalah Guidebook khusus Tahap Terpusat (Final Luring). "
                "Cabang Poster, Geo Video, Essay, dan English Speech hanya dicantumkan pada bagian Subtema Pre-Event (hlm. 5-9) "
                "dan tidak memiliki bab Rincian Perlombaan Tahap Terpusat di dokumen ini."
            ),
        },
    ],
    # DOC-061: NEW_GUIDEBOOK ENFORNATION 2026.txt (len=26262)
    "NEW_GUIDEBOOK ENFORNATION 2026.txt": [
        {
            "branch_code": "BR_SCIENTIFIC_PAPER",
            "section_title": "Tahap Penyisihan 2: Lomba Karya Tulis Ilmiah (LKTI) — ENFORNATION 2026",
            "start_char_fixed": 11322,
            "end_char_fixed": 16582,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.97,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Bagian J. Mekanisme Lomba Tahap Penyisihan — Subbab 2. Karya Tulis Ilmiah (LKTI).",
        },
        {
            "branch_code": "BR_VIDEO_FILM_PHOTO",
            "section_title": "Tahap Penyisihan 3: Cabang Videografi — ENFORNATION 2026",
            "start_char_fixed": 16582,
            "end_char_fixed": 21090,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.97,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Bagian J. Mekanisme Lomba Tahap Penyisihan — Subbab 3. Videografi.",
        },
        {
            "branch_code": "BR_SMART_QUIZ",
            "section_title": "Tahap Final 2: CBT (Computer Based Test) — ENFORNATION 2026",
            "start_char_fixed": 21634,
            "end_char_fixed": 23489,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.96,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Bagian Tahap Final — Subbab 2. CBT (Computer Based Test) bagi tim yang lolos seleksi LKTI.",
        },
        {
            "branch_code": "BR_ENG_CASE",
            "required_component_branches": ["BR_ENG_CASE", "BR_INFOGRAPHIC"],
            "section_title": "Tahap Final 3: Studi Kasus Lapangan & Presentasi Infografis — ENFORNATION 2026",
            "start_char_fixed": 23489,
            "end_char_fixed": 26091,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.96,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Bagian Tahap Final — Subbab 3. Studi Kasus Lapangan dengan luaran Infografis & Presentasi.",
        },
    ],
    # DOC-062: Panduan FIKSI 2026.txt (len=126598)
    "Panduan FIKSI 2026.txt": [
        {
            "branch_code": "BR_ENTREPRENEURSHIP_INNOVATION",
            "required_component_branches": ["BR_ENTREPRENEURSHIP_INNOVATION", "BR_BUSINESS_PLAN"],
            "section_title": "Ketentuan Umum, Mekanisme & Penilaian FIKSI 2026 (Kategori Rencana Usaha & Pengembangan Usaha - Bab I s.d. Bab VII)",
            "start_char_fixed": 13873,
            "end_char_fixed": 70881,
            "start_page": 7,
            "end_page": 35,
            "evidence_type": "explicit",
            "confidence": 0.96,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Kerangka aturan umum, mekanisme seleksi, dan rubrik penilaian FIKSI 2026 (Bab I-VII).",
        },
        {
            "branch_code": "BR_ENTREPRENEURSHIP_INNOVATION",
            "section_title": "Lampiran Deskripsi 11 Cabang Lomba FIKSI 2026 (1. Agribisnis s.d. 11. Seni Rupa dan Desain)",
            "start_char_fixed": 74271,
            "end_char_fixed": 124027,
            "start_page": 37,
            "end_page": 63,
            "evidence_type": "explicit",
            "confidence": 0.96,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Lampiran rincian karakteristik 11 bidang lomba wirausaha FIKSI 2026.",
        },
    ],
    # DOC-069: Panduan_FIKSI_SMA_MA_SMK 2025_.txt (len=93759)
    "Panduan_FIKSI_SMA_MA_SMK 2025_.txt": [
        {
            "branch_code": "BR_ENTREPRENEURSHIP_INNOVATION",
            "required_component_branches": ["BR_ENTREPRENEURSHIP_INNOVATION", "BR_BUSINESS_PLAN"],
            "section_title": "Ketentuan Umum, Mekanisme & Penilaian FIKSI 2025 (Kategori Rencana Usaha & Pengembangan Usaha - Bab I s.d. Bab VI)",
            "start_char_fixed": 7763,
            "end_char_fixed": 53156,
            "start_page": 6,
            "end_page": 29,
            "evidence_type": "explicit",
            "confidence": 0.96,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Kerangka aturan umum, mekanisme seleksi, dan penilaian FIKSI 2025 (Bab I-VI).",
        },
        {
            "branch_code": "BR_ENTREPRENEURSHIP_INNOVATION",
            "section_title": "Lampiran Deskripsi 11 Cabang Lomba FIKSI 2025 (1. Agribisnis s.d. 11. Seni Rupa dan Desain)",
            "start_char_fixed": 56532,
            "end_char_fixed": 91800,
            "start_page": 31,
            "end_page": 51,
            "evidence_type": "explicit",
            "confidence": 0.96,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Lampiran rincian karakteristik 11 bidang lomba wirausaha FIKSI 2025.",
        },
    ],
    # DOC-071: Pedoman FIKSI SMA SMK 2024.txt (len=124929)
    "Pedoman FIKSI SMA SMK 2024.txt": [
        {
            "branch_code": "BR_ENTREPRENEURSHIP_INNOVATION",
            "required_component_branches": ["BR_ENTREPRENEURSHIP_INNOVATION", "BR_BUSINESS_PLAN"],
            "section_title": "Pedoman Umum, Mekanisme & Ketentuan Khusus FIKSI 2024 (Bab I s.d. Bab V)",
            "start_char_fixed": 7288,
            "end_char_fixed": 42332,
            "start_page": 6,
            "end_page": 23,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Pedoman penyelenggaraan umum FIKSI SMA/MA & SMK 2024 (Bab I-V).",
        },
        {
            "branch_code": "BR_ENTREPRENEURSHIP_INNOVATION",
            "section_title": "Lampiran 1) Bidang Lomba Jenjang SMA/MA FIKSI 2024 (11 Bidang Industri Kreatif)",
            "start_char_fixed": 42924,
            "end_char_fixed": 105896,
            "start_page": 24,
            "end_page": 61,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Lampiran deskripsi teknis dan rubrik penilaian khusus jenjang SMA/MA FIKSI 2024.",
        },
        {
            "branch_code": "BR_ENTREPRENEURSHIP_INNOVATION",
            "section_title": "Lampiran 2) Bidang Lomba Jenjang SMK FIKSI 2024 (Manajemen Bisnis, Industri Kreatif, Teknologi Digital, dll.)",
            "start_char_fixed": 105896,
            "end_char_fixed": 124929,
            "start_page": 61,
            "end_page": 72,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Lampiran deskripsi teknis dan rubrik penilaian khusus jenjang SMK FIKSI 2024.",
        },
    ],
    # DOC-066: Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2024.txt (len=96772)
    "Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2024.txt": [
        {
            "branch_code": "BR_VOCATIONAL_LKS",
            "section_title": "Bab II.C Bidang dan Cabang Lomba — Daftar 6 Kelompok Bidang (37 Cabang Lomba LKS SMK 2024)",
            "start_char_fixed": 20619,
            "end_char_fixed": 23060,
            "start_page": 11,
            "end_page": 12,
            "evidence_type": "explicit",
            "confidence": 0.85,
            "needs_review": True,
            "segmentation_status": "needs_review_external_branch_specs",
            "segmentation_notes": (
                "NEEDS REVIEW: Memuat daftar 6 Kelompok Bidang dan 37 cabang lomba LKS SMK 2024 (hlm. 11-12), "
                "sedangkan spesifikasi proyek uji (Test Project) tiap cabang berada pada dokumen 'Deskripsi Teknis' terpisah."
            ),
        },
        {
            "branch_code": "BR_VOCATIONAL_LKS",
            "section_title": "Mekanisme, Norma & Ketentuan Penyelenggaraan Umum LKS SMK Tingkat Nasional 2024 (Bab II.D s.d. Bab IV)",
            "start_char_fixed": 23060,
            "end_char_fixed": 91264,
            "start_page": 12,
            "end_page": 45,
            "evidence_type": "explicit",
            "confidence": 0.85,
            "needs_review": True,
            "segmentation_status": "needs_review_external_branch_specs",
            "segmentation_notes": (
                "NEEDS REVIEW: Memuat ketentuan umum peserta, mekanisme, dan norma penyelenggaraan lintas cabang LKS 2024."
            ),
        },
    ],
    # DOC-067: Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2025 .txt (len=302962)
    "Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2025 .txt": [
        {
            "branch_code": "BR_VOCATIONAL_LKS",
            "section_title": "Panduan Penyelenggaraan Umum LKS Nasional 2025 (Bab I s.d. Bab IV)",
            "start_char_fixed": 5825,
            "end_char_fixed": 90751,
            "start_page": 5,
            "end_page": 52,
            "evidence_type": "explicit",
            "confidence": 0.96,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Ketentuan umum, mekanisme, dan norma penyelenggaraan LKS Nasional 2025 (hlm. 5-52).",
        },
        {
            "branch_code": "BR_VOCATIONAL_LKS",
            "section_title": "Lampiran Ruang Lingkup Keahlian 37 Bidang Lomba LKS Nasional 2025 (Kelompok Konstruksi, Rekayasa, TIK, Agribisnis, Pariwisata, Seni Kreatif)",
            "start_char_fixed": 90751,
            "end_char_fixed": 302962,
            "start_page": 53,
            "end_page": 179,
            "evidence_type": "explicit",
            "confidence": 0.96,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Tabel rincian Ruang Lingkup Keahlian untuk seluruh 37 bidang lomba LKS Nasional 2025 (hlm. 53-179).",
        },
    ],
    # DOC-068: Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2026.txt (len=84574)
    "Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2026.txt": [
        {
            "branch_code": "BR_VOCATIONAL_LKS",
            "section_title": "Bab II.C Bidang dan Cabang Lomba — Daftar 11 Bidang Keahlian & 37+1 Cabang Lomba LKS Dikmen 2026",
            "start_char_fixed": 19244,
            "end_char_fixed": 22150,
            "start_page": 10,
            "end_page": 12,
            "evidence_type": "explicit",
            "confidence": 0.85,
            "needs_review": True,
            "segmentation_status": "needs_review_external_branch_specs",
            "segmentation_notes": (
                "NEEDS REVIEW: Memuat daftar 37 bidang lomba dan 1 bidang ekshibisi (Kecerdasan Artifisial) pada hlm. 10-12, "
                "sedangkan rincian soal praktik tiap cabang diatur dalam dokumen 'Deskripsi Teknis' masing-masing bidang."
            ),
        },
        {
            "branch_code": "BR_VOCATIONAL_LKS",
            "section_title": "Mekanisme, Skema Penilaian & Norma Penyelenggaraan Umum LKS Dikmen Tingkat Nasional 2026 (Bab II.D s.d. Bab III)",
            "start_char_fixed": 22150,
            "end_char_fixed": 83224,
            "start_page": 12,
            "end_page": 37,
            "evidence_type": "explicit",
            "confidence": 0.85,
            "needs_review": True,
            "segmentation_status": "needs_review_external_branch_specs",
            "segmentation_notes": (
                "NEEDS REVIEW: Memuat ketentuan umum kesiapan lomba, mekanisme, skema penilaian CIS, dan norma penyelenggaraan LKS 2026."
            ),
        },
    ],
    # DOC-075: Sosialisasi LKS Dikmen 2025.txt (len=32521)
    "Sosialisasi LKS Dikmen 2025.txt": [
        {
            "branch_code": "BR_VOCATIONAL_LKS",
            "section_title": "Daftar Bidang dan 37+1 Cabang Lomba LKS Dikmen 2025 (Bidang Keahlian I s.d. XI)",
            "start_char_fixed": 4838,
            "end_char_fixed": 7290,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.75,
            "needs_review": True,
            "segmentation_status": "needs_review_external_branch_specs",
            "segmentation_notes": (
                "NEEDS REVIEW: Slide rekapitulasi 37 cabang lomba + 1 cabang ekshibisi LKS Dikmen 2025 tanpa rincian teknis per cabang."
            ),
        },
        {
            "branch_code": "BR_VOCATIONAL_LKS",
            "section_title": "Komposisi Proyek Uji, Ketentuan Umum, Mekanisme & Linimasa Sosialisasi LKS Dikmen 2025",
            "start_char_fixed": 7290,
            "end_char_fixed": 32521,
            "start_page": None,
            "end_page": None,
            "evidence_type": "explicit",
            "confidence": 0.75,
            "needs_review": True,
            "segmentation_status": "needs_review_external_branch_specs",
            "segmentation_notes": (
                "NEEDS REVIEW: Slide paparan komposisi proyek uji (30% softskill, 70% hardskill) dan jadwal umum LKS Dikmen 2025."
            ),
        },
    ],
    # DOC-076: Syarat & Ketentuan PIMA 2026.txt (len=10625)
    "Syarat & Ketentuan PIMA 2026.txt": [
        {
            "branch_code": "BR_JOURNALISM",
            "section_title": "Kategori Teks — Hard News (PIMA Pupuk Indonesia Media Awards 2026)",
            "start_char_fixed": 3444,
            "end_char_fixed": 4714,
            "start_page": 3,
            "end_page": 3,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Slide 3: Ketentuan khusus karya tulis jurnalistik kategori TEKS_HARD_NEWS.",
        },
        {
            "branch_code": "BR_JOURNALISM",
            "section_title": "Kategori Teks — Feature (PIMA Pupuk Indonesia Media Awards 2026)",
            "start_char_fixed": 4714,
            "end_char_fixed": 6026,
            "start_page": 4,
            "end_page": 4,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Slide 4: Ketentuan khusus karya tulis jurnalistik kategori TEKS_FEATURE.",
        },
        {
            "branch_code": "BR_JOURNALISM",
            "section_title": "Kategori Foto Cerita (PIMA Pupuk Indonesia Media Awards 2026)",
            "start_char_fixed": 6026,
            "end_char_fixed": 7699,
            "start_page": 5,
            "end_page": 5,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Slide 5: Ketentuan khusus karya jurnalistik kategori FOTO_CERITA (5-11 frame).",
        },
        {
            "branch_code": "BR_JOURNALISM",
            "section_title": "Kategori Jurnalistik Radio (PIMA Pupuk Indonesia Media Awards 2026)",
            "start_char_fixed": 7699,
            "end_char_fixed": 9145,
            "start_page": 6,
            "end_page": 6,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Slide 6: Ketentuan khusus karya jurnalistik kategori Radio (MP3 & transkrip .docx).",
        },
        {
            "branch_code": "BR_JOURNALISM",
            "section_title": "Kategori Jurnalistik Televisi (PIMA Pupuk Indonesia Media Awards 2026)",
            "start_char_fixed": 9145,
            "end_char_fixed": 10625,
            "start_page": 7,
            "end_page": 7,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": "Slide 7: Ketentuan khusus karya jurnalistik kategori TELEVISI (video berita minimal 1 menit 30 detik).",
        },
    ],
    # PRIMARY BRANCH WITH MULTI-EVENT INTRO (4 Documents: DOC-033, DOC-054, DOC-070, DOC-073)
    "Guidebook BCC MANIFEST 2026 (fixx).txt": [
        {
            "branch_code": "BR_BUSINESS_CASE",
            "section_title": "Business Case Competition (BCC) MANIFEST 2026 — Ketentuan Umum, Preliminary, Semifinal & Final Stage",
            "start_char_fixed": 4970,
            "end_char_fixed": 22813,
            "start_page": 5,
            "end_page": 18,
            "evidence_type": "explicit",
            "confidence": 0.95,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": (
                "Bagian pengantar umum MANIFEST 2026 (indeks 0..4970 yang menyebut BPC & EBPC) dipisahkan "
                "agar ekstraksi persyaratan berfokus murni pada cabang Business Case Competition (BCC)."
            ),
        },
    ],
    "HACKATHON GUIDEBOOK.txt": [
        {
            "branch_code": "BR_STEM_PROJECT",
            "required_component_branches": ["BR_STEM_PROJECT", "BR_IOT_ROBOTICS"],
            "section_title": "PE STEM Competition of Techtonic UI 3.0 — Connecting Lives through IoT",
            "start_char_fixed": 5101,
            "end_char_fixed": 15413,
            "start_page": 15,
            "end_page": 27,
            "evidence_type": "explicit",
            "confidence": 0.90,
            "needs_review": True,
            "segmentation_status": "needs_review_filename_mismatch",
            "segmentation_notes": (
                "NEEDS REVIEW (Filename Mismatch): Nama file adalah 'HACKATHON GUIDEBOOK.txt', tetapi bagian panduan spesifik "
                "(hlm. 15-27, indeks 5101..15413) adalah panduan PE STEM Competition ('Connecting Lives through IoT'). "
                "Bagian pengantar umum Techtonic UI 3.0 (0..5101) telah diisolasi."
            ),
        },
    ],
    "Pedoman EIC - PGTC 2026.txt": [
        {
            "branch_code": "BR_SCIENTIFIC_PAPER",
            "required_component_branches": ["BR_SCIENTIFIC_PAPER", "BR_STEM_PROJECT"],
            "section_title": "Pedoman Kompetisi Energynovation Ideas Competition (EIC) PGTC 2026 (Daftar Isi, Bab I-III & Lampiran 1-5)",
            "start_char_fixed": 3103,
            "end_char_fixed": 66490,
            "start_page": 2,
            "end_page": 46,
            "evidence_type": "explicit",
            "confidence": 0.98,
            "needs_review": False,
            "segmentation_status": "segmented_clean",
            "segmentation_notes": (
                "Bagian Kata Pengantar umum PGTC 2026 (hlm. 1, indeks 0..3103 yang menyebut Debat & Kompetisi Bisnis) "
                "diisolasi sehingga unit ini murni memuat Pedoman Energynovation Ideas Competition (hlm. 2-46)."
            ),
        },
    ],
    "STEM GUIDEBOOK.txt": [
        {
            "branch_code": "BR_HACKATHON",
            "required_component_branches": ["BR_HACKATHON", "BR_CYBERSECURITY_CTF"],
            "section_title": "Hackathon Competition of Techtonic UI 3.0 — STASH (Smart Technology and Security Hackathon)",
            "start_char_fixed": 5113,
            "end_char_fixed": 13768,
            "start_page": 28,
            "end_page": 38,
            "evidence_type": "explicit",
            "confidence": 0.90,
            "needs_review": True,
            "segmentation_status": "needs_review_filename_mismatch",
            "segmentation_notes": (
                "NEEDS REVIEW (Filename Mismatch): Nama file adalah 'STEM GUIDEBOOK.txt', tetapi bagian panduan spesifik "
                "(hlm. 28-38, indeks 5113..13768) adalah panduan Hackathon Competition ('STASH'). "
                "Bagian pengantar umum Techtonic UI 3.0 (0..5113) telah diisolasi."
            ),
        },
    ],
}


def segment_documents(
    raw_txt_dir: Path,
    validated_inventory_json: Path,
    taxonomy_json_path: Path,
    output_units_json: Path,
    output_units_csv: Path,
) -> Dict[str, Any]:
    """Segment all validated competition documents into discrete CompetitionBranchUnit records."""
    if not validated_inventory_json.exists():
        raise FileNotFoundError(f"Validated inventory JSON not found: {validated_inventory_json}")
    if not raw_txt_dir.exists():
        raise FileNotFoundError(f"Raw TXT directory not found: {raw_txt_dir}")
    if not taxonomy_json_path.exists():
        raise FileNotFoundError(f"Taxonomy JSON not found: {taxonomy_json_path}")

    validated_data = json.loads(validated_inventory_json.read_text(encoding="utf-8"))
    documents: List[Dict[str, Any]] = validated_data.get("documents", [])

    branch_units: List[CompetitionBranchUnit] = []
    excluded_documents: List[Dict[str, Any]] = []

    for doc in documents:
        doc_id = doc["document_id"]
        file_name = doc["file_name"]
        multi_type = doc["multi_branch_type"]
        macro_cat = doc["macro_document_category"]
        branch_codes: List[str] = doc.get("branch_codes", [])

        txt_path = raw_txt_dir / file_name
        raw_text = txt_path.read_text(encoding="utf-8", errors="replace") if txt_path.exists() else ""
        doc_len = len(raw_text)

        # Rule 13: Empty and non-competition documents must NOT be forced into competition branch units
        if multi_type == "non_competition_or_unclassified" or doc_len == 0 or not branch_codes:
            excluded_documents.append(
                {
                    "document_id": doc_id,
                    "file_name": file_name,
                    "macro_document_category": macro_cat,
                    "validated_document_type": doc["validated_document_type"],
                    "multi_branch_type": multi_type,
                    "readability_status": doc["readability_status"],
                    "exclusion_reason": doc["audit_reason"],
                }
            )
            continue

        # Case 1: `multi_branch_event` or `primary_branch_with_multi_event_intro`
        if multi_type in ("multi_branch_event", "primary_branch_with_multi_event_intro"):
            specs = MULTI_BRANCH_STRUCTURAL_SPECS.get(file_name)
            if not specs:
                raise KeyError(f"Missing structural segmentation spec for {multi_type} document: {file_name}")

            for idx, spec in enumerate(specs, start=1):
                unit_id = f"{doc_id}-BU-{idx:02d}"
                if "start_char_fixed" in spec:
                    start_char = int(spec["start_char_fixed"])
                else:
                    found_start = _find_anchor(raw_text, spec["start_anchor"], 0)
                    start_char = found_start if found_start is not None else 0

                if "end_char_fixed" in spec and spec["end_char_fixed"] is not None:
                    end_char = min(int(spec["end_char_fixed"]), doc_len)
                elif spec.get("end_anchor"):
                    found_end = _find_anchor(raw_text, spec["end_anchor"], start_char + 10)
                    end_char = found_end if found_end is not None else doc_len
                else:
                    end_char = doc_len

                start_char = max(0, min(start_char, doc_len - 1))
                end_char = max(start_char + 1, min(end_char, doc_len))

                req_components = list(spec.get("required_component_branches", [spec["branch_code"]]))
                evidence = _clean_snippet(raw_text, start_char, min(end_char, start_char + 450))

                unit = CompetitionBranchUnit(
                    branch_unit_id=unit_id,
                    document_id=doc_id,
                    file_name=file_name,
                    multi_branch_type=multi_type,
                    branch_code=spec["branch_code"],
                    required_component_branches=req_components,
                    section_title=spec["section_title"],
                    start_page=spec["start_page"],
                    end_page=spec["end_page"],
                    start_char=start_char,
                    end_char=end_char,
                    char_length=end_char - start_char,
                    evidence_text=evidence,
                    evidence_type=spec["evidence_type"],
                    confidence=float(spec["confidence"]),
                    needs_review=bool(spec["needs_review"]),
                    segmentation_status=spec["segmentation_status"],
                    segmentation_notes=spec["segmentation_notes"],
                )
                branch_units.append(unit)

        # Case 2: `composite_branch_competition` (Rule 9: record all required component branches in one competition)
        elif multi_type == "composite_branch_competition":
            unit_id = f"{doc_id}-BU-01"
            start_page, end_page = _detect_single_doc_page_span(raw_text)
            comp_str = ", ".join(branch_codes)
            unit = CompetitionBranchUnit(
                branch_unit_id=unit_id,
                document_id=doc_id,
                file_name=file_name,
                multi_branch_type=multi_type,
                branch_code=branch_codes[0],
                required_component_branches=list(branch_codes),
                section_title=f"{doc['document_name']} — Kompetisi Komposit ({ doc['validated_competition_branch'] })",
                start_page=start_page,
                end_page=end_page,
                start_char=0,
                end_char=doc_len,
                char_length=doc_len,
                evidence_text=doc["content_evidence"],
                evidence_type="explicit",
                confidence=0.96,
                needs_review=False,
                segmentation_status="segmented_composite",
                segmentation_notes=(
                    f"Kompetisi komposit tunggal yang mewajibkan integrasi {len(branch_codes)} komponen cabang "
                    f"sekaligus ({comp_str})."
                ),
            )
            branch_units.append(unit)

        # Case 3: `single_branch` (Rule 7: create one branch unit)
        elif multi_type == "single_branch":
            unit_id = f"{doc_id}-BU-01"
            start_page, end_page = _detect_single_doc_page_span(raw_text)
            is_catalog = macro_cat == "katalog_karya_atau_finalis"
            needs_rev = is_catalog
            seg_status = "needs_review_non_rulebook_catalog" if is_catalog else "segmented_clean"
            seg_notes = (
                "NEEDS REVIEW: Dokumen merupakan Katalog Profil Top 10 Tim Finalis (bukan buku panduan pendaftaran peserta)."
                if is_catalog
                else "Dokumen kompetisi cabang tunggal (1 dokumen = 1 unit cabang penuh)."
            )
            unit = CompetitionBranchUnit(
                branch_unit_id=unit_id,
                document_id=doc_id,
                file_name=file_name,
                multi_branch_type=multi_type,
                branch_code=branch_codes[0],
                required_component_branches=list(branch_codes),
                section_title=f"{doc['document_name']} — {doc['validated_competition_branch']}",
                start_page=start_page,
                end_page=end_page,
                start_char=0,
                end_char=doc_len,
                char_length=doc_len,
                evidence_text=doc["content_evidence"],
                evidence_type="explicit",
                confidence=0.80 if is_catalog else 0.98,
                needs_review=needs_rev,
                segmentation_status=seg_status,
                segmentation_notes=seg_notes,
            )
            branch_units.append(unit)

    # Build summary statistics
    by_multi_type: Dict[str, int] = {}
    by_branch_code: Dict[str, int] = {}
    by_seg_status: Dict[str, int] = {}
    for u in branch_units:
        by_multi_type[u.multi_branch_type] = by_multi_type.get(u.multi_branch_type, 0) + 1
        by_branch_code[u.branch_code] = by_branch_code.get(u.branch_code, 0) + 1
        by_seg_status[u.segmentation_status] = by_seg_status.get(u.segmentation_status, 0) + 1

    summary = {
        "total_parent_documents_inspected": len(documents),
        "segmented_competition_documents_count": len(documents) - len(excluded_documents),
        "excluded_non_competition_or_empty_documents_count": len(excluded_documents),
        "total_branch_units_created": len(branch_units),
        "branch_units_with_explicit_page_range": sum(1 for u in branch_units if u.start_page is not None),
        "branch_units_needs_review_count": sum(1 for u in branch_units if u.needs_review),
        "branch_units_by_multi_branch_type": by_multi_type,
        "branch_units_by_segmentation_status": by_seg_status,
        "branch_units_by_primary_branch_code": by_branch_code,
    }

    # Write JSON output
    output_units_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summary,
        "excluded_documents": excluded_documents,
        "branch_units": [asdict(u) for u in branch_units],
    }
    output_units_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write CSV output
    output_units_csv.parent.mkdir(parents=True, exist_ok=True)
    if branch_units:
        fieldnames = list(branch_units[0].to_csv_dict().keys())
        with output_units_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for u in branch_units:
                writer.writerow(u.to_csv_dict())

    logger.info(
        "Segmented %d competition documents into %d branch units (%d excluded non-competition/empty, %d flagged needs_review).",
        len(documents) - len(excluded_documents),
        len(branch_units),
        len(excluded_documents),
        summary["branch_units_needs_review_count"],
    )
    return payload
