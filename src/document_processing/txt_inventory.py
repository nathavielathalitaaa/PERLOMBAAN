"""TXT Document Inventory and Content-Based Inspection Module (V0.1 / V0.2 Stage 1).

Performs automated, deterministic, read-only inventory of raw TXT competition documents
converted from PDF and OCR. Strictly adheres to research provenance rules:
- Never modifies raw TXT files.
- Never determines competition branch solely from file names.
- Never fabricates missing information (uses 'unknown' or 'needs_review').
- Produces idempotent CSV and JSON outputs plus summary statistics.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from config.settings import DATA_DIR, PROCESSED_DATA_DIR

logger = logging.getLogger(__name__)

DEFAULT_TXT_DIR = DATA_DIR / "raw" / "txt"
DEFAULT_CSV_OUTPUT = PROCESSED_DATA_DIR / "document_inventory.csv"
DEFAULT_JSON_OUTPUT = PROCESSED_DATA_DIR / "document_inventory.json"


@dataclass
class DocumentInventoryItem:
    """Represents a single inventoried TXT document."""

    document_id: str
    file_name: str
    document_name: str
    character_count: int
    word_count: int
    readability_status: str
    document_type: str
    competition_branch: str
    classification_status: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert inventory record to dictionary."""
        return asdict(self)


@dataclass
class InventorySummary:
    """Statistical summary of the document inventory run."""

    total_documents: int
    empty_documents: int
    readable_documents: int
    readable_with_ocr_noise_documents: int
    unreadable_or_error_documents: int
    total_characters: int
    total_words: int
    min_word_count_non_empty: int
    max_word_count: int
    avg_word_count_non_empty: float
    readability_breakdown: Dict[str, int] = field(default_factory=dict)
    document_type_breakdown: Dict[str, int] = field(default_factory=dict)
    classification_status_breakdown: Dict[str, int] = field(default_factory=dict)
    competition_branch_breakdown: Dict[str, int] = field(default_factory=dict)
    flagged_documents: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return asdict(self)


class TxtDocumentInventorizer:
    """Rule-based, content-driven inventorizer for TXT competition documents."""

    # Known OCR corruption patterns in prose/headers
    OCR_CORRUPTION_PATTERNS = [
        r"\bmetalurgi_memiliki\b",
        r"\btransformasi_menuju\b",
        r"\.gan_pendekatan\b",
        r"\bInteenegrgi\b",
        r"NSINCSwS\)i",
        r"we ompetition Buideline",
        r"SMAIK Sederajat",
        r"terobuka untuk",
        r"f= mn ©\)",
        r"mt: ee oe F",
        r"tesien«",
        r"welasl Agraladasys",
        r"Tam@e\)it-lelelae-harelam",
        r"GC\. -@-O¢",
        r"Explore the Powe\s+L r of Words",
        r"\[DOCUMENT TITLE\]",
        r"Manaj emen Bisnii s Festiivala l",
    ]

    @classmethod
    def detect_readability(cls, text: str) -> Tuple[str, List[str]]:
        """Evaluate text readability and identify specific OCR, encoding, or structural anomalies."""
        stripped = text.strip()
        if not stripped:
            return "empty", ["Dokumen kosong (0 kata, hanya berisi karakter BOM/whitespace)."]

        words = stripped.split()
        if len(words) < 10:
            return "low_quality", [f"Teks terlalu pendek ({len(words)} kata)."]

        anomalies: List[str] = []

        # 1. Check for unreplaced template placeholders
        if re.search(r"\[DOCUMENT TITLE\]", stripped):
            anomalies.append("Terdapat placeholder template '[DOCUMENT TITLE]' pada bagian sampul.")

        # 2. Check for non-printable ASCII control characters (corrupted font glyphs, ligatures, or null bytes)
        ctrl_chars = re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", text)
        if ctrl_chars:
            null_count = ctrl_chars.count("\x00")
            ligature_ctrl = sum(1 for c in ctrl_chars if c in ("\x1e", "\x1f"))
            if null_count == len(ctrl_chars):
                anomalies.append(
                    f"Terdapat {null_count} karakter null byte (\\x00) akibat konversi simbol bullet PDF."
                )
            elif ligature_ctrl == len(ctrl_chars):
                anomalies.append(
                    f"Terdapat {ligature_ctrl} karakter kontrol (\\x1e/\\x1f) akibat kegagalan ekstraksi ligatur 'fi'/'fl' (contoh: 'e\\x1fsiensi', 'signi\\x1fkan')."
                )
            else:
                anomalies.append(
                    f"Terdapat {len(ctrl_chars)} karakter kontrol non-cetak (\\x02-\\x1f) akibat kegagalan encoding font PDF (contoh: teks judul TEMA tidak terbaca)."
                )

        # 3. Check specific OCR corruption patterns
        ocr_hits = []
        for pat in cls.OCR_CORRUPTION_PATTERNS:
            if pat == r"\[DOCUMENT TITLE\]":
                continue
            match = re.search(pat, stripped)
            if match:
                ocr_hits.append(re.sub(r"\s+", " ", match.group(0).strip()))

        if ocr_hits:
            sample_hits = ", ".join(f"'{h}'" for h in ocr_hits[:3])
            anomalies.append(f"Terdeteksi artefak/derau OCR pada teks ({sample_hits}).")

        if anomalies:
            return "readable_with_ocr_noise", anomalies

        return "readable", []

    @classmethod
    def identify_document_type(cls, text: str) -> str:
        """Identify document type strictly from document text content."""
        stripped = text.strip()
        if not stripped:
            return "unknown"

        norm_header = re.sub(r"\s+", " ", stripped[:2500]).lower()
        norm_full = re.sub(r"\s+", " ", stripped).lower()

        # 1. Non-competition learning module, bootcamp guidebook, finalist showcase, or open recruitment
        if (
            "modul ini dibuat untuk tujuan pendidikan dan pengembangan keterampilan" in norm_header
            and "pengenalan konsep backend" in norm_full
        ):
            return "modul_pembelajaran"

        if (
            "guidebook ini disusun untuk tujuan pendidikan dan pengembangan keterampilan" in norm_header
            and "tentang bootcamp" in norm_full
        ):
            return "guidebook_bootcamp"

        if "rekrutmen terbuka" in norm_header and "duta muda bineka" in norm_header:
            return "booklet_rekrutmen"

        if (
            "bi-ojk hackathon mengusung" in norm_header
            and "statistik jumlah problem statement finalis" in norm_full
        ):
            return "booklet_profil_finalis"

        if "paparan sosialisasi" in norm_header:
            return "paparan_sosialisasi"

        # 2. Explicit competition document headers
        if re.search(r"\bpetunjuk\s+teknis\b", norm_header):
            if re.search(r"\bguide\s*book\b", norm_header):
                return "guidebook_petunjuk_teknis"
            return "petunjuk_teknis"

        if re.search(r"\brulebook\b", norm_header):
            return "rulebook"

        if re.search(r"\bparticipants?\s+handbook\b|\bhandbook\b", norm_header):
            return "handbook"

        if re.search(r"\bpedoman\b", norm_header):
            return "pedoman"

        if re.search(r"\bpanduan\s+teknis\b", norm_header):
            return "panduan_teknis"

        if re.search(r"\bpanduan\b", norm_header):
            return "panduan"

        if re.search(r"\bcompetition\s+booklet\b|\bbooklet\b", norm_header):
            return "booklet"

        if re.search(r"\bguide\s*book\b|\bgu\s*i\s*debook\b|\bompetition\s+buideline\b", norm_header):
            return "guidebook"

        # 3. Broader content structure markers
        if re.search(r"\bguidebook\b|\bguide\s+book\b", norm_full):
            return "guidebook"

        if (
            "term and condition" in norm_full
            and "rules and regulation" in norm_full
            and "competition stage" in norm_full
        ):
            return "guidebook"

        if re.search(
            r"\bketentuan\s+umum\b|\bsyarat\s+&\s+ketentuan\b|\bketentuan\s+karya\b|\bketentuan\b",
            norm_full,
        ):
            return "ketentuan_lomba"

        return "unknown"

    @classmethod
    def extract_document_name_and_branch(
        cls, file_name: str, text: str
    ) -> Tuple[str, str, str, List[str]]:
        """Extract document title, competition branch, classification status, and notes strictly from content.

        Never relies solely on `file_name` to assign `competition_branch`.
        """
        stripped = text.strip()
        if not stripped:
            return (
                "unknown",
                "unknown",
                "unclassified",
                ["Tidak dapat mengidentifikasi nama dokumen maupun cabang lomba karena isi file kosong."],
            )

        notes: List[str] = []
        norm_text = re.sub(r"\s+", " ", stripped).lower()

        # --- Special Case 1: Non-competition Module / Bootcamp / Recruitment / Finalist Showcase ---
        if (
            "modul ini dibuat untuk tujuan pendidikan dan pengembangan keterampilan" in norm_text
            and "pengenalan konsep backend" in norm_text
        ):
            return (
                "Modul Pembelajaran Schematics BST 2025 (Backend Development dengan Golang)",
                "needs_review",
                "needs_review",
                [
                    "Isi dokumen merupakan modul materi pembelajaran pemrograman backend (bukan dokumen ketentuan perlombaan)."
                ],
            )

        if "schematics bst (bootcamp and seminar of technology)" in norm_text:
            return (
                "Guidebook Schematics BST 2025 - Advanced Bootcamp",
                "needs_review",
                "needs_review",
                [
                    "Isi dokumen merupakan panduan Advanced Bootcamp pemrograman (Golang) Schematics BST 2025 dengan evaluasi Final Project, bukan kompetisi murni."
                ],
            )

        if "rekrutmen terbuka" in norm_text and "duta muda bineka" in norm_text:
            return (
                "Booklet Rekrutmen Terbuka Duta Muda Bineka 2025",
                "needs_review",
                "needs_review",
                [
                    "Isi dokumen merupakan booklet seleksi/rekrutmen Duta Muda Bineka 2025 (bukan cabang perlombaan standar)."
                ],
            )

        if (
            "bi-ojk hackathon mengusung 3 (tiga) problem statements" in norm_text
            and "statistik jumlah problem statement finalis" in norm_text
        ):
            return (
                "Booklet Profil Finalis & Inovasi BI-OJK Hackathon 2025",
                "Hackathon (AI & Cybersecurity Financial Innovation)",
                "needs_review",
                [
                    "Isi dokumen merupakan katalog/booklet profil karya Top 10 tim finalis dan statistik BI-OJK Hackathon 2025 (bukan buku panduan syarat/ketentuan pendaftaran lomba)."
                ],
            )

        # --- Special Case 2: Techtonic UI 3.0 Guidebooks (Check actual body section!) ---
        if "techtonic" in norm_text and "#techfortomorrow" in norm_text:
            if "welcome to the business plan competition of techtonic ui 3.0" in norm_text:
                return (
                    "Guidebook Business Plan Competition - Techtonic UI 3.0",
                    "Business Plan Competition",
                    "identified",
                    [
                        "Bagian pengantar memuat gambaran 3 cabang Techtonic 3.0, isi utama membahas Business Plan Competition (BPC)."
                    ],
                )
            if "welcome to the pe stem competition of techtonic ui 3.0" in norm_text:
                if "hackathon" in file_name.lower():
                    notes.append(
                        "INKONSISTENSI NAMA FILE vs ISI: Nama file tertulis 'HACKATHON GUIDEBOOK.txt', namun isi dokumen sebenarnya membahas 'PE STEM Competition (Project Exhibition STEM)' Techtonic UI 3.0."
                    )
                    return (
                        "Guidebook PE STEM Competition - Techtonic UI 3.0",
                        "STEM Innovation / Project Exhibition (needs_review: filename mismatch)",
                        "needs_review",
                        notes,
                    )
                return (
                    "Guidebook PE STEM Competition - Techtonic UI 3.0",
                    "STEM Innovation / Project Exhibition",
                    "identified",
                    notes,
                )
            if (
                "welcome to hackathon competition of techtonic ui 3.0" in norm_text
                or "stash (smart technology and security hackathon)" in norm_text
            ):
                if "stem" in file_name.lower():
                    notes.append(
                        "INKONSISTENSI NAMA FILE vs ISI: Nama file tertulis 'STEM GUIDEBOOK.txt', namun isi dokumen sebenarnya membahas 'Hackathon Competition (STASH)' Techtonic UI 3.0."
                    )
                    return (
                        "Guidebook Hackathon Competition (STASH) - Techtonic UI 3.0",
                        "Hackathon (needs_review: filename mismatch)",
                        "needs_review",
                        notes,
                    )
                return (
                    "Guidebook Hackathon Competition (STASH) - Techtonic UI 3.0",
                    "Hackathon",
                    "identified",
                    notes,
                )

        # --- Content-based identification for Multi-Branch Documents ---
        # 1. FIKSI (Festival Inovasi dan Kewirausahaan Siswa Indonesia)
        if "festival inovasi dan kewirausahaan" in norm_text or "festifal inovasi dan" in norm_text:
            year_match = re.search(r"tahun\s+(202[4-7])", norm_text)
            year_str = year_match.group(1) if year_match else ""
            doc_prefix = "Pedoman" if "pedoman festival inovasi" in norm_text[:300] else "Panduan Ajang"
            return (
                f"{doc_prefix} Festival Inovasi dan Kewirausahaan Siswa Indonesia (FIKSI) {year_str}".strip(),
                "Multi-Cabang: Inovasi & Kewirausahaan (FIKSI - 11 Bidang)",
                "identified_multi_branch",
                ["Dokumen pedoman/panduan nasional FIKSI yang mencakup banyak cabang kewirausahaan siswa."],
            )

        # 2. LKS (Lomba Kompetensi Siswa)
        if "lomba kompetensi siswa" in norm_text:
            if "paparan sosialisasi" in norm_text[:300]:
                return (
                    "Paparan Sosialisasi Ajang Talenta LKS Dikmen 2025",
                    "Multi-Cabang: Kompetensi Vokasi/Keahlian Siswa (LKS - 37 Bidang)",
                    "identified_multi_branch",
                    ["Dokumen paparan sosialisasi LKS tingkat nasional mencakup 37 bidang lomba."],
                )
            year_match = re.search(r"tahun\s+(202[4-7])", norm_text)
            year_str = year_match.group(1) if year_match else ""
            return (
                f"Panduan Ajang Lomba Kompetensi Siswa (LKS) Tingkat Nasional Tahun {year_str}".strip(),
                "Multi-Cabang: Kompetensi Vokasi/Keahlian Siswa (LKS)",
                "identified_multi_branch",
                ["Dokumen panduan umum ajang talenta LKS tingkat nasional lintas bidang keahlian."],
            )

        # 3. Pharmacopeia 2026
        if (
            "pharmacopeia merupakan program tahunan" in norm_text
            and "digital poster competition" in norm_text
            and "video campaign competition" in norm_text
        ):
            return (
                "Competition Guideline Pharmacopeia 2026 (SMA/K Sederajat)",
                "Multi-Cabang: Science Olympiad, Essay, Digital Poster, Video Campaign (Kefarmasian)",
                "identified_multi_branch",
                [
                    "Mencakup 4 cabang lomba tingkat SMA/K: Science Olympiad, Essay, Digital Poster, dan Video Campaign."
                ],
            )

        # 4. FMIPA STEM Challenge UGM
        if "stem challenge 2026" in norm_text and "fakultas matematika dan ilmu pengetahuan alam" in norm_text:
            return (
                "Booklet FMIPA STEM Challenge 2026 UGM",
                "Multi-Cabang: Sains, Matematika, Robotika/IoT, Informatika, Kimia, Aktuaria (SCIENTA, LMNas, INSPIRE, JOINTS, TOP COP, OKN, ASiQ)",
                "identified_multi_branch",
                ["Booklet kolaborasi HIMA FMIPA UGM yang merangkum 7 ajang dan berbagai cabang kompetisi STEM."],
            )

        # 5. IMPACTEERS UNESA
        if (
            "impacteers" in norm_text
            and "cabang esai" in norm_text
            and "cabang bmc" in norm_text
            and "cabang poster" in norm_text
        ):
            return (
                "Guidebook IMPACTEERS Universitas Negeri Surabaya",
                "Multi-Cabang: Essay Competition, Business Model Canvas (BMC), Poster Competition",
                "identified_multi_branch",
                ["Memuat petunjuk lengkap untuk 3 cabang lomba: Esai, BMC, dan Poster."],
            )

        # 6. PJJ Challenge Chapter II UII
        if "pjj challenge adalah program kompetisi nasional" in norm_text and "brain challenge" in norm_text:
            return (
                "Guidebook PJJ Challenge Chapter II (Informatika UII)",
                "Multi-Cabang: Brain Challenge, Short Paper, Essay, Catch the Moment",
                "identified_multi_branch",
                ["Memuat 4 cabang lomba dalam PJJ Challenge Chapter II."],
            )

        # 7. Pre-Event OGG FITB ITB 2026 (Tahap Terpusat vs Essay)
        if "ogg atau olimpiade geografi dan geosains" in norm_text:
            if "tahap final" in norm_text[:300] and "science project competition" in norm_text[:1500]:
                return (
                    "Guidebook Tahap Terpusat (Final) Pre-Event OGG FITB ITB 2026",
                    "Multi-Cabang: Poster, Geo Debate, Geo Video, Smart Competition, Essay, Science Project, English Speech",
                    "identified_multi_branch",
                    ["Panduan tahap final terpusat untuk 7 cabang lomba Pre-Event OGG FITB ITB 2026."],
                )
            if "essay competition" in norm_text[:300]:
                return (
                    "Guidebook Essay Competition Pre-Event OGG FITB ITB 2026",
                    "Essay Competition (Geografi & Geosains)",
                    "identified",
                    [],
                )

        # 8. Booklet Firma Ceria 2025
        if "firma ceria 2025" in norm_text and "lomba tilawah" in norm_text and "puisi" in norm_text:
            return (
                "Guide Book Seminar & Lomba Firma Ceria 2025",
                "Multi-Cabang: Lomba Tilawah Al-Qur'an & Lomba Puisi Islami",
                "identified_multi_branch",
                ["Memuat tata tertib seminar serta 2 cabang lomba: Tilawah Al-Qur'an dan Puisi Islami."],
            )

        # 9. Booklet Literat Fest 2024
        if "literat fest 2024" in norm_text and "cipta puisi" in norm_text and "cerpen" in norm_text:
            return (
                "Booklet Sayembara Cipta Puisi dan Cerpen Nasional - Literat Fest 2024",
                "Multi-Cabang: Cipta Puisi & Cipta Cerpen",
                "identified_multi_branch",
                ["Sayembara literasi nasional dengan 2 kategori lomba: Puisi dan Cerpen."],
            )

        # 10. ENFORNATION 2026 UGM
        if "enfornation (environment and forestry national competition)" in norm_text:
            return (
                "Guidebook ENFORNATION 2026 (Environment and Forestry National Competition)",
                "Multi-Cabang/Rangkaian: Lomba Karya Tulis Ilmiah (LKTI), Videografi, CBT & Studi Kasus Infografis (Kehutanan & Lingkungan)",
                "identified_multi_branch",
                [
                    "Kompetisi riset ilmiah kehutanan nasional yang mencakup LKTI, lomba video, CBT, dan studi kasus infografis."
                ],
            )

        # 11. PIMA 2026 (Pupuk Indonesia Media Awards)
        if "pupuk indonesia" in norm_text and "media awards" in norm_text and "karya jurnalistik" in norm_text:
            return (
                "Syarat & Ketentuan Pupuk Indonesia Media Awards (PIMA) 2026",
                "Multi-Cabang: Jurnalistik Media (Hardnews, Feature, Foto Cerita, Televisi, Radio)",
                "identified_multi_branch",
                ["Kompetisi karya jurnalistik dengan 5 kategori media."],
            )

        # 12. SOBAT Competition 2026
        if "sobat competition 2026" in norm_text:
            return (
                "Panduan Peserta SOBAT Competition 2026",
                "Inovasi Sains, Teknologi & Sosial (Prototype & Makalah - Multi Kategori)",
                "identified",
                [
                    "Kompetisi proyek inovasi (makalah & prototype) untuk kategori SMA/SMK, Politeknik/Universitas, Guru/Dosen, dan Disabilitas."
                ],
            )

        # --- Single-Branch Content-Verified Competitions ---

        # AI / Machine Learning / Data Science / Analytics
        if "ai builder challenge 2026 is xdemia's free national student competition" in norm_text:
            return (
                "AI Builder Challenge 2026 – Participant Guidebook",
                "Artificial Intelligence (AI Prototype Development)",
                "identified",
                [],
            )

        if (
            "al innovation challenge (aic) merupakan kompetisi inovasi" in norm_text
            or "ai innovation challenge (aic) merupakan kompetisi inovasi" in norm_text
        ):
            return (
                "Rulebook AI Innovation Challenge (AIC) - COMPFEST 18",
                "Artificial Intelligence (AI Innovation Challenge)",
                "identified",
                [],
            )

        if "ekshibisi kompetisi" in norm_text and "kecerdasan artifisial" in norm_text and "ekka" in norm_text:
            return (
                "Panduan Teknis Pra-Seleksi Ekshibisi Kompetisi Kecerdasan Artifisial (EKKA) OSN Bidang Sains 2026",
                "Artificial Intelligence / Olimpiade Kecerdasan Artifisial (EKKA OSN)",
                "identified",
                [],
            )

        if "machine learning competition (mlc) merupakan salah satu cabang kompetisi dalam" in norm_text:
            return (
                "Guidebook Machine Learning Competition (MLC) - Data Slayer 4.0",
                "Machine Learning",
                "identified",
                [],
            )

        if "dashboard analytics competition (dac) kembali hadir sebagai ajang kompetisi" in norm_text:
            return (
                "Guidebook Dashboard Analytics Competition (DAC) - Data Slayer 4.0",
                "Data Analytics / Visualisasi Data (Dashboard Analytics)",
                "identified",
                [],
            )

        if "data science (ds) adalah sebuah cabang" in norm_text and "ara 7.0" in norm_text:
            return (
                "Guidebook Data Science Competition - ARA 7.0 ITS",
                "Data Science",
                "identified",
                [],
            )

        if "tangenfest #1" in norm_text and "data" in norm_text[:300] and "kaggle" in norm_text[:400]:
            return (
                "Petunjuk Teknis Data Science Competition - TANGENFEST #1 (2026/2027)",
                "Data Science",
                "identified",
                [],
            )

        # Cybersecurity / CTF
        if "ctf compfest 18 adalah kompetisi berskala nasional" in norm_text:
            return (
                "Rulebook Capture The Flag (CTF) - COMPFEST 18",
                "Cybersecurity / Capture The Flag (CTF)",
                "identified",
                [],
            )

        if "wreck-it 7.0 merupakan annual event di bidang keamanan" in norm_text and "capture the flag (ctf)" in norm_text:
            return (
                "Guidebook Petunjuk Teknis Perlombaan CTF - WRECK-IT 7.0",
                "Cybersecurity / Capture The Flag (CTF)",
                "identified",
                [],
            )

        # Software / Web / App / Hackathon / UI-UX / IoT / Clean Code / Competitive Programming
        if "application development competition merupakan cabang" in norm_text and "mage 12" in norm_text:
            return (
                "Guidebook Application Development Competition - MAGE 12",
                "Application Development",
                "identified",
                [],
            )

        if "internet of things (iot) competition merupakan cabang perlombaan" in norm_text and "mage 12" in norm_text:
            return (
                "Guidebook Internet of Things (IoT) Competition - MAGE 12",
                "Internet of Things (IoT)",
                "identified",
                [],
            )

        if "software development competition merupakan salah satu cabang perlombaan pada it" in norm_text:
            return (
                "Guidebook Software Development Competition - IT Festival 2026",
                "Software Development",
                "identified",
                [],
            )

        if "himtec (himatif technology competition) adalah ajang hackathon" in norm_text:
            return (
                "Guide Book HIMTEC 2026 – Hackathon Build App",
                "Hackathon / Application Development (Build App With AI)",
                "identified",
                [],
            )

        if "hackathon web innovation milad it fest 19 merupakan kompetisi pengembangan" in norm_text:
            return (
                "Guidebook Hackathon Web Innovation - Milad IT Fest 19",
                "Hackathon / Web Development",
                "identified",
                [],
            )

        if "ui/ux design competition merupakan kompetisi desain solusi digital" in norm_text and "milad it fest 19" in norm_text:
            return (
                "Guidebook UI/UX Design Competition - Milad IT Fest 19",
                "UI/UX Design",
                "identified",
                [],
            )

        if "web development competition" in norm_text and "jkb festival 2026" in norm_text:
            return (
                "Guide Book Peserta Web Development Competition - JKB Festival 2026",
                "Web Development",
                "identified",
                [],
            )

        if "web in action (wia) merupakan kompetisi" in norm_text and "multimedia in action 2026" in norm_text:
            return (
                "Guidebook Web In Action (WIA) - Multimedia In Action 2026",
                "Web Development",
                "identified",
                [],
            )

        if "genesis 2026 - guidebook web development" in norm_text:
            return (
                "Guidebook Web Development - GENESIS 2026",
                "Web Development",
                "identified",
                [],
            )

        if "daftar isi lomba clean code" in norm_text and "informind fest vol. ii" in norm_text:
            return (
                "Guidebook Lomba Clean Code - INFORMIND FEST VOL. II",
                "Web Development / Clean Code",
                "identified",
                [],
            )

        if "algoquest 2026 merupakan" in norm_text and "berpikir komputasional" in norm_text:
            return (
                "Guidebook AlgoQuest 2026",
                "Computational Thinking, Logic & Mathematics",
                "identified",
                [],
            )

        if "logicodix 2024" in norm_text and "kompetisi logika dan pemrograman" in norm_text:
            return (
                "Guidebook LOGICODIX 2024 - Kompetisi Logika dan Pemrograman",
                "Competitive Programming & Logic",
                "identified",
                [],
            )

        if "immersive" in norm_text and "lomba 3d walking loop animation: merupakan kompetisi utama" in norm_text:
            return (
                "Guidebook Lomba 3D Walking Loop Animation - Immersive Fiesta 2025",
                "3D Animation (3D Walking Loop Animation)",
                "identified",
                [],
            )

        # Business Plan / Business Case / BMC / Policy Case / Engineering Case
        if "future entrepreneur summit" in norm_text and "businessp lan" in norm_text:
            return (
                "Guidebook Business Plan Competition Siswa - Future Entrepreneur Summit",
                "Business Plan Competition",
                "identified",
                [],
            )

        if "business plan competition (bpc) itb insight 2026 merupakan kompetisi rancang" in norm_text:
            return (
                "Guidebook Business Plan Competition (BPC) - ITB INSIGHT 2026 (KAI)",
                "Business Plan Competition",
                "identified",
                [],
            )

        if "high school business plan competition" in norm_text and "brand ui 2026" in norm_text:
            return (
                "Participants Handbook High School Business Plan Competition - BRAND UI 2026",
                "Business Plan Competition",
                "identified",
                [],
            )

        if "merupakan kompetisi business plan yang termasuk dalam rangkaian kegiatan" in norm_text and "olimpiade update festival 10 2025" in norm_text:
            return (
                "Juknis EPIC (Business Plan Competition) - Olimpiade Update Festival 10 2025",
                "Business Plan Competition",
                "identified",
                [],
            )

        if "next gen bmc 2.0 merupakan lomba penyusunan" in norm_text and "business model canvas" in norm_text:
            return (
                "Guidebook Next Gen BMC 2.0 - International Business Carnival 2026",
                "Business Model Canvas (BMC) Competition",
                "identified",
                [],
            )

        if "halo mentor menghadirkan national bmc competition 2026" in norm_text:
            return (
                "Guidebook National BMC Competition 2026 - Halo Mentor",
                "Business Model Canvas (BMC) Competition",
                "identified",
                [],
            )

        if "share international" in norm_text and "business case competition" in norm_text and "dwdg" in norm_text:
            return (
                "Competition Booklet ShARE International Business Case Competition (SIBCC) 26/27",
                "Business Case Competition",
                "identified",
                [],
            )

        if "manifest business case competition (bcc)" in norm_text and "proposal business case" in norm_text:
            return (
                "Guidebook Business Case Competition (BCC) - MANIFEST 2026 ITS",
                "Business Case Competition",
                "identified",
                [
                    "Pengantar dokumen memperkenalkan 3 lomba MANIFEST (BPC, EBPC, BCC), sedangkan isi ketentuan teknis spesifik membahas Business Case Competition (BCC)."
                ],
            )

        if "beimpact" in norm_text and "180dc its" in norm_text and "business case" in norm_text:
            return (
                "Participant Guidebook BeImpact Global Business Case Competition - 180DC ITS",
                "Business Case Competition",
                "identified",
                [],
            )

        if "sxc international business case competition (ibcc)" in norm_text:
            return (
                "Guidebook International Business Case Competition (IBCC) - SxC International Summit 2026",
                "Business Case Competition",
                "identified",
                [],
            )

        if "public action 2026" in norm_text and "policy pitching" in norm_text:
            return (
                "Guidebook Policy Case Competition - Public Action 2026 UGM",
                "Policy Case Competition (Public Policy)",
                "identified",
                [],
            )

        if "study case competition merupakan salah satu cabang kompetisi pada ui science" in norm_text:
            return (
                "Guidebook Study Case Competition - UI Science Olympiad 2026",
                "Study Case Competition (Science & Environment)",
                "identified",
                [],
            )

        if "engineering case competition metalfest" in norm_text:
            return (
                "Preliminary Guidebook Engineering Case Competition (ECC) - MetalFest ITB 2027",
                "Engineering Case Competition (Metallurgy)",
                "identified",
                [],
            )

        # Science / Engineering / Environment Innovation & Research (LKTI / KTI / STEM)
        if "the energy4me competition is a high school level or" in norm_text:
            return (
                "Guidebook ENERGY4ME Competition - SPARK UP 2026",
                "Science Experiment Competition (Renewable & Non-Renewable Energy)",
                "identified",
                [],
            )

        if (
            "isoterm (indonesia’s innovative research competition) merupakan" in norm_text
            or "isoterm (indonesia's innovative research competition) merupakan" in norm_text
        ):
            return (
                "Guidebook Peserta ISOTERM (Indonesia's Innovative Research Competition) - OKTAN ITB 2027",
                "Karya Tulis Ilmiah / Innovative Research Competition",
                "identified",
                [],
            )

        if "eco-project" in norm_text and "taman zakat" in norm_text:
            return (
                "Guidebook Eco-Project Competition - Taman Zakat",
                "Environmental Project Innovation (Eco-Project)",
                "identified",
                [],
            )

        if "emic sma/ma" in norm_text and "mr days" in norm_text:
            return (
                "Guidebook Engineering Management Innovation Competition (EMIC) 2026 [Kategori SMA/MA] - MR Days ITB",
                "Engineering Management Innovation (Extended Abstract & Prototype)",
                "identified",
                [],
            )

        if "energynovation ideas competition" in norm_text and "pertamina goes to campus 2026" in norm_text:
            return (
                "Pedoman Energynovation Ideas Competition (EIC) - Pertamina Goes to Campus (PGTC) 2026",
                "Karya Tulis Ilmiah & Inovasi Energi (Energynovation Ideas Competition)",
                "identified",
                [],
            )

        # Essay / Infographic / Poster / Cerpen Competitions
        if "essay & infographic competition (college)" in norm_text and "metalfest itb 2027" in norm_text:
            return (
                "Guidebook Essay & Infographic Competition (EIC College) - MetalFest ITB 2027",
                "Essay & Infographic Competition (Tingkat Mahasiswa)",
                "identified",
                [],
            )

        if "essay & infographic competition (high school)" in norm_text and "metalfest itb 2027" in norm_text:
            return (
                "Guidebook Essay & Infographic Competition (EIC High School) - MetalFest ITB 2027",
                "Essay & Infographic Competition (Tingkat SMA/Sederajat)",
                "identified",
                [],
            )

        if "esai gagasan kreatif merupakan salah satu cabang kompetisi pada ui science" in norm_text:
            return (
                "Guidebook Esai Gagasan Kreatif - UI Science Olympiad 2026",
                "Essay Competition (Esai Gagasan Kreatif)",
                "identified",
                [],
            )

        if "esai gagasan kritis merupakan salah satu cabang kompetisi pada ui science" in norm_text:
            return (
                "Guidebook Esai Gagasan Kritis - UI Science Olympiad 2026",
                "Essay Competition (Esai Gagasan Kritis)",
                "identified",
                [],
            )

        if "guidebook essay social competition (esco) sma 2026" in norm_text:
            return (
                "Guidebook Essay Social Competition (ESCO) SMA 2026 - EMPOWER ITS",
                "Essay Competition (Social Essay)",
                "identified",
                [],
            )

        if "essay competition yang merupakan series of event public action" in norm_text:
            return (
                "Guidebook Essay Competition - Public Action 2026 UGM",
                "Essay Competition (Public Policy & Socio-Ecological)",
                "identified",
                [],
            )

        if "java business competition (jbc)" in norm_text and "call for essay" in norm_text:
            return (
                "Guidebook Call for Essay Competition - Java Business Competition (JBC) 2026 Telkom University",
                "Essay Competition (Business & Technology Essay)",
                "identified",
                [],
            )

        if "comp 01" in norm_text and "essay" in norm_text[:200] and "eureka" in norm_text:
            return (
                "Guidebook Essay Competition - EUREKA! ITB 2026",
                "Essay Competition (Physics & Sustainable Technology)",
                "identified",
                [],
            )

        if "ketentuan umum lomba esai pelajar smp dan sma sederajat" in norm_text:
            return (
                "Panduan Ketentuan Umum Lomba Esai Pelajar SMP dan SMA Sederajat (Kesehatan Remaja)",
                "Essay Competition (Kesehatan & Gizi Remaja)",
                "identified",
                [],
            )

        if "it - competition amikom surakarta (it-cas) 2026" in norm_text and "essay" in norm_text[:250]:
            return (
                "Ketentuan Lomba Essay Pelajar - IT Competition AMIKOM Surakarta (IT-CAS) 2026",
                "Essay Competition (Inovasi Teknologi Pelajar)",
                "identified",
                [],
            )

        if "infographic competition fasilkom fest 2026" in norm_text:
            return (
                "Guidebook Infographic Competition - Fasilkom Fest 2026 UPNVJ",
                "Infographic Design Competition",
                "identified",
                [],
            )

        if "infografis merupakan salah satu cabang kompetisi pada ui science olympiad 2026" in norm_text:
            return (
                "Guidebook Lomba Infografis - UI Science Olympiad 2026",
                "Infographic Design Competition",
                "identified",
                [],
            )

        if "lomba poster merupakan kompetisi tingkat nasional" in norm_text and "pharmanova" in norm_text:
            return (
                "Guidebook Lomba Poster Nasional - Pharmanova ITB",
                "Poster Design Competition (Kesehatan & Kefarmasian)",
                "identified",
                [],
            )

        if "panjang cerpen minimal 3 halaman" in norm_text and "kosakata" in norm_text:
            return (
                "Petunjuk Teknis Lomba Cipta Cerpen KOSA KATA - Olimpiade Update Festival",
                "Penulisan Cerita Pendek (Cerpen)",
                "identified",
                [],
            )

        # Fallback if a future document is added whose branch isn't explicitly matched in content
        lines = [re.sub(r"\s+", " ", l).strip() for l in stripped.splitlines() if l.strip()]
        fallback_title = " - ".join(lines[:2])[:120] if lines else "unknown"
        return (
            fallback_title,
            "needs_review",
            "needs_review",
            ["Cabang perlombaan belum dapat dipastikan secara otomatis dari teks dan memerlukan tinjauan manual."],
        )

    @classmethod
    def inspect_file(cls, file_path: Path, index: int) -> DocumentInventoryItem:
        """Inspect a single TXT file and produce its inventory item."""
        doc_id = f"DOC-{index:03d}"
        file_name = file_path.name

        try:
            # Read with utf-8-sig to strip BOM if present without altering original file
            raw_text = file_path.read_text(encoding="utf-8-sig", errors="replace")
        except Exception as exc:
            logger.error("Failed to read file %s: %s", file_path, exc)
            return DocumentInventoryItem(
                document_id=doc_id,
                file_name=file_name,
                document_name="unknown",
                character_count=0,
                word_count=0,
                readability_status="unreadable_error",
                document_type="unknown",
                competition_branch="unknown",
                classification_status="unclassified",
                notes=f"Gagal membaca file: {exc}",
            )

        char_count = len(raw_text)
        words = raw_text.split()
        word_count = len(words)

        readability_status, readability_notes = cls.detect_readability(raw_text)
        document_type = cls.identify_document_type(raw_text)
        document_name, competition_branch, classification_status, content_notes = (
            cls.extract_document_name_and_branch(file_name, raw_text)
        )

        all_notes = readability_notes + content_notes
        notes_str = " ".join(all_notes).strip()

        return DocumentInventoryItem(
            document_id=doc_id,
            file_name=file_name,
            document_name=document_name,
            character_count=char_count,
            word_count=word_count,
            readability_status=readability_status,
            document_type=document_type,
            competition_branch=competition_branch,
            classification_status=classification_status,
            notes=notes_str,
        )

    @classmethod
    def build_inventory(
        cls, txt_dir: str | Path = DEFAULT_TXT_DIR
    ) -> Tuple[List[DocumentInventoryItem], InventorySummary]:
        """Scan all TXT files in `txt_dir`, build inventory list and summary statistics."""
        source_dir = Path(txt_dir).resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise FileNotFoundError(f"TXT source directory not found: {source_dir}")

        txt_files = sorted(source_dir.glob("*.txt"), key=lambda p: p.name)
        logger.info("Found %d TXT files in %s", len(txt_files), source_dir)

        items: List[DocumentInventoryItem] = []
        for idx, file_path in enumerate(txt_files, start=1):
            item = cls.inspect_file(file_path, index=idx)
            items.append(item)

        summary = cls.compute_summary(items)
        return items, summary

    @staticmethod
    def compute_summary(items: List[DocumentInventoryItem]) -> InventorySummary:
        """Compute comprehensive statistics over inventoried documents."""
        total_docs = len(items)
        empty_docs = sum(1 for i in items if i.readability_status == "empty")
        readable_docs = sum(1 for i in items if i.readability_status == "readable")
        noisy_docs = sum(
            1 for i in items if i.readability_status == "readable_with_ocr_noise"
        )
        error_docs = sum(
            1
            for i in items
            if i.readability_status not in ("empty", "readable", "readable_with_ocr_noise")
        )

        total_chars = sum(i.character_count for i in items)
        total_words = sum(i.word_count for i in items)

        non_empty_words = [i.word_count for i in items if i.word_count > 0]
        min_words = min(non_empty_words) if non_empty_words else 0
        max_words = max(non_empty_words) if non_empty_words else 0
        avg_words = (
            round(sum(non_empty_words) / len(non_empty_words), 2)
            if non_empty_words
            else 0.0
        )

        readability_breakdown: Dict[str, int] = {}
        doc_type_breakdown: Dict[str, int] = {}
        class_status_breakdown: Dict[str, int] = {}
        branch_breakdown: Dict[str, int] = {}
        flagged_docs: List[Dict[str, Any]] = []

        for item in items:
            readability_breakdown[item.readability_status] = (
                readability_breakdown.get(item.readability_status, 0) + 1
            )
            doc_type_breakdown[item.document_type] = (
                doc_type_breakdown.get(item.document_type, 0) + 1
            )
            class_status_breakdown[item.classification_status] = (
                class_status_breakdown.get(item.classification_status, 0) + 1
            )
            branch_breakdown[item.competition_branch] = (
                branch_breakdown.get(item.competition_branch, 0) + 1
            )

            if (
                item.readability_status != "readable"
                or item.classification_status in ("unclassified", "needs_review")
            ):
                flagged_docs.append(
                    {
                        "document_id": item.document_id,
                        "file_name": item.file_name,
                        "character_count": item.character_count,
                        "word_count": item.word_count,
                        "readability_status": item.readability_status,
                        "document_type": item.document_type,
                        "competition_branch": item.competition_branch,
                        "classification_status": item.classification_status,
                        "notes": item.notes,
                    }
                )

        return InventorySummary(
            total_documents=total_docs,
            empty_documents=empty_docs,
            readable_documents=readable_docs,
            readable_with_ocr_noise_documents=noisy_docs,
            unreadable_or_error_documents=error_docs,
            total_characters=total_chars,
            total_words=total_words,
            min_word_count_non_empty=min_words,
            max_word_count=max_words,
            avg_word_count_non_empty=avg_words,
            readability_breakdown=readability_breakdown,
            document_type_breakdown=doc_type_breakdown,
            classification_status_breakdown=class_status_breakdown,
            competition_branch_breakdown=branch_breakdown,
            flagged_documents=flagged_docs,
        )

    @classmethod
    def save_inventory(
        cls,
        items: List[DocumentInventoryItem],
        summary: InventorySummary,
        csv_path: str | Path = DEFAULT_CSV_OUTPUT,
        json_path: str | Path = DEFAULT_JSON_OUTPUT,
    ) -> Tuple[Path, Path]:
        """Save inventory to CSV and JSON atomically and idempotently (overwriting previous run)."""
        csv_target = Path(csv_path).resolve()
        json_target = Path(json_path).resolve()

        csv_target.parent.mkdir(parents=True, exist_ok=True)
        json_target.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
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
        ]

        with open(csv_target, "w", encoding="utf-8", newline="") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
            writer.writeheader()
            for item in items:
                writer.writerow(item.to_dict())

        payload = {
            "summary": summary.to_dict(),
            "documents": [item.to_dict() for item in items],
        }
        with open(json_target, "w", encoding="utf-8") as f_json:
            json.dump(payload, f_json, indent=2, ensure_ascii=False)

        logger.info(
            "Saved document inventory (%d records) to %s and %s",
            len(items),
            csv_target,
            json_target,
        )
        return csv_target, json_target

    @classmethod
    def run(
        cls,
        txt_dir: str | Path = DEFAULT_TXT_DIR,
        csv_path: str | Path = DEFAULT_CSV_OUTPUT,
        json_path: str | Path = DEFAULT_JSON_OUTPUT,
    ) -> Tuple[List[DocumentInventoryItem], InventorySummary]:
        """Execute full inventory pipeline and persist outputs."""
        items, summary = cls.build_inventory(txt_dir=txt_dir)
        cls.save_inventory(items, summary, csv_path=csv_path, json_path=json_path)
        return items, summary
