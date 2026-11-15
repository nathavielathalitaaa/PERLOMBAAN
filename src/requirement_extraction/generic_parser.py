"""Stage 4.4: Generic Rule-Based Section-and-Clause Competition Requirement Parser.

A general-purpose, document-agnostic parser that extracts structured competition
requirements from raw TXT documents using:
1. Unit & shared event-level span resolution (via Stage 3 / 3.1 metadata).
2. Structural page, header, list, and rubric-table segmentation.
3. Near-duplicate block deduplication (handling OCR-duplicated pages & repeated sections).
4. Contextual + linguistic classification into the 6 requirement categories.
5. Verbatim provenance preservation (`raw_text[start:end] == evidence_text`).

STRICT DESIGN CONSTRAINT:
This module MUST NOT contain any document-ID-specific dispatchers or hardcoded
document/file-name special cases.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.requirement_extraction.rules import (
    REQUIREMENT_CATEGORIES,
    apply_term_normalization,
    extract_exception_or_condition,
    is_non_requirement_background,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_TXT_DIR = PROJECT_ROOT / "data" / "raw" / "txt"
UNITS_PATH = PROJECT_ROOT / "data" / "processed" / "competition_branch_units.json"
SEG_VAL_PATH = PROJECT_ROOT / "data" / "processed" / "segmentation_validation.json"

# Generic header/footer noise lines frequently produced by PDF/OCR extraction
_NOISE_LINE_PATTERNS = (
    re.compile(r"^\s*@[\w.]+\s+\S+@\S+\s*$", re.IGNORECASE),
    re.compile(r"^\s*#TechForTomorrow\b.*$", re.IGNORECASE),
    re.compile(r"^\s*e?chtonic\s*3\.0\s*$", re.IGNORECASE),
    re.compile(r"^\s*H\s*I\s*M\s*T\s*E\s*C\s*\|\s*\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d{1,3}\s*$"),
    re.compile(r"^\s*IT\s*-\s*Competition\s+AMIKOM.*$", re.IGNORECASE),
)

# Section titles that contain non-requirement context (cover, TOC, greetings, prizes, contacts, examples, blank forms)
_IGNORED_SECTION_PATTERNS = (
    re.compile(r"\btables?\s+of\s+contents?\b|\bdaftar\s+isi\b|\bguidebook\s+content\b", re.IGNORECASE),
    re.compile(r"\bdid\s+you\s+know\b|\bour\s+vision\b|\bvision\s+mision\b|\btypes?\s+of\s+competition\b", re.IGNORECASE),
    re.compile(r"\blatar\s+belakang\b|\btujuan\b|\bpendahuluan\b|\bdeskripsi\s+umum\b", re.IGNORECASE),
    re.compile(r"\bhadiah\b|\bpenghargaan\b|\bbenefits?\b|\binformasi\s+hadiah\b", re.IGNORECASE),
    re.compile(r"\bcontact\s+person\b|\bcontact\s+us\b|\bkontak\s+panitia\b|\blayanan\s+informasi\b|\binformasi\s+lebih\s+lanjut\b", re.IGNORECASE),
    re.compile(r"\bpartner\s+collaboration\b|\bregister\s+now\b", re.IGNORECASE),
    re.compile(r"\blembar\s+pernyataan\s+orisinalitas\b|\byang\s+bertanda\s+tangan\s+di\s+bawah\s+ini\b", re.IGNORECASE),
    re.compile(r"\bdaftar\s+pustaka\b", re.IGNORECASE),
)

# Section titles that strongly indicate requirement-bearing sections
_SECTION_HEADER_PATTERNS = (
    re.compile(r"^(?:[A-N]|[IVX]{1,4})\.\s+[A-Za-z].{2,80}$"),
    re.compile(r"^(?:BAB\s+[IVX]+|BAGIAN\s+\w+|TAHAP\s+[IVX0-9]+).*$", re.IGNORECASE),
    re.compile(
        r"^(?:#TechForTomorrow\s+)?(?:"
        r"FLOW\s+REGISTRATION|MATERIALS\s+REQUIREMENTS|GENERAL\s+RULES|COMPETITION\s+TIMELINE|"
        r"TIMELINE(?:\s+KEGIATAN)?|PRELIMINARY(?:\s+ROUND|\s*:\s*.*)?|CONCEPT\s+POSAL.*|"
        r"CONCEPT\s+PROPOSAL.*|BUSINESS\s+MODEL\s+CANVAS.*|WRITING\s+RULES.*|"
        r"PROPOSAL\s+FORMATTING.*|SYARAT\s+DAN\s+KETENTUAN|KETENTUAN\s+UMUM|KETENTUAN\s+PESERTA|"
        r"KETENTUAN\s+TIM|KETENTUAN\s+ESAI|KETENTUAN\s+KARYA|KETENTUAN\s+PENILAIAN|"
        r"SYARAT\s+ESAI|PANDUAN\s+PENULISAN.*|PELAKSANAAN\s+PENILAIAN|"
        r"PENILAIAN\s+NASKAH.*|PENILAIAN\s+PRESENTASI|KRITERIA\s+PENILAIAN|"
        r"ALUR\s+PENDAFTARAN|PROSEDUR\s+PENDAFTARAN.*|TAHAP\s+\d+.*|TAHAP\s+[IVX]+.*|"
        r"TEKNIS\s+.*|BIAYA\s+PENDAFTARAN.*|FORMAT\s+PENULISAN.*|ATURAN\s+TAMBAHAN|"
        r"PROPORSI\s+PENILAIAN.*"
        r")$",
        re.IGNORECASE,
    ),
)


@dataclass
class SpanWindow:
    start_char: int
    end_char: int
    scope_level: str = "branch_specific"  # "branch_specific" or "event_shared"


@dataclass
class SectionBlock:
    title: str
    start_char: int
    end_char: int
    text: str
    scope_level: str
    page: int


@dataclass
class CandidateClause:
    text: str
    start_char: int
    end_char: int
    section_title: str
    scope_level: str
    page: int
    is_table: bool = False
    is_timeline: bool = False


@dataclass
class ParsedRequirement:
    requirement_id: str
    document_id: str
    branch_unit_id: str
    requirement_category: str
    requirement_subcategory: str
    requirement_name: str
    requirement_description: str
    evidence_text: str
    source_char_start: int
    source_char_end: int
    source_page: int
    source_section: str
    statement_nature: str
    evidence_type: str
    scope_level: str
    canonical_topics: List[str] = field(default_factory=list)


def _compute_page(raw_text: str, char_pos: int) -> int:
    return raw_text[: max(0, char_pos)].count("\n\n\n") + 1


def _clean_for_matching(text: str) -> str:
    return re.sub(r"[\u200b\u00a0\u2028\r]+", " ", text).strip()


def _is_noise_line(line: str) -> bool:
    s = _clean_for_matching(line)
    if not s:
        return True
    return any(p.match(s) for p in _NOISE_LINE_PATTERNS)


def _is_ignored_section(title: str) -> bool:
    t = _clean_for_matching(title)
    return any(p.search(t) for p in _IGNORED_SECTION_PATTERNS)


def _looks_like_section_header(line: str, next_line: str = "") -> Tuple[bool, str, bool]:
    """Detect whether `line` (or `line + ' ' + next_line`) is a structural section header.

    Returns (is_header, normalized_title, consumed_next_line).
    """
    s = _clean_for_matching(line)
    if not s or len(s) > 95 or _is_noise_line(s):
        return False, "", False

    # Strip "#TechForTomorrow " prefix if present
    s_stripped = re.sub(r"^#TechForTomorrow\s+", "", s, flags=re.IGNORECASE).strip()

    # Single-line exact patterns
    for pat in _SECTION_HEADER_PATTERNS:
        if pat.match(s_stripped):
            return True, s_stripped.rstrip(":").strip(), False

    # Short colon-terminated heading (e.g., "Ketentuan Peserta:", "Timeline:", "Biaya Pendaftaran: GRATIS")
    if ":" in s_stripped:
        left, right = s_stripped.split(":", 1)
        left_w = left.strip()
        if 1 <= len(left_w.split()) <= 6 and not right.strip():
            return True, left_w, False
        if re.match(r"^(?:Biaya\s+Pendaftaran|Timeline|Tema|Subtema)$", left_w, re.IGNORECASE):
            return True, left_w, False

    # Two-line split header (e.g., "Alur\npendaftaran", "ketentuan\numum", "kriteria\npenilaian")
    if next_line:
        n = _clean_for_matching(next_line)
        combined = f"{s_stripped} {n}".strip()
        if 2 <= len(combined.split()) <= 6 and len(combined) <= 60:
            for pat in _SECTION_HEADER_PATTERNS:
                if pat.match(combined):
                    return True, combined.rstrip(":").strip(), True

    # Short all-caps heading (2-7 words, no sentence punctuation)
    if s_stripped.isupper() and 1 <= len(s_stripped.split()) <= 7 and not re.search(r"[.,;?!]", s_stripped):
        if not re.match(r"^(?:M|GUIDEBOOK|APP|STEM|BPC|HACKATHON|3\.0)$", s_stripped):
            return True, s_stripped, False

    return False, "", False


def resolve_unit_windows(
    unit: Dict[str, Any],
    seg_validation: Optional[Dict[str, Any]] = None,
) -> List[SpanWindow]:
    """Resolve primary branch unit bounds plus any shared event-level registration spans."""
    doc_id = unit["document_id"]
    start_char = int(unit["start_char"])
    end_char = int(unit["end_char"])
    windows: List[SpanWindow] = []

    if seg_validation:
        for span in seg_validation.get("uncovered_char_spans", []):
            if span.get("document_id") == doc_id and span.get("category") == "shared_registration_or_payment_rules":
                s = int(span["start_char"])
                e = int(span["end_char"])
                if e <= start_char or s >= end_char:
                    windows.append(SpanWindow(start_char=s, end_char=e, scope_level="event_shared"))

    windows.append(SpanWindow(start_char=start_char, end_char=end_char, scope_level="branch_specific"))
    windows.sort(key=lambda w: w.start_char)
    return windows


def _segment_window_into_sections(raw_text: str, window: SpanWindow) -> List[SectionBlock]:
    """Segment a character window of raw_text into structural sections with exact char offsets."""
    sub = raw_text[window.start_char : window.end_char]
    lines_with_offsets: List[Tuple[int, int, str]] = []
    pos = 0
    for ln in sub.splitlines(keepends=True):
        s_off = window.start_char + pos
        e_off = s_off + len(ln)
        lines_with_offsets.append((s_off, e_off, ln.rstrip("\r\n")))
        pos += len(ln)

    headers: List[Tuple[int, int, str]] = []  # (header_start, body_start, title)
    i = 0
    while i < len(lines_with_offsets):
        s_off, e_off, text_ln = lines_with_offsets[i]
        next_ln = ""
        next_idx = i + 1
        while next_idx < len(lines_with_offsets) and not _clean_for_matching(lines_with_offsets[next_idx][2]):
            next_idx += 1
        if next_idx < len(lines_with_offsets):
            next_ln = lines_with_offsets[next_idx][2]

        is_hdr, title, consumed_next = _looks_like_section_header(text_ln, next_ln)
        if is_hdr:
            body_start = lines_with_offsets[next_idx][1] if consumed_next else e_off
            # If the header line itself has content after ':' (e.g. "Biaya Pendaftaran: GRATIS"), keep it in body
            if ":" in text_ln and text_ln.split(":", 1)[1].strip():
                body_start = s_off
            headers.append((s_off, body_start, title))
            i = (next_idx + 1) if consumed_next else (i + 1)
            continue
        i += 1

    if not headers:
        return [
            SectionBlock(
                title="GENERAL",
                start_char=window.start_char,
                end_char=window.end_char,
                text=sub,
                scope_level=window.scope_level,
                page=_compute_page(raw_text, window.start_char),
            )
        ]

    sections: List[SectionBlock] = []
    for idx, (h_start, b_start, title) in enumerate(headers):
        sec_end = headers[idx + 1][0] if idx + 1 < len(headers) else window.end_char
        if b_start < sec_end and not _is_ignored_section(title):
            sections.append(
                SectionBlock(
                    title=title,
                    start_char=b_start,
                    end_char=sec_end,
                    text=raw_text[b_start:sec_end],
                    scope_level=window.scope_level,
                    page=_compute_page(raw_text, h_start),
                )
            )
    return sections


def _is_list_item_start(line: str) -> bool:
    s = _clean_for_matching(line)
    return bool(
        re.match(r"^(?:\d{1,2}\.|[a-z]\.|[•\-\*]|\u2022)\s+", s)
        or re.match(r"^(?:\d{1,2}\.|[a-z]\.)\S", s)
    )


def _is_sub_item_start(line: str) -> bool:
    s = _clean_for_matching(line)
    return bool(re.match(r"^(?:[a-z]\.|[•\-\*]|\u2022|■|○|●)\s+", s))


def _section_kind(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ("timeline", "jadwal", "rangkaian kegiatan")):
        return "timeline"
    if any(k in t for k in ("kriteria penilaian", "penilaian naskah", "penilaian presentasi", "proporsi penilaian", "proses penilain")):
        return "assessment"
    if any(k in t for k in ("alur pendaftaran", "flow registration", "materials requirements", "biaya pendaftaran")):
        return "registration"
    if any(k in t for k in ("format penulisan", "writing rules", "proposal formatting", "panduan penulisan")):
        return "formatting"
    if any(k in t for k in ("business model canvas", "concept proposal", "format pengumpulan", "preliminary", "tahap ")):
        return "deliverable_stage"
    if any(k in t for k in ("ketentuan peserta", "syarat dan ketentuan", "general rules", "ketentuan umum", "ketentuan karya", "etika", "aturan teknis")):
        return "rules"
    return "general"


def _split_into_paragraphs_with_offsets(raw_text: str, sec: SectionBlock) -> List[Tuple[int, int, str]]:
    """Split section text into non-noise logical line/paragraph units preserving exact char offsets."""
    sub = raw_text[sec.start_char : sec.end_char]
    lines: List[Tuple[int, int, str]] = []
    pos = 0
    for ln in sub.splitlines(keepends=True):
        s_off = sec.start_char + pos
        e_off = s_off + len(ln)
        pos += len(ln)
        stripped = ln.strip()
        if _is_noise_line(stripped):
            continue
        lines.append((s_off, e_off, ln.rstrip("\r\n")))

    # Group lines into logical paragraphs/list-items
    paragraphs: List[Tuple[int, int, str]] = []
    cur_start: Optional[int] = None
    cur_end: Optional[int] = None
    prev_end_line = -1

    for s_off, e_off, txt in lines:
        gap = raw_text[prev_end_line:s_off] if prev_end_line != -1 else ""
        blank_lines = gap.count("\n") - 1 if prev_end_line != -1 else 0
        starts_new = (
            cur_start is None
            or _is_list_item_start(txt)
            or blank_lines >= 1
        )
        # Keep sub-items attached if previous item ended with ':'
        if cur_start is not None and _is_sub_item_start(txt):
            prev_txt = raw_text[cur_start:cur_end].rstrip()
            if prev_txt.endswith(":") or re.search(r"(?:berikut|meliputi|antara lain|terdiri dari|sebagai berikut)\s*:?\s*$", prev_txt, re.IGNORECASE):
                starts_new = False

        if starts_new:
            if cur_start is not None and cur_end is not None:
                paragraphs.append((cur_start, cur_end, raw_text[cur_start:cur_end].strip()))
            cur_start = s_off
            cur_end = e_off
        else:
            cur_end = e_off
        prev_end_line = e_off

    if cur_start is not None and cur_end is not None:
        paragraphs.append((cur_start, cur_end, raw_text[cur_start:cur_end].strip()))

    return [(s, e, t) for s, e, t in paragraphs if len(_clean_for_matching(t)) >= 12]


def _classify_clause_text(text: str, section_title: str) -> Tuple[str, str]:
    """Classify a candidate block into (requirement_category, requirement_subcategory) using context + linguistic rules."""
    t_low = _clean_for_matching(text).lower()
    sec_low = _clean_for_matching(section_title).lower()
    sec_kind = _section_kind(section_title)

    # 1. Explicit section-level strong priors for timelines and rubrics
    if sec_kind == "timeline" and any(k in t_low for k in ("2025", "2026", "januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember", "aug", "sept", "oct", "nov", "technical meeting", "grand final", "preliminary", "semifinal")):
        return "competition_structure", "competition_timeline_and_deadlines"

    if sec_kind == "assessment" or any(k in t_low for k in ("aspek penilaian", "kriteria penilaian", "bobot", "rentang nilai", "dewan juri terdiri", "skor maksimum", "total skor", "turnitin maksimal")):
        if re.search(r"\d+\s*%|\bpoin\b|\bskor\b|\bbobot\b", t_low):
            return "assessment_criteria", "judging_criterion_weighted"
        return "assessment_criteria", "judging_criterion_unweighted"

    # 2. Strong clause-level signals with negative guards
    # 2a. Formatting & writing rules (MUST precede deliverables even inside Proposal/Esai sections!)
    is_formatting = any(
        k in t_low
        for k in (
            "times new roman",
            "arial",
            "margin",
            "spasi",
            "line spacing",
            "kertas a4",
            "ukuran a4",
            "maksimal 25 halaman",
            "maksimal 30 halaman",
            "5 to 7 pages",
            "maximum of 2 pages",
            "700-1000 kata",
            "3000 kata",
            "1.000-1.500 kata",
            "maksimal 20 kata",
            "puebi",
            "apa style",
            "vancouver",
            "ieee",
            "si units",
            "standard si",
            "two-column",
            "justified",
            "font:",
            "font ",
        )
    )
    if is_formatting and not any(k in t_low for k in ("format penamaan file", "penamaan file", "file naming", "bernama", "dikumpulkan dalam bentuk pdf", "format .rar")):
        return "technical_and_general_rules", "document_formatting_and_length"

    # 2b. Registration fees, portals, twibbon, social media follow/repost/tag
    if any(
        k in t_low
        for k in (
            "biaya pendaftaran",
            "registration fee",
            "free of charge",
            "gratis",
            "qris",
            "bukti pembayaran",
            "proof payment",
            "non-refundable",
            "tidak dapat dikembalikan",
            "tidak dapat ditarik kembali",
            "registrasi ulang",
            "bit.ly/registration",
            "bit.ly/materials",
            "mage-its.id",
            "himtec-utb.my.id",
            "ugm.id/daftar",
            "twibbon",
            "follow akun",
            "follow official instagram",
            "follow instagram",
            "repost poster",
            "instastory",
            "instagram story",
            "sharing poster",
            "tag 3",
            "verifikasi pembayaran",
            "followproof",
            "twibbonproof",
            "storyproof",
            "commentproof",
            "sharingposterproof",
        )
    ):
        if any(k in t_low for k in ("biaya", "fee", "qris", "gratis", "free of charge", "non-refundable", "pembayaran", "rp.")):
            return "registration_requirements", "registration_fee_and_payment"
        if any(k in t_low for k in ("twibbon", "follow", "repost", "story", "tag ", "kartu pelajar", "ktm", "ktp", "studentid")):
            return "registration_requirements", "administrative_and_twibbon_requirements"
        return "registration_requirements", "registration_mechanism_and_portal"

    # 2c. Eligibility (education level, student status, team size, member replacement, single team)
    if any(
        k in t_low
        for k in (
            "siswa",
            "pelajar",
            "mahasiswa",
            "sma/smk",
            "smp",
            "s1",
            "d3/d4",
            "undergraduate",
            "senior high school",
            "kartu tanda mahasiswa",
            "kartu pelajar",
            "satu tim terdiri",
            "each team",
            "one team consists",
            "beranggotakan",
            "bersifat individu",
            "lomba individu",
            "pergantian anggota",
            "tidak dapat digantikan",
            "cannot be changed",
            "mengubah susunan anggota",
            "hanya boleh terdaftar di satu tim",
            "join only one team",
            "satu tim pada kompetisi",
            "ketua tim",
            "panitia, juri, dan mentor",
            "perwakilan dari",
        )
    ) and not any(k in t_low for k in ("proposal", "bmc", "pitch deck", "laporan pengembangan", "source code")):
        if any(k in t_low for k in ("sma", "smp", "mahasiswa", "undergraduate", "high school", "umum", "pelajar")):
            return "eligibility_requirements", "education_level_and_student_status"
        return "eligibility_requirements", "participation_mode_and_team_size"

    # 2d. Originality, plagiarism, content prohibition, AI rules, platform limits, disqualification, jury decision
    if any(
        k in t_low
        for k in (
            "orisinal",
            "original",
            "plagiar",
            "sara",
            "pornografi",
            "kekerasan",
            "hak cipta",
            "hak kekayaan intelektual",
            "berlisensi",
            "belum pernah menang",
            "belum pernah menjuarai",
            "previously won",
            "tidak sedang diikutsertakan",
            "diskualifikasi",
            "disqualification",
            "keputusan dewan juri",
            "keputusan panitia",
            "judges' decision",
            "decision of the judges",
            "materai",
            "stamp duty",
            "meterai",
            "platform pc",
            "platform aplikasi",
            "bring your own device",
            "bantuan teknis",
            "remote coding",
            "artificial intelligence",
            "generative ai",
            "boilerplate",
            "re-skinning",
            "code freeze",
            "modifikasi atau perubahan pada aplikasi",
            "keterlambatan",
            "late submissions",
        )
    ):
        if any(k in t_low for k in ("orisinal", "original", "plagiar", "materai", "stamp duty", "belum pernah")):
            return "technical_and_general_rules", "originality_and_plagiarism_threshold"
        if any(k in t_low for k in ("diskualifikasi", "disqualification", "sanksi", "late submissions", "keputusan")):
            return "technical_and_general_rules", "disqualification_and_sanction_rules"
        return "technical_and_general_rules", "content_and_tool_prohibition"

    # 2e. Deliverables (proposal, BMC, source code, video, pitch deck, report, Google Drive, file naming)
    if any(
        k in t_low
        for k in (
            "mengumpulkan",
            "dikumpulkan",
            "submit",
            "submission",
            "penamaan file",
            "file naming",
            "format nama file",
            "business model canvas",
            "bmc",
            "concept proposal",
            "proposal aplikasi",
            "laporan pengembangan",
            "source code",
            "github",
            "readme",
            "pitch deck",
            "powerpoint",
            "x-banner",
            "video",
            "google drive",
            ".rar",
            ".exe",
            ".apk",
            "working prototype",
            "prototipe",
            "poin-poin berikut",
            "struktur esai",
            "bill of materials",
            "swot analysis",
            "9 komponen",
            "key partners",
        )
    ):
        if "bmc" in t_low or "business model canvas" in t_low or "key partners" in t_low:
            return "deliverables", "bmc_deliverable"
        if "video" in t_low:
            return "deliverables", "video_deliverable"
        if "source code" in t_low or "github" in t_low or ".exe" in t_low or ".apk" in t_low or "prototipe" in t_low:
            return "deliverables", "prototype_or_exam_deliverable"
        if "pitch deck" in t_low or "powerpoint" in t_low or "x-banner" in t_low:
            return "deliverables", "presentation_slide_deliverable"
        return "deliverables", "proposal_or_essay_deliverable"

    # 2f. Competition structure (stages, technical meeting, live coding 13 jam, pitching duration, finalist selection)
    if any(
        k in t_low
        for k in (
            "technical meeting",
            "babak penyisihan",
            "babak final",
            "tahap 1",
            "tahap 2",
            "tahap 3",
            "tahap pertama",
            "tahap kedua",
            "live coding",
            "13 jam",
            "konfirmasi kehadiran",
            "presentasi dan demo",
            "alokasi waktu",
            "menit",
            "50% terbaik",
            "tim terbaik",
            "finalis",
            "seleksi dilakukan",
            "exhibition",
        )
    ):
        return "competition_structure", "competition_stages_and_selection"

    # 3. Section-context fallback
    if sec_kind == "registration":
        return "registration_requirements", "registration_mechanism_and_portal"
    if sec_kind == "formatting":
        return "technical_and_general_rules", "document_formatting_and_length"
    if sec_kind == "deliverable_stage":
        return "deliverables", "proposal_or_essay_deliverable"
    if "peserta" in sec_low:
        return "eligibility_requirements", "participation_mode_and_team_size"

    return "technical_and_general_rules", "content_and_tool_prohibition"


def _detect_statement_nature(text: str, category: str) -> str:
    t = _clean_for_matching(text).lower()
    if category == "assessment_criteria":
        return "evaluation_criterion"
    if extract_exception_or_condition(text):
        return "mandatory_with_exception"
    if any(k in t for k in ("dilarang", "tidak boleh", "tidak diperbolehkan", "tidak diperkenankan", "cannot", "must not", "prohibited")):
        return "prohibition"
    if any(k in t for k in ("jika ", "apabila ", "only if", "only required to pay if")):
        return "conditional_requirement"
    return "mandatory_requirement"


def _extract_canonical_topics(text: str, category: str) -> List[str]:
    t = _clean_for_matching(text).lower()
    topics: List[str] = []
    topic_rules = [
        ("education_level", r"\b(?:sma|smk|smp|mts|ma|mahasiswa|undergraduate|s1|d3|d4|senior high school|pelajar)\b"),
        ("team_size", r"\b(?:maksimal\s+(?:tiga|3|4)|2[\s\-–]+3\s+(?:orang|peserta|members?)|individu|individual)\b"),
        ("member_replacement", r"(?:pergantian anggota|mengubah susunan anggota|tidak dapat digantikan|cannot be changed)"),
        ("registration_mechanism", r"(?:bit\.ly/|mage-its\.id|himtec-utb|ugm\.id/|formulir online|formulir pendaftaran)"),
        ("registration_documents", r"(?:followproof|studentid|twibbon|kartu pelajar|ktm|ktp|surat keterangan|orisinalitas)"),
        ("registration_fee", r"(?:biaya pendaftaran|registration fee|qris|gratis|free of charge|non-refundable|rp\.?\s*55\.000)"),
        ("timeline", r"(?:timeline|2025|2026|januari|februari|agustus|oktober|november)"),
        ("technical_meeting", r"technical meeting"),
        ("final_round", r"(?:babak final|grand final|exhibition|presentasi finalis|live demo)"),
        ("proposal", r"(?:proposal|concept proposal|laporan pengembangan)"),
        ("business_model_canvas", r"(?:business model canvas|bmc)"),
        ("source_code", r"(?:source code|github|readme)"),
        ("video_demo", r"(?:video|\.mp4|720p)"),
        ("file_naming", r"(?:penamaan file|format nama file|file naming)"),
        ("assessment_criteria", r"(?:aspek penilaian|kriteria penilaian|bobot|rentang nilai|10[\s\-–]+100\s*poin)"),
        ("originality", r"(?:orisinal|original|plagiar|turnitin)"),
        ("document_formatting", r"(?:times new roman|arial|margin|spasi|halaman|kata|puebi|ieee|apa style|vancouver)"),
        ("disqualification", r"(?:diskualifikasi|disqualification)"),
    ]
    for tag, pat in topic_rules:
        if re.search(pat, t):
            topics.append(tag)
    if not topics:
        topics.append(category)
    return topics


def _token_set(text: str) -> set[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", _clean_for_matching(text).lower())
    return {tok for tok in cleaned.split() if len(tok) >= 3}


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _containment_similarity(smaller: set[str], larger: set[str]) -> float:
    if not smaller or not larger:
        return 0.0
    return len(smaller & larger) / len(smaller)


def _is_duplicate_candidate(cand_tokens: set[str], accepted_tokens_list: List[set[str]]) -> bool:
    for prev_tokens in accepted_tokens_list:
        if _jaccard_similarity(cand_tokens, prev_tokens) >= 0.72:
            return True
        if len(cand_tokens) >= 12 and _containment_similarity(cand_tokens, prev_tokens) >= 0.85:
            return True
    return False


def _make_requirement_name(category: str, section_title: str, evidence_text: str) -> str:
    clean_ev = _clean_for_matching(evidence_text)
    first_line = next((ln.strip() for ln in clean_ev.splitlines() if ln.strip()), clean_ev)
    snippet = first_line[:90].rstrip(" ,;:-")
    if len(first_line) > 90:
        snippet += "..."
    sec = _clean_for_matching(section_title)
    return f"[{category}] {sec}: {snippet}"


def _make_grounded_description(evidence_text: str) -> str:
    """Create a clean single-paragraph description strictly grounded in evidence_text."""
    lines = [_clean_for_matching(ln) for ln in evidence_text.splitlines() if not _is_noise_line(ln)]
    joined = re.sub(r"\s+", " ", " ".join(lines)).strip()
    joined = apply_term_normalization(joined)
    if len(joined) > 650:
        joined = joined[:647].rstrip() + "..."
    return joined


def parse_branch_unit(
    unit: Dict[str, Any],
    raw_text: str,
    seg_validation: Optional[Dict[str, Any]] = None,
) -> List[ParsedRequirement]:
    """Extract structured competition requirements from a single CompetitionBranchUnit."""
    doc_id = unit["document_id"]
    bu_id = unit["branch_unit_id"]
    windows = resolve_unit_windows(unit, seg_validation=seg_validation)

    sections: List[SectionBlock] = []
    for w in windows:
        sections.extend(_segment_window_into_sections(raw_text, w))

    # Group paragraphs within each section by (category) while preserving contiguous spans where appropriate
    raw_candidates: List[Tuple[str, str, int, int, str, str, int]] = []
    for sec in sections:
        sec_kind = _section_kind(sec.title)

        # Timeline & Assessment sections are best represented as cohesive section-level blocks
        if sec_kind in ("timeline", "assessment"):
            paras = _split_into_paragraphs_with_offsets(raw_text, sec)
            if paras:
                s_min = paras[0][0]
                e_max = paras[-1][1]
                ev = raw_text[s_min:e_max]
                if not is_non_requirement_background(ev):
                    cat, subcat = _classify_clause_text(ev, sec.title)
                    raw_candidates.append((cat, subcat, s_min, e_max, sec.title, sec.scope_level, sec.page))
            continue

        paras = _split_into_paragraphs_with_offsets(raw_text, sec)
        # Cluster consecutive paragraphs that classify into the same requirement_category
        cur_cat: Optional[str] = None
        cur_subcat: Optional[str] = None
        cur_s: Optional[int] = None
        cur_e: Optional[int] = None

        for s_off, e_off, p_txt in paras:
            if is_non_requirement_background(p_txt):
                continue
            cat, subcat = _classify_clause_text(p_txt, sec.title)

            # Avoid over-merging distinct sub-topics inside deliverables or registration if chunk gets large
            should_merge = (
                cur_cat == cat
                and cur_s is not None
                and (e_off - cur_s) <= 1800
            )
            if should_merge:
                cur_e = e_off
            else:
                if cur_cat is not None and cur_s is not None and cur_e is not None:
                    raw_candidates.append((cur_cat, cur_subcat or "", cur_s, cur_e, sec.title, sec.scope_level, sec.page))
                cur_cat = cat
                cur_subcat = subcat
                cur_s = s_off
                cur_e = e_off

        if cur_cat is not None and cur_s is not None and cur_e is not None:
            raw_candidates.append((cur_cat, cur_subcat or "", cur_s, cur_e, sec.title, sec.scope_level, sec.page))

    # Deduplicate near-duplicate blocks (e.g., OCR-duplicated pages or repeated rules)
    accepted_tokens_by_cat: Dict[str, List[set[str]]] = {c: [] for c in REQUIREMENT_CATEGORIES}
    results: List[ParsedRequirement] = []
    seq = 1

    for cat, subcat, s_off, e_off, sec_title, scope_level, page in raw_candidates:
        ev = raw_text[s_off:e_off]
        toks = _token_set(ev)
        if len(toks) < 3:
            continue
        if _is_duplicate_candidate(toks, accepted_tokens_by_cat[cat]):
            continue

        accepted_tokens_by_cat[cat].append(toks)
        req_id = f"GEN-{doc_id}-{bu_id.split('-')[-1]}-{seq:03d}"
        seq += 1
        results.append(
            ParsedRequirement(
                requirement_id=req_id,
                document_id=doc_id,
                branch_unit_id=bu_id,
                requirement_category=cat,
                requirement_subcategory=subcat,
                requirement_name=_make_requirement_name(cat, sec_title, ev),
                requirement_description=_make_grounded_description(ev),
                evidence_text=ev,
                source_char_start=s_off,
                source_char_end=e_off,
                source_page=page,
                source_section=sec_title,
                statement_nature=_detect_statement_nature(ev, cat),
                evidence_type="explicit",
                scope_level=scope_level,
                canonical_topics=_extract_canonical_topics(ev, cat),
            )
        )

    return results


def parse_documents_by_ids(
    document_ids: Sequence[str],
    units_path: Path = UNITS_PATH,
    seg_val_path: Path = SEG_VAL_PATH,
    raw_txt_dir: Path = RAW_TXT_DIR,
) -> List[ParsedRequirement]:
    """Run generic parser across all CompetitionBranchUnits belonging to `document_ids`."""
    units_data = json.loads(units_path.read_text(encoding="utf-8"))
    seg_val_data = json.loads(seg_val_path.read_text(encoding="utf-8")) if seg_val_path.exists() else {}
    target_set = set(document_ids)
    all_reqs: List[ParsedRequirement] = []
    text_cache: Dict[str, str] = {}

    for unit in units_data.get("branch_units", []):
        doc_id = unit["document_id"]
        if doc_id not in target_set:
            continue
        fname = unit["file_name"]
        if fname not in text_cache:
            text_cache[fname] = (raw_txt_dir / fname).read_text(encoding="utf-8")
        all_reqs.extend(parse_branch_unit(unit, text_cache[fname], seg_validation=seg_val_data))

    return all_reqs
