"""Stage 2: Audit, Validation, and Multi-Branch Taxonomy Classification for TXT Inventory.

This module audits the initial Stage 1 inventory (`document_inventory.csv` / `.json`)
against the raw TXT corpus (`data/raw/txt/`), identifies misclassifications in
`document_type` and `competition_branch`, assigns macro document categories and
standardized multi-branch taxonomy codes, extracts verbatim evidence from each
document, and flags documents requiring repair or PDF/OCR re-conversion.

Original Stage 1 inventory files are strictly preserved and never overwritten.
"""

from __future__ import annotations

import csv
import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Mapping from validated_document_type to one of the 6 macro categories (+ unknown)
DOCUMENT_TYPE_TO_MACRO_CATEGORY: Dict[str, str] = {
    "guidebook": "dokumen_panduan_kompetisi",
    "panduan": "dokumen_panduan_kompetisi",
    "panduan_pelaksanaan": "dokumen_panduan_kompetisi",
    "pedoman": "dokumen_panduan_kompetisi",
    "booklet": "dokumen_panduan_kompetisi",
    "handbook": "dokumen_panduan_kompetisi",
    "petunjuk_teknis": "dokumen_ketentuan_dan_petunjuk_teknis",
    "guidebook_petunjuk_teknis": "dokumen_ketentuan_dan_petunjuk_teknis",
    "panduan_teknis": "dokumen_ketentuan_dan_petunjuk_teknis",
    "rulebook": "dokumen_ketentuan_dan_petunjuk_teknis",
    "ketentuan_lomba": "dokumen_ketentuan_dan_petunjuk_teknis",
    "syarat_ketentuan": "dokumen_ketentuan_dan_petunjuk_teknis",
    "modul_pembelajaran": "modul_pembelajaran",
    "booklet_profil_finalis": "katalog_karya_atau_finalis",
    "paparan_sosialisasi": "dokumen_sosialisasi",
    "guidebook_bootcamp": "dokumen_lainnya",
    "booklet_rekrutmen": "dokumen_lainnya",
    "unknown": "unknown",
}


# Mapping from branch_code to domain_code
BRANCH_TO_DOMAIN: Dict[str, str] = {
    "BR_AI": "DOM_IT_DIGITAL",
    "BR_ML": "DOM_IT_DIGITAL",
    "BR_DATA_SCIENCE": "DOM_IT_DIGITAL",
    "BR_DATA_ANALYTICS": "DOM_IT_DIGITAL",
    "BR_CYBERSECURITY_CTF": "DOM_IT_DIGITAL",
    "BR_NETWORK_ADMIN": "DOM_IT_DIGITAL",
    "BR_SOFTWARE_DEV": "DOM_IT_DIGITAL",
    "BR_APP_DEV": "DOM_IT_DIGITAL",
    "BR_WEB_DEV": "DOM_IT_DIGITAL",
    "BR_HACKATHON": "DOM_IT_DIGITAL",
    "BR_UIUX_DESIGN": "DOM_IT_DIGITAL",
    "BR_IOT_ROBOTICS": "DOM_IT_DIGITAL",
    "BR_COMP_PROGRAMMING_LOGIC": "DOM_IT_DIGITAL",
    "BR_3D_ANIMATION": "DOM_IT_DIGITAL",
    "BR_BUSINESS_PLAN": "DOM_BUSINESS_ECON",
    "BR_BUSINESS_CASE": "DOM_BUSINESS_ECON",
    "BR_BMC": "DOM_BUSINESS_ECON",
    "BR_ENTREPRENEURSHIP_INNOVATION": "DOM_BUSINESS_ECON",
    "BR_POLICY_CASE": "DOM_BUSINESS_ECON",
    "BR_ACTUARIAL_CASE": "DOM_BUSINESS_ECON",
    "BR_SCIENCE_OLYMPIAD": "DOM_SCIENCE_ENG_STEM",
    "BR_STEM_PROJECT": "DOM_SCIENCE_ENG_STEM",
    "BR_ENG_CASE": "DOM_SCIENCE_ENG_STEM",
    "BR_ENG_MANAGEMENT_INNOVATION": "DOM_SCIENCE_ENG_STEM",
    "BR_ENV_ECO_PROJECT": "DOM_SCIENCE_ENG_STEM",
    "BR_SMART_QUIZ": "DOM_SCIENCE_ENG_STEM",
    "BR_SCIENTIFIC_PAPER": "DOM_WRITING_RESEARCH",
    "BR_ESSAY": "DOM_WRITING_RESEARCH",
    "BR_LITERARY_WRITING": "DOM_WRITING_RESEARCH",
    "BR_JOURNALISM": "DOM_WRITING_RESEARCH",
    "BR_INFOGRAPHIC": "DOM_CREATIVE_MEDIA_COMMUNICATION",
    "BR_POSTER_DESIGN": "DOM_CREATIVE_MEDIA_COMMUNICATION",
    "BR_VIDEO_FILM_PHOTO": "DOM_CREATIVE_MEDIA_COMMUNICATION",
    "BR_DEBATE_SPEECH": "DOM_CREATIVE_MEDIA_COMMUNICATION",
    "BR_RELIGIOUS_ARTS": "DOM_CREATIVE_MEDIA_COMMUNICATION",
    "BR_VOCATIONAL_LKS": "DOM_VOCATIONAL_NATIONAL",
}


@dataclass
class ValidatedDocumentRecord:
    """Validated inventory record preserving all Stage 1 fields and adding Stage 2 audit fields."""

    # Stage 1 Original Fields (Preserved)
    document_id: str
    file_name: str
    document_name: str
    character_count: int
    word_count: int
    readability_status: str
    document_type: str
    competition_branch: str
    classification_status: str
    notes: str

    # Explicit Original Snapshots
    original_document_type: str
    original_competition_branch: str
    original_classification_status: str

    # Stage 2 Validated & Taxonomy Fields
    macro_document_category: str
    validated_document_type: str
    multi_branch_type: str
    is_multi_branch: bool
    domain_codes: List[str] = field(default_factory=list)
    branch_codes: List[str] = field(default_factory=list)
    secondary_event_branch_codes: List[str] = field(default_factory=list)
    validated_competition_branch: str = ""
    validated_classification_status: str = ""
    document_type_changed: bool = False
    competition_branch_changed: bool = False
    classification_changed: bool = False
    audit_reason: str = ""
    content_evidence: str = ""
    reconversion_status: str = "clean"
    reconversion_reason: str = ""

    def to_csv_dict(self) -> Dict[str, Any]:
        """Serialize record for CSV output (lists joined by '|')."""
        data = asdict(self)
        data["domain_codes"] = "|".join(self.domain_codes)
        data["branch_codes"] = "|".join(self.branch_codes)
        data["secondary_event_branch_codes"] = "|".join(self.secondary_event_branch_codes)
        return data


# Per-document audit specification keyed by file_name.
# Every entry is grounded in the actual text content of `data/raw/txt/<file_name>`.
DOCUMENT_AUDIT_SPEC: Dict[str, Dict[str, Any]] = {
    "AI Builder Challenge 2026 – Participant Guidebook.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_AI"],
        "validated_competition_branch": "Artificial Intelligence (AI Prototype Development)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai buku panduan (Guidebook) kompetisi pengembangan prototipe berbasis AI.",
        "evidence_pattern": r"AI BUILDER CHALLENGE 2026.*PARTICIPANT GUIDEBOOK",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "App Dev.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_APP_DEV"],
        "validated_competition_branch": "Application Development",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook kompetisi Application Development pada ajang IT Today 2025.",
        "evidence_pattern": r"Rulebook Application Development.*IT Today 2025",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "BPC GUIDEBOOK.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Business Plan Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Business Plan Competition (BPC).",
        "evidence_pattern": r"BUSINESS PLAN COMPETITION.*GUIDEBOOK",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "BUSINESS PLAN COMPETITION .txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Business Plan Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Business Plan Competition.",
        "evidence_pattern": r"BUSINESS PLAN COMPETITION",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Booklet Duta Muda Bineka 2025 - Berbineka Indonesia.txt": {
        "validated_document_type": "booklet_rekrutmen",
        "multi_branch_type": "non_competition_or_unclassified",
        "is_multi_branch": False,
        "branch_codes": [],
        "validated_competition_branch": "non_competition (Seleksi Duta Muda Bineka)",
        "validated_classification_status": "validated_non_competition",
        "audit_reason": (
            "Audit dokumen berstatus needs_review: Isi dokumen adalah Booklet Pendaftaran "
            "Open Recruitment Duta Muda Bineka 2025 (seleksi peran duta pemuda, bukan cabang perlombaan karya/kompetisi). "
            "Dimasukkan ke kategori makro 'dokumen_lainnya'."
        ),
        "evidence_pattern": r"Booklet Pendaftaran Duta Muda Bineka 2025",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Booklet Firma Ceria 2025.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_RELIGIOUS_ARTS", "BR_LITERARY_WRITING"],
        "validated_competition_branch": "Multi-Cabang: Lomba Tilawah Al-Qur'an & Lomba Puisi Islami",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Terkonfirmasi sebagai Guidebook ('GUIDE BOOK SEMINAR & LOMBA FIRMA CERIA 2025' pada teks isi, "
            "kategori makro: dokumen_panduan_kompetisi) yang mencakup 2 cabang lomba: Lomba Tilawah Al-Qur'an dan Lomba Puisi Islami."
        ),
        "evidence_pattern": r"GUIDE BOOK SEMINAR & LOMBA FIRMA CERIA 2025.*LOMBA TILAWAH.*LOMBA PUISI ISLAMI",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Booklet Hackathon 2025.txt": {
        "validated_document_type": "booklet_profil_finalis",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_HACKATHON", "BR_AI", "BR_CYBERSECURITY_CTF"],
        "validated_competition_branch": "Hackathon (AI & Cybersecurity Financial Innovation)",
        "validated_classification_status": "needs_review_non_rulebook_catalog",
        "audit_reason": (
            "Audit dokumen berstatus needs_review & readable_with_ocr_noise: Dokumen ini bukan buku panduan pendaftaran "
            "melainkan Katalog/Booklet Profil Top 10 Tim Finalis beserta ringkasan inovasi BI-OJK Hackathon 2025 "
            "(kategori makro: 'katalog_karya_atau_finalis'). Terdapat 58 karakter kontrol (\\x1e/\\x1f) akibat "
            "kerusakan ekstraksi ligatur 'fi'/'fl'."
        ),
        "evidence_pattern": r"10 Finalis Terpilih.*Profil 10 Tim Finalis Hackathon 2025",
        "reconversion_status": "needs_font_encoding_fix",
        "reconversion_reason": "Terdapat 58 karakter kontrol ASCII (\\x1e dan \\x1f) yang menggantikan ligatur 'fi' dan 'fl' (contoh: 'e\\x1fsiensi', 'signi\\x1fkan'). Perlu pembersihan ligatur atau ekstraksi ulang PDF.",
    },
    "Booklet Literat Fest 2024.txt": {
        "validated_document_type": "booklet",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_LITERARY_WRITING"],
        "validated_competition_branch": "Multi-Cabang: Cipta Puisi & Cipta Cerpen",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'booklet' (kategori makro: dokumen_panduan_kompetisi). "
            "Pada tahap 1 terklasifikasi 'ketentuan_lomba' karena sampul rusak akibat OCR ('Explore the Powe / L r of Words'), "
            "namun dokumen memiliki struktur Booklet Panduan Lomba lengkap (Daftar Isi, Latar Belakang, Tujuan, Syarat dan Ketentuan, "
            "Linimasa, Hadiah) untuk 2 cabang sastra: Puisi dan Cerpen."
        ),
        "evidence_pattern": r"SAYEMBARA CIPTA PUISI DAN CERPEN TINGKAT NASIONAL.*Daftar Isi\s+Latar Belakang",
        "reconversion_status": "needs_ocr_cleanup",
        "reconversion_reason": "Teks sampul terpecah per karakter akibat OCR ('Explore the Powe / L r of Words / E S T').",
    },
    "Booklet SMA_K Sederajat_Pharmacopeia 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_SCIENCE_OLYMPIAD", "BR_ESSAY", "BR_POSTER_DESIGN", "BR_VIDEO_FILM_PHOTO"],
        "validated_competition_branch": "Multi-Cabang: Science Olympiad, Essay, Digital Poster, Video Campaign (Kefarmasian)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Audit dokumen readable_with_ocr_noise: Terkonfirmasi sebagai Competition Guideline / Guidebook Pharmacopeia 2026 "
            "(kategori makro: dokumen_panduan_kompetisi) yang mencakup 4 cabang perlombaan tingkat SMA/K Sederajat: "
            "Science Olympiad, Essay, Digital Poster, dan Video Campaign."
        ),
        "evidence_pattern": r"science Olympiad\s+Digital Poster Competition\s+Video Campaign Competition.*Essay Competition",
        "reconversion_status": "needs_ocr_cleanup",
        "reconversion_reason": "Artefak OCR pada sampul dan isi ('we ompetition Buideline a)', 'SMAIK Sederajat', 'terobuka', 'wajidb').",
    },
    "Competition Booklet - SIBCC 2627.txt": {
        "validated_document_type": "booklet",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BUSINESS_CASE"],
        "validated_competition_branch": "Business Case Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Competition Booklet untuk Business Case Competition (SIBCC).",
        "evidence_pattern": r"COMPETITION BOOKLET.*BUSINESS CASE COMPETITION",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "ENERGY4ME GUIDEBOOK.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_STEM_PROJECT"],
        "validated_competition_branch": "Science Experiment Competition (Renewable & Non-Renewable Energy)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook kompetisi eksperimen sains dan energi (Energy4Me).",
        "evidence_pattern": r"ENERGY4ME.*SCIENCE EXPERIMENT COMPETITION",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "ESAI GAGASAN KREATIF UI SCIENCE OLYMPIAD 2026.txt": {
        "validated_document_type": "panduan_pelaksanaan",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ESSAY"],
        "validated_competition_branch": "Essay Competition (Esai Gagasan Kreatif)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'panduan_pelaksanaan' (kategori makro: dokumen_panduan_kompetisi). "
            "Teks bagian Penutup secara eksplisit menyebut dokumen ini sebagai 'panduan pelaksanaan Lomba Esai Gagasan Kreatif "
            "UI Science Olympiad 2026' dan memuat struktur panduan lengkap (Pendahuluan, Tema, Timeline, Ketentuan, Mekanisme, Kriteria Penilaian)."
        ),
        "evidence_pattern": r"Demikian panduan pelaksanaan Lomba Esai Gagasan Kreatif UI Science Olympiad 2026",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "ESAI GAGASAN KRITIS UI SCIENCE OLYMPIAD 2026.txt": {
        "validated_document_type": "panduan_pelaksanaan",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ESSAY"],
        "validated_competition_branch": "Essay Competition (Esai Gagasan Kritis)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'panduan_pelaksanaan' (kategori makro: dokumen_panduan_kompetisi). "
            "Teks bagian Penutup secara eksplisit menyebut dokumen ini sebagai 'panduan pelaksanaan Lomba Esai Gagasan Kritis "
            "UI Science Olympiad 2026' dengan struktur bab panduan lengkap."
        ),
        "evidence_pattern": r"Demikian panduan pelaksanaan Lomba Esai Gagasan Kritis UI Science Olympiad 2026",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "FIX Guidebook Advanced 2025.txt": {
        "validated_document_type": "guidebook_bootcamp",
        "multi_branch_type": "non_competition_or_unclassified",
        "is_multi_branch": False,
        "branch_codes": [],
        "validated_competition_branch": "non_competition (Bootcamp Pelatihan Schematics BST Advanced)",
        "validated_classification_status": "validated_non_competition",
        "audit_reason": (
            "Audit dokumen berstatus needs_review: Isi dokumen adalah Guidebook Peserta Bootcamp/Pelatihan "
            "Schematics BST 2025 (kurikulum pelatihan 4 hari, quiz harian, dan final project peserta bootcamp), "
            "bukan kompetisi terbuka. Dimasukkan ke kategori makro 'dokumen_lainnya'."
        ),
        "evidence_pattern": r"Schematics Bootstrapping.*program pelatihan yang dirancang untuk generasi muda",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "FMIPA STEM Challenge.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": [
            "BR_SCIENTIFIC_PAPER",
            "BR_SCIENCE_OLYMPIAD",
            "BR_IOT_ROBOTICS",
            "BR_DATA_SCIENCE",
            "BR_ACTUARIAL_CASE",
            "BR_SMART_QUIZ",
        ],
        "validated_competition_branch": "Multi-Cabang: Sains, Matematika, Robotika/IoT, Informatika, Kimia, Aktuaria (SCIENTA, LMNas, INSPIRE, JOINTS, TOP COP, OKN, ASiQ)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Audit dokumen readable_with_ocr_noise: Terkonfirmasi sebagai Master Guidebook FMIPA UGM STEM Challenge 2026 "
            "yang menaungi 7 sub-event multi-cabang (SCIENTA, LMNas 37, INSPIRE, JOINTS, TOP COP, OKN, dan ASiQ)."
        ),
        "evidence_pattern": r"1\.\s*SCIENTA.*2\.\s*LMNas 37.*3\.\s*INSPIRE.*4\.\s*JOINTS.*5\.\s*TOP COP.*6\.\s*OKN.*7\.\s*ASiQ",
        "reconversion_status": "needs_ocr_cleanup",
        "reconversion_reason": "Artefak OCR pada halaman pembuka ('f= mn ©)') dan kesalahan pengenalan karakter 'IoT' menjadi 'lol'.",
    },
    "GUIDE BOOK HIMTEC-1.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "composite_branch_competition",
        "is_multi_branch": True,
        "branch_codes": ["BR_HACKATHON", "BR_APP_DEV", "BR_AI"],
        "validated_competition_branch": "Hackathon / Application Development (Build App With AI)",
        "validated_classification_status": "validated_composite_branch",
        "audit_reason": (
            "Terkonfirmasi sebagai Guidebook kompetisi 'Build App With AI' (HIMTEC) yang menggabungkan "
            "kompetensi Hackathon, pengembangan aplikasi (App Dev), dan pemanfaatan AI."
        ),
        "evidence_pattern": r"BUILD APP WITH AI.*GUIDE BOOK",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDE BOOK NEXTGEN BMC.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BMC"],
        "validated_competition_branch": "Business Model Canvas (BMC) Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook kompetisi Business Model Canvas (NextGen BMC).",
        "evidence_pattern": r"GUIDEBOOK.*BUSINESS MODEL CANVAS",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK ALGOQUEST 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_COMP_PROGRAMMING_LOGIC"],
        "validated_competition_branch": "Computational Thinking, Logic & Mathematics",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Pada tahap 1 terklasifikasi 'ketentuan_lomba' karena tulisan sampul berbentuk grafik tidak terekstrak, "
            "tetapi isi dokumen memuat struktur Guidebook lengkap (Latar Belakang, Tujuan, Tema, Ketentuan, Mekanisme Babak, "
            "Silabus Computational Thinking/Logika/Matematika, dan Hadiah)."
        ),
        "evidence_pattern": r"ALGOQUEST 2026.*Latar Belakang.*Mekanisme Kompetisi",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK BPC.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Business Plan Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Business Plan Competition.",
        "evidence_pattern": r"GUIDEBOOK.*BUSINESS PLAN COMPETITION",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK DAC.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_DATA_ANALYTICS"],
        "validated_competition_branch": "Data Analytics / Visualisasi Data (Dashboard Analytics)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Data Analytics Competition (DAC).",
        "evidence_pattern": r"Data Analytics Competition.*Dashboard",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK ESCO 2026 .txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ESSAY"],
        "validated_competition_branch": "Essay Competition (Social Essay)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Essay Social Competition (ESCO 2026).",
        "evidence_pattern": r"GUIDEBOOK.*ESCO 2026",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK ESSAY COMPETITION (7).txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ESSAY"],
        "validated_competition_branch": "Essay Competition (Public Policy & Socio-Ecological)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook National Essay Competition.",
        "evidence_pattern": r"GUIDEBOOK.*ESSAY COMPETITION",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK ESSAY JBC 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ESSAY"],
        "validated_competition_branch": "Essay Competition (Business & Technology Essay)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Essay Competition JBC 2026.",
        "evidence_pattern": r"GUIDEBOOK.*ESSAY.*JBC 2026",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK IMPACTEERS UNIVERSITAS NEGERI SURABAYA.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_ESSAY", "BR_BMC", "BR_POSTER_DESIGN"],
        "validated_competition_branch": "Multi-Cabang: Essay Competition, Business Model Canvas (BMC), Poster Competition",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook multi-cabang Impacteers UNESA yang memuat 3 lomba: Essay, BMC, dan Poster.",
        "evidence_pattern": r"Essay Competition.*Business Model Canvas.*Poster Competition",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK INFOGRAFIS COMPETITION.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_INFOGRAPHIC"],
        "validated_competition_branch": "Infographic Design Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Dokumen memiliki Daftar Isi dan bab Guidebook lengkap (Latar Belakang, Tema, Timeline, Ketentuan, Kriteria Penilaian Infografis)."
        ),
        "evidence_pattern": r"DAFTAR ISI.*LATAR BELAKANG.*INFOGRAFIS",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK ISOTHERM.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_SCIENTIFIC_PAPER"],
        "validated_competition_branch": "Karya Tulis Ilmiah / Innovative Research Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook ISOTHERM (Innovative Research / Karya Tulis Ilmiah).",
        "evidence_pattern": r"GUIDEBOOK.*ISOTHERM",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK IT FEST 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": [
            "BR_SOFTWARE_DEV",
            "BR_NETWORK_ADMIN",
            "BR_CYBERSECURITY_CTF",
            "BR_VIDEO_FILM_PHOTO",
        ],
        "validated_competition_branch": "Multi-Cabang: Software Development, IT Network System Administration (ITNSA), Capture The Flag (CTF), Short Movie",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "KOREKSI KRITIS (document_type & competition_branch): Pada tahap 1 terklasifikasi tunggal sebagai "
            "'Software Development' dan 'petunjuk_teknis' karena posisi subbab 'G. Petunjuk Teknis Pengumpulan' "
            "dan cabang pertama pada Daftar Isi. Audit isi membuktikan dokumen ini adalah Master Guidebook IT FEST 2026 "
            "yang memuat 4 cabang perlombaan lengkap: Software Development (hlm. 1), IT Network System Administration / ITNSA (hlm. 7), "
            "Capture The Flag / CTF (hlm. 19), dan Short Movie (hlm. 27)."
        ),
        "evidence_pattern": r"DAFTAR ISI\s+SOFTWARE DEVELOPMENT",
        "verbatim_clauses": [
            "DAFTAR ISI",
            "SOFTWARE DEVELOPMENT",
            "IT NETWORK SYSTEM ADMINISTRATION (ITNSA)",
            "CAPTURE THE FLAG",
            "SHORT MOVIE",
        ],
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK LOMBA POSTER.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_POSTER_DESIGN"],
        "validated_competition_branch": "Poster Design Competition (Kesehatan & Kefarmasian)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Lomba Poster.",
        "evidence_pattern": r"GUIDEBOOK.*LOMBA POSTER",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK MLC.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ML"],
        "validated_competition_branch": "Machine Learning",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Machine Learning Competition (MLC).",
        "evidence_pattern": r"Machine Learning Competition",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK POLICY CASE COMPETITION .txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_POLICY_CASE"],
        "validated_competition_branch": "Policy Case Competition (Public Policy)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Policy Case Competition.",
        "evidence_pattern": r"POLICY CASE COMPETITION",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "GUIDEBOOK WEB DEVELOPMENT COMPETITION FINALL.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_WEB_DEV"],
        "validated_competition_branch": "Web Development",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Web Development Competition.",
        "evidence_pattern": r"WEB DEVELOPMENT COMPETITION",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guide book Eco-Project Competition.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ENV_ECO_PROJECT"],
        "validated_competition_branch": "Environmental Project Innovation (Eco-Project)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Eco-Project Competition (Greenova).",
        "evidence_pattern": r"Eco-Project Competition",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook BCC MANIFEST 2026 (fixx).txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "primary_branch_with_multi_event_intro",
        "is_multi_branch": False,
        "branch_codes": ["BR_BUSINESS_CASE"],
        "secondary_event_branch_codes": ["BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Business Case Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Audit dokumen readable_with_ocr_noise: Bagian pengenalan MANIFEST 2026 menyebutkan 3 rangkaian lomba "
            "(BPC, BCC, dan EBPC), namun isi teknis, mekanisme penyisihan/final, dan format pengiriman berkas pada dokumen ini "
            "secara spesifik mengatur cabang Business Case Competition (BCC)."
        ),
        "evidence_pattern": r"Business Case Competition \(BCC\).*BCC Proposal_Nama Tim_Nama Ketua Tim",
        "reconversion_status": "needs_ocr_cleanup",
        "reconversion_reason": "Terdapat derau OCR pada header dan paragraf awal ('NSINCSwS)i CaUiS C,', 'Manaj emen Bisnii s Festiivala l').",
    },
    "Guidebook BPC TSF 2026.txt": {
        "validated_document_type": "unknown",
        "multi_branch_type": "non_competition_or_unclassified",
        "is_multi_branch": False,
        "branch_codes": [],
        "validated_competition_branch": "unknown",
        "validated_classification_status": "unclassified_empty",
        "audit_reason": (
            "Audit dokumen berstatus empty & unclassified: File hanya berukuran 3 byte (UTF-8 BOM '\\ufeff', 0 karakter, 0 kata). "
            "Sesuai prinsip integritas data, cabang lomba tidak boleh ditebak hanya dari nama file ('BPC TSF 2026'). "
            "Wajib dilakukan ekstraksi/OCR ulang dari PDF sumber."
        ),
        "evidence_pattern": None,
        "reconversion_status": "needs_reextraction_empty",
        "reconversion_reason": "File TXT kosong (0 kata, hanya 3 byte UTF-8 BOM). Kemungkinan PDF sumber berbasis gambar (scanned PDF) yang belum melalui OCR.",
    },
    "Guidebook Business Case Competition.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BUSINESS_CASE"],
        "validated_competition_branch": "Business Case Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Business Case Competition.",
        "evidence_pattern": r"Business Case Competition",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook Data Science.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_DATA_SCIENCE"],
        "validated_competition_branch": "Data Science",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Data Science Competition.",
        "evidence_pattern": r"Data Science",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook EIC College.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "composite_branch_competition",
        "is_multi_branch": True,
        "branch_codes": ["BR_ESSAY", "BR_INFOGRAPHIC"],
        "validated_competition_branch": "Essay & Infographic Competition (Tingkat Mahasiswa)",
        "validated_classification_status": "validated_composite_branch",
        "audit_reason": (
            "Terkonfirmasi sebagai Guidebook Essay & Infographic Competition (EIC) MetalFest ITB 2027 tingkat Mahasiswa "
            "yang mengintegrasikan dua luaran lomba sekaligus: karya esai ilmiah dan poster infografis (dipetakan ke BR_ESSAY dan BR_INFOGRAPHIC)."
        ),
        "evidence_pattern": r"MetalFest ITB 2027.*Essay & Infographic Competition",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook EIC High School.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "composite_branch_competition",
        "is_multi_branch": True,
        "branch_codes": ["BR_ESSAY", "BR_INFOGRAPHIC"],
        "validated_competition_branch": "Essay & Infographic Competition (Tingkat SMA/Sederajat)",
        "validated_classification_status": "validated_composite_branch",
        "audit_reason": (
            "Terkonfirmasi sebagai Guidebook Essay & Infographic Competition (EIC) MetalFest ITB 2027 tingkat SMA/Sederajat "
            "yang mengintegrasikan dua luaran lomba sekaligus: esai dan infografis (dipetakan ke BR_ESSAY dan BR_INFOGRAPHIC)."
        ),
        "evidence_pattern": r"MetalFest ITB 2027.*Essay & Infographic Competition",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook EMIC 2026 [SMA].txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ENG_MANAGEMENT_INNOVATION"],
        "validated_competition_branch": "Engineering Management Innovation (Extended Abstract & Prototype)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'panduan' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Teks secara eksplisit menampilkan tajuk 'EMIC SMA/MA GUIDEBOOK' untuk Engineering Management Innovation Competition."
        ),
        "evidence_pattern": r"EMIC SMA/MA GUIDEBOOK",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook Essay Competition Pre-Event OGG FITB ITB 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ESSAY"],
        "validated_competition_branch": "Essay Competition (Geografi & Geosains)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Essay Competition Pre-Event Olimpiade Geografi & Geosains (OGG) FITB ITB 2026.",
        "evidence_pattern": r"ESSAY COMPETITION.*OLIMPIADE GEOGRAFI DAN GEOSAINS",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook Essay EUREKA! ITB 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ESSAY"],
        "validated_competition_branch": "Essay Competition (Physics & Sustainable Technology)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Dokumen memiliki struktur Daftar Isi dan bab Guidebook lengkap untuk Essay Competition EUREKA! ITB 2026."
        ),
        "evidence_pattern": r"DAFTAR ISI.*LATAR BELAKANG.*EUREKA! ITB 2026",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook IBCC SxC International Summit 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BUSINESS_CASE"],
        "validated_competition_branch": "Business Case Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook International Business Case Competition (IBCC) SxC International Summit 2026.",
        "evidence_pattern": r"International Business Case Competition",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook Immersive Fiesta 2025.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_3D_ANIMATION"],
        "validated_competition_branch": "3D Animation (3D Walking Loop Animation)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'panduan' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Teks pengantar secara eksplisit menyatakan: 'Guidebook ini disusun untuk menjadi panduan resmi bagi para peserta "
            "dalam mengikuti rangkaian kompetisi Immersive Fiesta 2025'."
        ),
        "evidence_pattern": r"Guidebook ini disusun untuk menjadi panduan resmi bagi para peserta dalam mengikuti rangkaian kompetisi Immersive Fiesta 2025",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook Logicodix 2024.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_COMP_PROGRAMMING_LOGIC"],
        "validated_competition_branch": "Competitive Programming & Logic",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'panduan' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Teks mencantumkan tajuk 'LOGICODIX 2024 ... GUIDEBOOK' untuk kompetisi pemrograman dan logika."
        ),
        "evidence_pattern": r"LOGICODIX 2024.*GUIDEBOOK",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook National BMC Competition 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BMC"],
        "validated_competition_branch": "Business Model Canvas (BMC) Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Teks di dalam dokumen secara eksplisit merujuk dokumen ini sebagai 'Guidebook National Business Model Canvas Competition'."
        ),
        "evidence_pattern": r"National Business Model Canvas \(BMC\) Competition",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook PJJ CHALLENGE Chapter II.txt": {
        "validated_document_type": "guidebook_petunjuk_teknis",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": [
            "BR_SMART_QUIZ",
            "BR_SCIENTIFIC_PAPER",
            "BR_ESSAY",
            "BR_VIDEO_FILM_PHOTO",
        ],
        "validated_competition_branch": "Multi-Cabang: Brain Challenge, Short Paper, Essay, Catch the Moment",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Terkonfirmasi sebagai dokumen gabungan Guidebook & Petunjuk Teknis (Juknis) PJJ Challenge Chapter II "
            "yang mengatur 4 cabang perlombaan: Brain Challenge, Short Paper Competition, Essay Competition, dan Catch the Moment."
        ),
        "evidence_pattern": r"Brain Challenge.*Short Paper.*Essay Competition.*Catch the Moment",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook Tahap Terpusat Pre-Event OGG FITB ITB 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": [
            "BR_POSTER_DESIGN",
            "BR_DEBATE_SPEECH",
            "BR_VIDEO_FILM_PHOTO",
            "BR_SMART_QUIZ",
            "BR_ESSAY",
            "BR_STEM_PROJECT",
        ],
        "validated_competition_branch": "Multi-Cabang: Poster, Geo Debate, Geo Video, Smart Competition, Essay, Science Project, English Speech",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Dokumen merupakan Guidebook Tahap Terpusat Pre-Event OGG FITB ITB 2026 yang memuat 7 mata lomba."
        ),
        "evidence_pattern": r"Poster Competition.*Geo Debate.*Geo Video.*Smart Competition.*Essay Competition.*Science Project.*English Speech",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook WIA.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_WEB_DEV"],
        "validated_competition_branch": "Web Development",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Web In Action (WIA) - Web Development.",
        "evidence_pattern": r"Web In Action",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook Web Development Genesis 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_WEB_DEV"],
        "validated_competition_branch": "Web Development",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Web Development Genesis 2026.",
        "evidence_pattern": r"WEB DEVELOPMENT.*GENESIS",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook_CleanCode_Updated.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_WEB_DEV"],
        "validated_competition_branch": "Web Development / Clean Code",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Dokumen memiliki struktur Daftar Isi dan bab Guidebook lengkap untuk cabang Clean Code (Web Development)."
        ),
        "evidence_pattern": r"Clean Code.*Deskripsi Lomba.*Kriteria Penilaian",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook_Hackathon.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "composite_branch_competition",
        "is_multi_branch": True,
        "branch_codes": ["BR_HACKATHON", "BR_WEB_DEV"],
        "validated_competition_branch": "Hackathon / Web Development",
        "validated_classification_status": "validated_composite_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook Hackathon yang berfokus pada pengembangan solusi berbasis Web.",
        "evidence_pattern": r"HACKATHON.*GUIDEBOOK",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook_UIUX_Design.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_UIUX_DESIGN"],
        "validated_competition_branch": "UI/UX Design",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Dokumen memuat Daftar Isi dan struktur Guidebook lengkap untuk cabang UI/UX Design."
        ),
        "evidence_pattern": r"UI/UX Design.*Deskripsi Lomba.*Kriteria Penilaian",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Guidebook_Wreck_IT_7.0.txt": {
        "validated_document_type": "guidebook_petunjuk_teknis",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_CYBERSECURITY_CTF"],
        "validated_competition_branch": "Cybersecurity / Capture The Flag (CTF)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook & Petunjuk Teknis kompetisi Capture The Flag (CTF) Wreck IT 7.0.",
        "evidence_pattern": r"WRECK-IT 7\.0.*Capture The Flag",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "HACKATHON GUIDEBOOK.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "primary_branch_with_multi_event_intro",
        "is_multi_branch": False,
        "branch_codes": ["BR_STEM_PROJECT", "BR_IOT_ROBOTICS"],
        "secondary_event_branch_codes": ["BR_BUSINESS_PLAN", "BR_HACKATHON"],
        "validated_competition_branch": "STEM Innovation & IoT Project Exhibition (PE STEM Techtonic UI 3.0 — Filename Mismatch: File bernama HACKATHON GUIDEBOOK.txt)",
        "validated_classification_status": "needs_review_filename_mismatch",
        "audit_reason": (
            "TEMUAN AUDIT KRITIS (Tertukarnya Nama File vs Isi Dokumen): Nama file adalah 'HACKATHON GUIDEBOOK.txt', "
            "dan halaman 1–5 memuat pengenalan umum 3 cabang Techtonic UI 3.0 (STEM, BPC, Hackathon). Namun bagian panduan utama "
            "(halaman 15–27) secara eksplisit adalah panduan cabang PE STEM Competition ('Welcome to the PE STEM Competition of Techtonic UI 3.0!', "
            "Tema: 'Connecting Lives through IoT', Manajer: Abdur Rasyiid Ridha Muflihin). Isi file ini tertukar dengan 'STEM GUIDEBOOK.txt'."
        ),
        "evidence_pattern": r"Welcome to the PE STEM Competition of Techtonic UI 3\.0!.*Connecting Lives through IoT",
        "reconversion_status": "needs_filename_swap_fix",
        "reconversion_reason": "Nama file 'HACKATHON GUIDEBOOK.txt' tertukar dengan 'STEM GUIDEBOOK.txt' pada saat penyimpanan/konversi PDF sumber.",
    },
    "HSC BRAND UI 2026 HANDBOOK.txt": {
        "validated_document_type": "handbook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Business Plan Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Audit dokumen readable_with_ocr_noise: Terkonfirmasi sebagai Handbook kompetisi Business Plan HSC BRAND UI 2026.",
        "evidence_pattern": r"HSC BRAND UI 2026.*Business Plan Competition",
        "reconversion_status": "needs_ocr_cleanup",
        "reconversion_reason": "Artefak OCR pada halaman sampul ('Powere d by // GC. -@-O¢').",
    },
    "INFOGRAFIS UI SCIENCE OLYMPIAD 2026.txt": {
        "validated_document_type": "panduan_pelaksanaan",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_INFOGRAPHIC"],
        "validated_competition_branch": "Infographic Design Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'panduan_pelaksanaan' (kategori makro: dokumen_panduan_kompetisi). "
            "Teks bagian Penutup secara eksplisit menyebut dokumen ini sebagai 'panduan pelaksanaan Lomba Infografis UI Science Olympiad 2026'."
        ),
        "evidence_pattern": r"Demikian panduan pelaksanaan Lomba Infografis UI Science Olympiad 2026",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Internet Of Things.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_IOT_ROBOTICS"],
        "validated_competition_branch": "Internet of Things (IoT)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Guidebook kompetisi Internet of Things (IoT).",
        "evidence_pattern": r"Internet of Things",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Juknis EPIC.txt": {
        "validated_document_type": "ketentuan_lomba",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Business Plan Competition",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Audit dokumen readable_with_ocr_noise: Terkonfirmasi sebagai dokumen ketentuan teknis lomba "
            "('KETENTUAN KARYA / Ketentuan Business Model Canvas / Ketentuan Proposal', kategori makro: "
            "dokumen_ketentuan_dan_petunjuk_teknis) untuk Business Plan Competition EPIC (Olimpiade Update Festival 10)."
        ),
        "evidence_pattern": r"Merupakan Kompetisi Business Plan.*KETENTUAN KARYA",
        "reconversion_status": "needs_font_encoding_fix",
        "reconversion_reason": "Terdapat 69 karakter kontrol ASCII (\\x02 s.d. \\x1f) pada bagian 'TEMA' sehingga kalimat tema utama tidak terbaca akibat kegagalan font ToUnicode map.",
    },
    "Juknis KOSA KATA Cerpen.txt": {
        "validated_document_type": "ketentuan_lomba",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_LITERARY_WRITING"],
        "validated_competition_branch": "Penulisan Cerita Pendek (Cerpen)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Audit dokumen readable_with_ocr_noise: Terkonfirmasi sebagai dokumen ketentuan teknis lomba "
            "('KETENTUAN KARYA / MEKANISME KOMPETISI', kategori makro: dokumen_ketentuan_dan_petunjuk_teknis) "
            "untuk Lomba Cipta Cerpen KOSA KATA (Olimpiade Update Festival)."
        ),
        "evidence_pattern": r"KETENTUAN KARYA\s+1\s+Karya yang dikirimkan adalah karya cerita pendek \(cerpen\)",
        "reconversion_status": "needs_font_encoding_fix",
        "reconversion_reason": "Terdapat 71 karakter kontrol ASCII (\\x02 s.d. \\x1f) pada bagian 'TEMA' sehingga judul tema utama rusak akibat kegagalan font encoding PDF.",
    },
    "Modul BST Advance 2025.txt": {
        "validated_document_type": "modul_pembelajaran",
        "multi_branch_type": "non_competition_or_unclassified",
        "is_multi_branch": False,
        "branch_codes": [],
        "validated_competition_branch": "non_competition (Modul Pembelajaran Backend Golang Schematics BST)",
        "validated_classification_status": "validated_non_competition",
        "audit_reason": (
            "Audit dokumen berstatus needs_review: Dokumen ini adalah Modul Pembelajaran teknis pengembangan aplikasi "
            "Backend menggunakan Golang (25.690 kata) untuk peserta pelatihan Schematics BST 2025, bukan panduan perlombaan. "
            "Dimasukkan ke kategori makro 'modul_pembelajaran'."
        ),
        "evidence_pattern": r"MODUL.*SCHEMATICS BST.*Golang",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "NEW_GUIDEBOOK ENFORNATION 2026.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": [
            "BR_SCIENTIFIC_PAPER",
            "BR_VIDEO_FILM_PHOTO",
            "BR_SMART_QUIZ",
            "BR_ENG_CASE",
            "BR_INFOGRAPHIC",
        ],
        "validated_competition_branch": "Multi-Cabang/Rangkaian: Lomba Karya Tulis Ilmiah (LKTI), Videografi, CBT & Studi Kasus Infografis (Kehutanan & Lingkungan)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'guidebook' (kategori makro: dokumen_panduan_kompetisi). "
            "Dokumen merupakan Guidebook ENFORNATION 2026 dengan Daftar Isi dan rincian tahapan LKTI, Videografi, CBT, dan Studi Kasus Infografis."
        ),
        "evidence_pattern": r"ENFORNATION 2026.*Lomba Karya Tulis Ilmiah.*Videografi.*Studi Kasus",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Panduan FIKSI 2026.txt": {
        "validated_document_type": "panduan",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_ENTREPRENEURSHIP_INNOVATION", "BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Multi-Cabang: Inovasi & Kewirausahaan (FIKSI - 11 Bidang)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": "Terkonfirmasi sebagai Panduan Teknis Pelaksanaan FIKSI 2026 yang mencakup 11 bidang kewirausahaan siswa.",
        "evidence_pattern": r"FESTIVAL INOVASI DAN KEWIRAUSAHAAN SISWA INDONESIA \(FIKSI\)",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Panduan Lomba Esai untuk Pelajar SMP SMA.txt": {
        "validated_document_type": "ketentuan_lomba",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ESSAY"],
        "validated_competition_branch": "Essay Competition (Kesehatan & Gizi Remaja)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'panduan' menjadi 'ketentuan_lomba' (kategori makro: dokumen_ketentuan_dan_petunjuk_teknis). "
            "Baris pertama dokumen bertajuk 'Ketentuan Umum Lomba Esai Pelajar SMP dan SMA Sederajat' (1.126 kata) yang langsung memuat "
            "syarat peserta, ketentuan penulisan, dan sistematika naskah esai tanpa bab pendahuluan/latar belakang acara."
        ),
        "evidence_pattern": r"Ketentuan Umum Lomba Esai Pelajar SMP dan SMA Sederajat",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Panduan SOBAT Competition 2026.txt": {
        "validated_document_type": "panduan",
        "multi_branch_type": "composite_branch_competition",
        "is_multi_branch": True,
        "branch_codes": ["BR_STEM_PROJECT", "BR_SCIENTIFIC_PAPER"],
        "validated_competition_branch": "Inovasi Sains, Teknologi & Sosial (Prototype & Makalah - Multi Kategori)",
        "validated_classification_status": "validated_composite_branch",
        "audit_reason": (
            "Terkonfirmasi sebagai Panduan Peserta SOBAT Competition 2026 yang mewajibkan luaran ganda "
            "berupa Prototype dan Makalah Ilmiah pada berbagai kategori inovasi."
        ),
        "evidence_pattern": r"PANDUAN PESERTA.*SOBAT COMPETITION 2026.*OUTPUT: PROTOTYPE & MAKALAH",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Panduan Teknis Pra-Seleksi EKKA OSN Bidang Sains Tahun 2026.txt": {
        "validated_document_type": "panduan_teknis",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_AI", "BR_SCIENCE_OLYMPIAD"],
        "validated_competition_branch": "Artificial Intelligence / Olimpiade Kecerdasan Artifisial (EKKA OSN)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Panduan Teknis Pra-Seleksi EKKA OSN Bidang Sains (Kecerdasan Artifisial) Tahun 2026.",
        "evidence_pattern": r"Panduan Teknis Pra-Seleksi.*Eksplorasi Kemampuan Kecerdasan Artifisial \(EKKA\)",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2024.txt": {
        "validated_document_type": "pedoman",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_VOCATIONAL_LKS"],
        "validated_competition_branch": "Multi-Cabang: Kompetensi Vokasi/Keahlian Siswa (LKS)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Audit dokumen readable_with_ocr_noise: Terkonfirmasi sebagai Pedoman Lomba Kompetensi Siswa (LKS SMK) Tahun 2024 "
            "(halaman sampul memiliki placeholder template MS Word '[DOCUMENT TITLE]' yang belum diganti)."
        ),
        "evidence_pattern": r"PEDOMAN\s+LOMBA KOMPETENSI SISWA\s+SEKOLAH MENENGAH KEJURUAN \(LKS\s*–\s*SMK\s*\)\s+TAHUN 2024",
        "reconversion_status": "needs_ocr_cleanup",
        "reconversion_reason": "Halaman sampul berisi placeholder template MS Word ('[DOCUMENT TITLE]', '[COMPANY NAME]') yang belum dihapus saat ekspor PDF.",
    },
    "Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2025 .txt": {
        "validated_document_type": "panduan",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_VOCATIONAL_LKS"],
        "validated_competition_branch": "Multi-Cabang: Kompetensi Vokasi/Keahlian Siswa (LKS)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": "Terkonfirmasi sebagai Panduan Ajang Talenta Lomba Kompetensi Siswa (LKS) Tahun 2025.",
        "evidence_pattern": r"LOMBA KOMPETENSI SISWA.*2025",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Panduan_Ajang_Talenta_Lomba_Kompetensi_Siswa_Tahun_2026.txt": {
        "validated_document_type": "panduan",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_VOCATIONAL_LKS"],
        "validated_competition_branch": "Multi-Cabang: Kompetensi Vokasi/Keahlian Siswa (LKS)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'pedoman' menjadi 'panduan' (kategori makro: dokumen_panduan_kompetisi). "
            "Judul resmi pada sampul dalam adalah 'PANDUAN AJANG LOMBA KOMPETENSI SISWA (LKS) TINGKAT NASIONAL TAHUN 2026'."
        ),
        "evidence_pattern": r"PANDUAN AJANG LOMBA KOMPETENSI SISWA \(LKS\)\s+TINGKAT NASIONAL TAHUN 2026",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Panduan_FIKSI_SMA_MA_SMK 2025_.txt": {
        "validated_document_type": "panduan",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_ENTREPRENEURSHIP_INNOVATION", "BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Multi-Cabang: Inovasi & Kewirausahaan (FIKSI - 11 Bidang)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": "Terkonfirmasi sebagai Panduan FIKSI Jenjang SMA/MA/SMK Tahun 2025 (11 bidang wirausaha).",
        "evidence_pattern": r"FESTIVAL INOVASI DAN KEWIRAUSAHAAN SISWA INDONESIA.*2025",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Pedoman EIC - PGTC 2026.txt": {
        "validated_document_type": "pedoman",
        "multi_branch_type": "primary_branch_with_multi_event_intro",
        "is_multi_branch": False,
        "branch_codes": ["BR_SCIENTIFIC_PAPER", "BR_STEM_PROJECT"],
        "secondary_event_branch_codes": ["BR_DEBATE_SPEECH", "BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Karya Tulis Ilmiah & Inovasi Energi (Energynovation Ideas Competition)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Terkonfirmasi sebagai Pedoman Kompetisi Energynovation Ideas Competition (EIC) PGTC 2026. "
            "Pengantar dokumen menyebutkan 3 kompetisi PGTC (Debat British Parliamentary, EIC, dan ide bisnis/startup), "
            "tetapi seluruh isi teknis pedoman ini khusus mengatur cabang Energynovation Ideas Competition (Karya Tulis Ilmiah & Poster/Video)."
        ),
        "evidence_pattern": r"PEDOMAN KOMPETISI.*ENERGYNOVATION IDEAS COMPETITION.*PERTAMINA GOES TO CAMPUS 2026",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Pedoman FIKSI SMA SMK 2024.txt": {
        "validated_document_type": "pedoman",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_ENTREPRENEURSHIP_INNOVATION", "BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Multi-Cabang: Inovasi & Kewirausahaan (FIKSI - 11 Bidang)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": "Audit dokumen readable_with_ocr_noise: Terkonfirmasi sebagai Pedoman FIKSI SMA/MA/SMK Tahun 2024 (11 bidang).",
        "evidence_pattern": r"PEDOMAN.*FESTIVAL INOVASI DAN KEWIRAUSAHAAN SISWA INDONESIA.*2024",
        "reconversion_status": "needs_font_encoding_fix",
        "reconversion_reason": "Terdapat 13 karakter null byte (\\x00) dari konversi simbol bullet kustom pada PDF.",
    },
    "Preliminary Guidebook ECC.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ENG_CASE"],
        "validated_competition_branch": "Engineering Case Competition (Metallurgy)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Audit dokumen readable_with_ocr_noise: Terkonfirmasi sebagai Preliminary Guidebook Engineering Case Competition (ECC) MetalFest ITB.",
        "evidence_pattern": r"Engineering Case Competition.*MetalFest ITB",
        "reconversion_status": "needs_ocr_cleanup",
        "reconversion_reason": "Terdapat kata yang tergabung underscore dan derau OCR multi-kolom ('metalurgi_memiliki', 'Inteenegrgi rte', 'em_b_aplei').",
    },
    "STEM GUIDEBOOK.txt": {
        "validated_document_type": "guidebook",
        "multi_branch_type": "primary_branch_with_multi_event_intro",
        "is_multi_branch": False,
        "branch_codes": ["BR_HACKATHON", "BR_CYBERSECURITY_CTF"],
        "secondary_event_branch_codes": ["BR_STEM_PROJECT", "BR_BUSINESS_PLAN"],
        "validated_competition_branch": "Hackathon — Smart Technology and Security Hackathon / STASH (Techtonic UI 3.0 — Filename Mismatch: File bernama STEM GUIDEBOOK.txt)",
        "validated_classification_status": "needs_review_filename_mismatch",
        "audit_reason": (
            "TEMUAN AUDIT KRITIS (Tertukarnya Nama File vs Isi Dokumen): Nama file adalah 'STEM GUIDEBOOK.txt', "
            "dan halaman 1–5 memuat pengenalan umum 3 cabang Techtonic UI 3.0. Namun bagian panduan utama "
            "(halaman 28–38) secara eksplisit adalah panduan cabang Hackathon ('Welcome to Hackathon Competition of Techtonic UI 3.0!', "
            "Tema: 'STASH (Smart Technology and Security Hackathon)', Manajer: Sultan Ariq Zaman Syari). "
            "Isi file ini tertukar dengan 'HACKATHON GUIDEBOOK.txt'."
        ),
        "evidence_pattern": r"Welcome to Hackathon Competition of Techtonic UI 3\.0!.*STASH \(Smart Technology and Security Hackathon\)",
        "reconversion_status": "needs_filename_swap_fix",
        "reconversion_reason": "Nama file 'STEM GUIDEBOOK.txt' tertukar dengan 'HACKATHON GUIDEBOOK.txt' pada saat penyimpanan/konversi PDF sumber.",
    },
    "STUDY CASE COMPETITION UI SCIENCE OLYMPIAD 2026.txt": {
        "validated_document_type": "panduan_pelaksanaan",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ENG_CASE"],
        "validated_competition_branch": "Study Case Competition (Science & Environment)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'ketentuan_lomba' menjadi 'panduan_pelaksanaan' (kategori makro: dokumen_panduan_kompetisi). "
            "Teks bagian Penutup secara eksplisit menyebut dokumen ini sebagai 'panduan pelaksanaan Lomba Study Case Competition UI Science Olympiad 2026'."
        ),
        "evidence_pattern": r"Demikian panduan pelaksanaan Lomba Study Case Competition UI Science Olympiad 2026",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Sosialisasi LKS Dikmen 2025.txt": {
        "validated_document_type": "paparan_sosialisasi",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_VOCATIONAL_LKS"],
        "validated_competition_branch": "Multi-Cabang: Kompetensi Vokasi/Keahlian Siswa (LKS - 37 Bidang)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Terkonfirmasi sebagai dokumen paparan/slide Sosialisasi LKS Dikmen 2025 (kategori makro: 'dokumen_sosialisasi') "
            "yang memetakan 37 cabang lomba ke dalam 6 kelompok bidang keahlian."
        ),
        "evidence_pattern": r"SOSIALISASI.*LOMBA KOMPETENSI SISWA.*37 Cabang Lomba",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "Syarat & Ketentuan PIMA 2026.txt": {
        "validated_document_type": "syarat_ketentuan",
        "multi_branch_type": "multi_branch_event",
        "is_multi_branch": True,
        "branch_codes": ["BR_JOURNALISM"],
        "validated_competition_branch": "Multi-Cabang: Jurnalistik Media (Hardnews, Feature, Foto Cerita, Televisi, Radio)",
        "validated_classification_status": "validated_multi_branch",
        "audit_reason": (
            "Perbaikan sub-tipe document_type dari 'ketentuan_lomba' menjadi 'syarat_ketentuan' "
            "(kategori makro: dokumen_ketentuan_dan_petunjuk_teknis) sesuai judul dokumen Syarat & Ketentuan PIMA 2026 "
            "untuk 5 kategori jurnalistik mahasiswa."
        ),
        "evidence_pattern": r"1\.\s*Laporan Utama \(Feature\).*2\.\s*Berita Singkat \(Hardnews\).*3\.\s*Foto Cerita.*4\.\s*Jurnalistik Televisi.*5\.\s*Jurnalistik Radio",
        "reconversion_status": "needs_ocr_cleanup",
        "reconversion_reason": "Terdapat kesalahan pengenalan karakter OCR pada banner/tanggal ('31 Besember 2026', 'mt: ee oe F', 'tesien«').",
    },
    "[AIC] AI Innovation Challenge.txt": {
        "validated_document_type": "rulebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_AI"],
        "validated_competition_branch": "Artificial Intelligence (AI Innovation Challenge)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Audit dokumen readable_with_ocr_noise: Terkonfirmasi sebagai Rulebook AI Innovation Challenge (COMPFEST 17).",
        "evidence_pattern": r"AI Innovation Challenge.*Rulebook",
        "reconversion_status": "needs_ocr_cleanup",
        "reconversion_reason": "Artefak OCR pada grafik header ('Tam@e)it-lelelae-harelam') dan substitusi huruf 'AI' menjadi 'Al'.",
    },
    "[CTF] Capture The Flag.txt": {
        "validated_document_type": "rulebook",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_CYBERSECURITY_CTF"],
        "validated_competition_branch": "Cybersecurity / Capture The Flag (CTF)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Rulebook Capture The Flag (CTF) COMPFEST 17.",
        "evidence_pattern": r"Capture The Flag.*Rulebook",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "essay.txt": {
        "validated_document_type": "ketentuan_lomba",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_ESSAY"],
        "validated_competition_branch": "Essay Competition (Inovasi Teknologi Pelajar)",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": (
            "Perbaikan document_type dari 'pedoman' menjadi 'ketentuan_lomba' (kategori makro: dokumen_ketentuan_dan_petunjuk_teknis). "
            "Pada tahap 1 terklasifikasi 'pedoman' karena kalimat 'Format penulisan mengikuti pedoman yang ditentukan', "
            "padahal tajuk utama dokumen adalah 'Ketentuan / IT - Competition AMIKOM Surakarta (IT-CAS) 2026 / ESSAY (Pelajar)' (606 kata)."
        ),
        "evidence_pattern": r"Ketentuan\s+IT - Competition AMIKOM Surakarta \(IT-CAS\) 2026\s+ESSAY \(Pelajar\)",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
    "juknis-data-science.txt": {
        "validated_document_type": "petunjuk_teknis",
        "multi_branch_type": "single_branch",
        "is_multi_branch": False,
        "branch_codes": ["BR_DATA_SCIENCE"],
        "validated_competition_branch": "Data Science",
        "validated_classification_status": "validated_single_branch",
        "audit_reason": "Terkonfirmasi sebagai Petunjuk Teknis (Juknis) Lomba Data Science.",
        "evidence_pattern": r"Data Science",
        "reconversion_status": "clean",
        "reconversion_reason": "",
    },
}


def extract_verbatim_evidence(
    raw_text: str,
    pattern: Optional[str],
    max_len: int = 240,
    verbatim_clauses: Optional[List[str]] = None,
) -> str:
    """Extract a clean verbatim evidence snippet from raw document text."""
    stripped = raw_text.lstrip("\ufeff").strip()
    if not stripped:
        return "[DOKUMEN KOSONG: 0 karakter dapat dibaca, hanya 3 byte UTF-8 BOM (\\ufeff)]"

    normalized = re.sub(r"\s+", " ", stripped)
    if verbatim_clauses:
        matched_clauses = [c for c in verbatim_clauses if c in normalized]
        if len(matched_clauses) == len(verbatim_clauses):
            return " ... ".join(matched_clauses)

    if pattern:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 20)
            end = min(len(normalized), match.end() + 60)
            snippet = normalized[start:end].strip()
            if len(snippet) > max_len:
                snippet = snippet[:max_len].rstrip() + "..."
            return snippet

    # Fallback: first non-empty lines normalized
    snippet = normalized[:max_len].strip()
    if len(normalized) > max_len:
        snippet += "..."
    return snippet


def derive_domain_codes(branch_codes: List[str]) -> List[str]:
    """Derive unique ordered domain codes from branch codes."""
    domains: List[str] = []
    for code in branch_codes:
        dom = BRANCH_TO_DOMAIN.get(code)
        if dom and dom not in domains:
            domains.append(dom)
    return domains


def get_recommended_stage3_metadata_schema() -> Dict[str, Any]:
    """Return the recommended metadata structure for Stage 3 (Information & Requirement Extraction)."""
    return {
        "schema_version": "0.3.0-draft",
        "description": "Rekomendasi struktur metadata terstandar untuk Tahap 3 (Ekstraksi Persyaratan, Indikator Penilaian, dan Kebutuhan Kompetensi).",
        "entities": {
            "document_metadata": {
                "document_id": "str (contoh: DOC-027)",
                "file_name": "str",
                "file_sha256": "str (hash integritas file sumber)",
                "macro_document_category": "enum (dokumen_panduan_kompetisi | dokumen_ketentuan_dan_petunjuk_teknis | modul_pembelajaran | katalog_karya_atau_finalis | dokumen_sosialisasi | dokumen_lainnya | unknown)",
                "validated_document_type": "str",
                "readability_status": "enum (readable | readable_with_ocr_noise | empty)",
                "reconversion_status": "enum (clean | needs_reextraction_empty | needs_filename_swap_fix | needs_font_encoding_fix | needs_ocr_cleanup)",
                "is_eligible_for_requirement_extraction": "bool (True untuk dokumen_panduan_kompetisi dan dokumen_ketentuan_dan_petunjuk_teknis yang tidak empty)",
            },
            "competition_event_metadata": {
                "event_id": "str (ID induk penyelenggaraan/event, misal: EVT-ITFEST-2026)",
                "event_name": "str (Nama event induk, misal: IT Fest 2026 / Techtonic UI 3.0)",
                "organizer_institution": "str (Institusi/universitas/kementerian penyelenggara)",
                "organizer_unit": "str (Himpunan/BEM/Balai penyelenggara)",
                "event_year": "int (2024 | 2025 | 2026 | 2027)",
                "scale": "enum (national | international | regional | internal)",
                "general_theme": "str (Tema besar acara)",
                "sub_themes": "List[str]",
                "multi_branch_type": "enum (single_branch | multi_branch_event | composite_branch_competition | primary_branch_with_multi_event_intro)",
            },
            "competition_branch_unit": {
                "branch_unit_id": "str (Penting untuk dokumen multi-cabang: 1 dokumen dapat menghasilkan N unit cabang lomba terpisah, misal DOC-027 -> 4 unit cabang)",
                "document_id": "str (FK ke document_metadata)",
                "branch_name_raw": "str (Nama cabang tertulis di dokumen)",
                "taxonomy_domain_codes": "List[str] (misal: ['DOM_IT_DIGITAL'])",
                "taxonomy_branch_codes": "List[str] (misal: ['BR_CYBERSECURITY_CTF'])",
                "section_char_span": "Tuple[int, int] (Rentang halaman/karakter spesifik cabang tersebut di dalam dokumen multi-cabang)",
                "participant_education_level": "List[enum] (SMP | SMA_MA | SMK | Mahasiswa_D3_D4_S1 | Umum)",
                "team_composition_rule": {
                    "participation_mode": "enum (individual | team | both)",
                    "min_members": "Optional[int]",
                    "max_members": "Optional[int]",
                    "cross_major_allowed": "Optional[bool]",
                    "cross_institution_allowed": "Optional[bool]",
                },
                "stages_and_deliverables": "List[Dict[stage_name, deliverable_type, format_constraints, deadline]]",
                "evaluation_criteria": "List[Dict[criterion_name, weight_percentage, sub_indicators, source_status]]",
                "evidence_trace": {
                    "source_status": "enum (explicit | inferred | unverified)",
                    "verbatim_quote": "str",
                    "line_or_page_reference": "str",
                },
            },
        },
    }


def validate_inventory(
    raw_txt_dir: Path,
    initial_inventory_json: Path,
    taxonomy_json_path: Path,
    output_validated_csv: Path,
    output_validated_json: Path,
    output_audit_report_json: Path,
    output_processed_taxonomy_json: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run Stage 2 validation on the Stage 1 inventory without modifying original files."""
    if not initial_inventory_json.exists():
        raise FileNotFoundError(f"Initial inventory JSON not found: {initial_inventory_json}")
    if not raw_txt_dir.exists():
        raise FileNotFoundError(f"Raw TXT directory not found: {raw_txt_dir}")
    if not taxonomy_json_path.exists():
        raise FileNotFoundError(f"Taxonomy JSON not found: {taxonomy_json_path}")

    # Load initial inventory and taxonomy
    initial_data = json.loads(initial_inventory_json.read_text(encoding="utf-8"))
    taxonomy_data = json.loads(taxonomy_json_path.read_text(encoding="utf-8"))

    # Optionally sync taxonomy JSON to data/processed/competition_taxonomy.json
    if output_processed_taxonomy_json is not None:
        output_processed_taxonomy_json.parent.mkdir(parents=True, exist_ok=True)
        if taxonomy_json_path.resolve() != output_processed_taxonomy_json.resolve():
            shutil.copyfile(taxonomy_json_path, output_processed_taxonomy_json)

    initial_docs: List[Dict[str, Any]] = initial_data.get("documents", [])
    validated_records: List[ValidatedDocumentRecord] = []

    for doc in initial_docs:
        file_name = doc["file_name"]
        txt_path = raw_txt_dir / file_name
        raw_text = txt_path.read_text(encoding="utf-8", errors="replace") if txt_path.exists() else ""

        spec = DOCUMENT_AUDIT_SPEC.get(file_name)
        if spec is None:
            raise KeyError(f"Missing Stage 2 audit specification for document: {file_name}")

        validated_doc_type = spec["validated_document_type"]
        macro_category = DOCUMENT_TYPE_TO_MACRO_CATEGORY[validated_doc_type]
        branch_codes = list(spec.get("branch_codes", []))
        secondary_codes = list(spec.get("secondary_event_branch_codes", []))
        domain_codes = derive_domain_codes(branch_codes)
        validated_branch = spec["validated_competition_branch"]
        validated_status = spec["validated_classification_status"]

        orig_doc_type = doc["document_type"]
        orig_branch = doc["competition_branch"]
        orig_status = doc["classification_status"]

        doc_type_changed = validated_doc_type != orig_doc_type
        branch_changed = validated_branch != orig_branch
        classification_changed = doc_type_changed or branch_changed

        evidence = extract_verbatim_evidence(
            raw_text,
            spec.get("evidence_pattern"),
            verbatim_clauses=spec.get("verbatim_clauses"),
        )

        record = ValidatedDocumentRecord(
            document_id=doc["document_id"],
            file_name=file_name,
            document_name=doc["document_name"],
            character_count=doc["character_count"],
            word_count=doc["word_count"],
            readability_status=doc["readability_status"],
            document_type=orig_doc_type,
            competition_branch=orig_branch,
            classification_status=orig_status,
            notes=doc["notes"],
            original_document_type=orig_doc_type,
            original_competition_branch=orig_branch,
            original_classification_status=orig_status,
            macro_document_category=macro_category,
            validated_document_type=validated_doc_type,
            multi_branch_type=spec["multi_branch_type"],
            is_multi_branch=bool(spec["is_multi_branch"]),
            domain_codes=domain_codes,
            branch_codes=branch_codes,
            secondary_event_branch_codes=secondary_codes,
            validated_competition_branch=validated_branch,
            validated_classification_status=validated_status,
            document_type_changed=doc_type_changed,
            competition_branch_changed=branch_changed,
            classification_changed=classification_changed,
            audit_reason=spec["audit_reason"],
            content_evidence=evidence,
            reconversion_status=spec["reconversion_status"],
            reconversion_reason=spec["reconversion_reason"],
        )
        validated_records.append(record)

    # Compute summary breakdowns
    macro_cat_counts: Dict[str, int] = {}
    val_doc_type_counts: Dict[str, int] = {}
    val_status_counts: Dict[str, int] = {}
    multi_branch_type_counts: Dict[str, int] = {}
    domain_counts: Dict[str, int] = {}
    branch_code_counts: Dict[str, int] = {}
    reconversion_counts: Dict[str, int] = {}

    for rec in validated_records:
        macro_cat_counts[rec.macro_document_category] = macro_cat_counts.get(rec.macro_document_category, 0) + 1
        val_doc_type_counts[rec.validated_document_type] = val_doc_type_counts.get(rec.validated_document_type, 0) + 1
        val_status_counts[rec.validated_classification_status] = (
            val_status_counts.get(rec.validated_classification_status, 0) + 1
        )
        multi_branch_type_counts[rec.multi_branch_type] = (
            multi_branch_type_counts.get(rec.multi_branch_type, 0) + 1
        )
        reconversion_counts[rec.reconversion_status] = reconversion_counts.get(rec.reconversion_status, 0) + 1

        for dom in rec.domain_codes:
            domain_counts[dom] = domain_counts.get(dom, 0) + 1
        for br in rec.branch_codes:
            branch_code_counts[br] = branch_code_counts.get(br, 0) + 1

    changed_records = [asdict(r) for r in validated_records if r.classification_changed]
    special_status_audited = [
        asdict(r)
        for r in validated_records
        if r.original_classification_status in ("needs_review", "unclassified")
        or r.readability_status in ("empty", "readable_with_ocr_noise")
    ]
    reconversion_list = [
        {
            "document_id": r.document_id,
            "file_name": r.file_name,
            "readability_status": r.readability_status,
            "reconversion_status": r.reconversion_status,
            "reconversion_reason": r.reconversion_reason,
            "recommended_action": _recommend_repair_action(r.reconversion_status),
        }
        for r in validated_records
        if r.reconversion_status != "clean"
    ]

    summary = {
        "total_documents_audited": len(validated_records),
        "total_classification_changed": len(changed_records),
        "document_type_changed_count": sum(1 for r in validated_records if r.document_type_changed),
        "competition_branch_changed_count": sum(1 for r in validated_records if r.competition_branch_changed),
        "multi_branch_documents_count": sum(1 for r in validated_records if r.is_multi_branch),
        "single_branch_documents_count": sum(
            1 for r in validated_records if not r.is_multi_branch and r.branch_codes
        ),
        "non_competition_or_empty_count": sum(1 for r in validated_records if not r.branch_codes),
        "documents_requiring_repair_or_reconversion": len(reconversion_list),
        "macro_document_category_breakdown": macro_cat_counts,
        "validated_document_type_breakdown": val_doc_type_counts,
        "validated_classification_status_breakdown": val_status_counts,
        "multi_branch_type_breakdown": multi_branch_type_counts,
        "taxonomy_domain_document_frequency": domain_counts,
        "taxonomy_branch_code_document_frequency": branch_code_counts,
        "reconversion_status_breakdown": reconversion_counts,
    }

    # Write validated CSV
    output_validated_csv.parent.mkdir(parents=True, exist_ok=True)
    if validated_records:
        csv_fields = list(validated_records[0].to_csv_dict().keys())
        with output_validated_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fields)
            writer.writeheader()
            for rec in validated_records:
                writer.writerow(rec.to_csv_dict())

    # Write validated JSON
    output_validated_json.parent.mkdir(parents=True, exist_ok=True)
    validated_payload = {
        "summary": summary,
        "taxonomy_version": taxonomy_data.get("taxonomy_version", "0.2.0"),
        "documents": [asdict(r) for r in validated_records],
    }
    output_validated_json.write_text(
        json.dumps(validated_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write detailed audit report JSON
    output_audit_report_json.parent.mkdir(parents=True, exist_ok=True)
    audit_report_payload = {
        "audit_summary": summary,
        "classification_changes": changed_records,
        "audited_flagged_and_noisy_documents": special_status_audited,
        "documents_needing_repair_or_reconversion": reconversion_list,
        "recommended_stage3_metadata_schema": get_recommended_stage3_metadata_schema(),
    }
    output_audit_report_json.write_text(
        json.dumps(audit_report_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info(
        "Validated %d documents (%d classification updates, %d needing repair/reconversion).",
        len(validated_records),
        len(changed_records),
        len(reconversion_list),
    )
    return validated_payload


def _recommend_repair_action(reconversion_status: str) -> str:
    """Return concrete technical action for each reconversion status."""
    actions = {
        "needs_reextraction_empty": (
            "Lakukan ekstraksi ulang dari PDF asli menggunakan OCR (Tesseract / PaddleOCR) "
            "karena PDF kemungkinan berupa hasil scan gambar tanpa text layer."
        ),
        "needs_filename_swap_fix": (
            "Perbaiki pemetaan nama file antara 'HACKATHON GUIDEBOOK.txt' dan 'STEM GUIDEBOOK.txt' "
            "pada metadata (tanpa mengubah file mentah asli) atau pisahkan halaman 15-27 (PE STEM) dan 28-38 (Hackathon)."
        ),
        "needs_font_encoding_fix": (
            "Jalankan OCR ulang pada halaman yang mengandung font kustom/ligatur rusak, "
            "atau terapkan normalisasi karakter kontrol (\\x00, \\x1e, \\x1f) sebelum ekstraksi persyaratan."
        ),
        "needs_ocr_cleanup": (
            "Terapkan post-processing teks (normalisasi spasi/underscore dan penghapusan noise banner) "
            "atau ekstraksi ulang berbasis layout-aware PDF parser."
        ),
    }
    return actions.get(reconversion_status, "Tidak memerlukan perbaikan.")
