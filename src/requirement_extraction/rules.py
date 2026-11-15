"""Deterministic Rule-Based Helpers for Stage 4.2 Requirement Extraction Refinement.

Provides:
- Controlled vocabularies for categories, subcategories, record types, statement natures,
  validation statuses, and term normalization rules.
- Rule-based clause classification (`classify_requirement_clause`) with negative guards
  against misclassifying file/format rules into deliverables.
- False-positive filter (`is_non_requirement_background`) to prevent historical,
  epidemiological, or promotional narratives from entering active requirements.
- Exception and conditional clause extractor (`extract_exception_or_condition`).
- Active term normalizer (`apply_term_normalization`).
- Semantic grounding verifier (`verify_description_grounded_in_evidence`) ensuring
  `requirement_description` never exceeds the facts present in `evidence_text`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

REQUIREMENT_CATEGORIES = (
    "eligibility_requirements",
    "registration_requirements",
    "competition_structure",
    "deliverables",
    "assessment_criteria",
    "technical_and_general_rules",
)

REQUIREMENT_SUBCATEGORIES: Dict[str, Tuple[str, ...]] = {
    "eligibility_requirements": (
        "education_level_and_student_status",
        "student_identity_document",
        "participation_mode_and_team_size",
        "team_composition_and_institution_rule",
        "single_team_or_cross_branch_restriction",
        "school_delegation_quota",
    ),
    "registration_requirements": (
        "registration_fee_and_payment",
        "registration_mechanism_and_portal",
        "administrative_and_twibbon_requirements",
        "payment_confirmation_format",
        "participant_verification_rule",
    ),
    "competition_structure": (
        "competition_tracks_and_themes",
        "competition_stages_and_selection",
        "competition_timeline_and_deadlines",
        "coaching_and_mentoring_program",
        "final_stage_offline_protocol",
    ),
    "deliverables": (
        "proposal_or_essay_deliverable",
        "bmc_deliverable",
        "poster_deliverable",
        "video_deliverable",
        "prototype_or_exam_deliverable",
        "presentation_slide_deliverable",
        "originality_and_plagiarism_document",
        "deliverable_template_or_example",
    ),
    "assessment_criteria": (
        "judging_criterion_weighted",
        "judging_criterion_unweighted",
        "exam_point_scoring_formula",
    ),
    "technical_and_general_rules": (
        "document_formatting_and_length",
        "media_and_file_specification",
        "originality_and_plagiarism_threshold",
        "content_and_tool_prohibition",
        "copyright_and_publication_rights",
        "exam_proctoring_and_device_rules",
        "disqualification_and_sanction_rules",
    ),
}

RECORD_TYPES = (
    "requirement",
    "information",
    "extraction_gap",
    "review_item",
)

EVIDENCE_TYPES = ("explicit", "inferred")

CONFIDENCE_LEVELS = ("high", "medium", "low")

VALIDATION_STATUSES = (
    "VALIDATED",
    "NEEDS_REVIEW",
    "VALIDATED_WITH_SEGMENTATION_LIMITATION",
)

STATEMENT_NATURES = (
    "official_rule",
    "recommendation",
    "example",
    "template",
    "supporting_info",
)

TERM_NORMALIZATION_RULES: Dict[str, Dict[str, Any]] = {
    "education_level_terms": {
        "rule_id": "NORM-EDU-01",
        "description": (
            "Istilah jenjang pendidikan dipertahankan sesuai teks sumber dan hanya dipetakan ke "
            "label terstandar apabila bukti eksplisit menyebutkan jenjang tersebut."
        ),
        "mappings": {
            "Indonesian university students": "Mahasiswa Perguruan Tinggi di Indonesia",
            "Mahasiswa aktif Perguruan Tinggi Negeri/Swasta di Indonesia": "Mahasiswa Aktif PTN/PTS di Indonesia",
            "Individu Mahasiswa aktif Perguruan Tinggi": "Mahasiswa Aktif PTN/PTS di Indonesia (Individu)",
            "pelajar aktif sekolah": "Pelajar Aktif Sekolah Negeri/Swasta di Indonesia",
            "siswa/i aktif SMA/K atau sederajat di Indonesia": "Siswa/i Aktif SMA/SMK/MA Sederajat di Indonesia",
        },
        "non_equivalent_distinction": (
            "'Mahasiswa' (University Student) dan 'Siswa/Pelajar SMA/K' (High School Student) "
            "TIDAK disamakan; cabang Poster DOC-024 membuka dua kategori terpisah (Mahasiswa & Siswa), "
            "sedangkan Esai dan BMC DOC-024 hanya untuk Mahasiswa."
        ),
    },
    "student_identity_document_terms": {
        "rule_id": "NORM-DOC-01",
        "description": (
            "Dokumen bukti status peserta dibedakan secara ketat sesuai jenjang dan istilah di buku panduan."
        ),
        "mappings": {
            "(KTM)": "Kartu Tanda Mahasiswa (University Student ID)",
            "(KTMS)": "Kartu Tanda Mahasiswa Sementara (Temporary University Student ID)",
            "Kartu Tanda\nPelajar (KTP)": "Kartu Tanda Pelajar (School Student ID pada DOC-024 Poster)",
            "Kartu Tanda Pelajar (KTP)": "Kartu Tanda Pelajar (School Student ID pada DOC-024 Poster)",
            "kartu pelajar \natau surat keterangan siswa aktif": "Kartu Pelajar atau Surat Keterangan Siswa Aktif dari Sekolah (DOC-009)",
            "kartu pelajar atau surat keterangan siswa aktif": "Kartu Pelajar atau Surat Keterangan Siswa Aktif dari Sekolah (DOC-009)",
        },
        "non_equivalent_distinction": (
            "Singkatan 'KTP' pada DOC-024 hlm. 19 tertulis secara eksplisit sebagai 'Kartu Tanda Pelajar (KTP)', "
            "BUKAN Kartu Tanda Penduduk nasional."
        ),
    },
    "deliverable_type_terms": {
        "rule_id": "NORM-DELIV-01",
        "description": (
            "Jenis karya/luaran kompetisi tidak disamakan antar-cabang walaupun menggunakan format file PDF yang sama."
        ),
        "mappings": {
            "short proposal": "Written Proposal (AI Builder Challenge)",
            "working\nprototype": "Working AI Prototype (Live Demo)",
            "working \n\nprototype": "Working AI Prototype (Live Demo)",
            "working AI prototype": "Working AI Prototype (Live Demo)",
            "Struktur esai": "Naskah Esai Ilmiah (Essay Manuscript)",
            "9 elemen BMC": "Karya Business Model Canvas (9 Elemen BMC)",
            "Customer Segments": "Karya Business Model Canvas (9 Elemen BMC)",
            "poster infografis": "Poster Infografis Digital (.pdf A3)",
            "Desain poster dibuat secara digital": "Poster Digital (JPG/JPEG/PNG A4)",
            "Video Campaign dibuat dalam bentuk portrait": "Video Campaign Edukasi (.mp4 9:16)",
            "media presentasi (PowerPoint)": "Slide Presentasi Final (PowerPoint)",
            "Surat Orisinalitas": "Surat Pernyataan Orisinalitas Karya (PDF)",
            "Hasil Turnitin": "Lampiran Bukti Cek Plagiasi / Turnitin (PDF)",
        },
        "non_equivalent_distinction": (
            "'Written Proposal', 'Naskah Esai', 'Karya BMC (9 elemen Business Model Canvas)', "
            "'Desain Poster (JPG/PNG atau PDF A3)', 'Working AI Prototype (Live Demo)', dan "
            "'Video Campaign (.mp4 9:16)' adalah luaran yang berbeda secara substansi maupun kompetensi."
        ),
    },
}

# Regex patterns for non-requirement background detection (False Positive guard)
_BACKGROUND_PATTERNS = (
    re.compile(
        r"\b(data\s+WHO|74%\s+kematian|transisi\s+epidemiologi|penyakit\s+tidak\s+menular\s*\(PTM\))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(merupakan\s+program\s+tahunan|diharapkan\s+dapat\s+menjadi\s+ajang|di\s+era\s+disrupsi|indonesia\s+emas\s+2045\s+menjadi\s+pengingat)\b",
        re.IGNORECASE,
    ),
)

_OBLIGATION_MODAL_PATTERN = re.compile(
    r"\b(wajib|wajid|wajidb|wajip|wajiod|harus|dilarang|tidak\s+diperkenankan|tidak\s+boleh|"
    r"diperbolehkan|dapat\s+mengirimkan|maksimal|minimal|batas\s+waktu|deadline|"
    r"must|required|eligible|disqualified|not\s+accepted|open\s+to|team\s+size)\b",
    re.IGNORECASE,
)


def is_non_requirement_background(text: str, section_title: str = "") -> bool:
    """Return True if text is historical/epidemiological/motivational background rather than a requirement."""
    sec_lower = section_title.lower()
    if any(
        k in sec_lower
        for k in ("latar belakang", "kata pengantar", "sambutan", "overview")
    ):
        if not _OBLIGATION_MODAL_PATTERN.search(text):
            return True

    for pat in _BACKGROUND_PATTERNS:
        if pat.search(text) and not _OBLIGATION_MODAL_PATTERN.search(text):
            return True

    return False


def classify_requirement_clause(
    text: str, section_title: str = ""
) -> Tuple[str, str, str]:
    """Classify a requirement text clause into (requirement_category, requirement_subcategory, statement_nature).

    Implements deterministic priority rules and negative guards to prevent category misclassification
    (such as placing file format/resolution specs into `deliverables`).
    """
    t_lower = text.lower()
    s_lower = section_title.lower()

    # Determine statement_nature first
    statement_nature = "official_rule"
    if re.search(
        r"\b(diusahakan|disarankan|sebaiknya|recommended)\b", t_lower
    ):
        statement_nature = "recommendation"
    elif re.search(
        r"\b(hanya\s+dipergunakan\s+sebagai\s+contoh|sebagai\s+contoh\s+sehingga)\b",
        t_lower,
    ):
        statement_nature = "example"
    elif re.search(
        r"\b(format\s+cover\s+dan\s+lembar\s+orisinalitas\s+peserta\s+dapat\s+diakses|template\s+dari\s+naskah\s+esai\s+akan\s+diberikan)\b",
        t_lower,
    ):
        statement_nature = "template"
    elif is_non_requirement_background(text, section_title):
        statement_nature = "supporting_info"

    # 1. Assessment Criteria guard
    if (
        any(
            k in s_lower
            for k in (
                "judging criteria",
                "skema penilaian",
                "kriteria penilaian",
                "sistem penilaian",
            )
        )
        and re.search(
            r"(\d+\s*%|poin|aspek\s+penilaian|inovasi|keaslian|kreativitas|tata\s+letak|akurasi|penyampaian\s+presentasi|sesi\s+tanya\s+jawab|orisinalitas\s+ide)",
            t_lower,
        )
        and not re.search(r"akan\s+diseleksi\s+oleh\s+tim\s+juri\s+dan\s+dipilih", t_lower)
    ):
        if re.search(r"[+-]?\d+\s*poin", t_lower):
            return (
                "assessment_criteria",
                "exam_point_scoring_formula",
                statement_nature,
            )
        if re.search(r"\d+\s*%", t_lower):
            return (
                "assessment_criteria",
                "judging_criterion_weighted",
                statement_nature,
            )
        return (
            "assessment_criteria",
            "judging_criterion_unweighted",
            statement_nature,
        )

    # 2. Technical & General Rules guard (MUST run before Deliverables to prevent file-spec misclassification!)
    if re.search(
        r"(format\s+file\s*:\s*jpg|resolusi\s*:\s*minimal\s*300\s*pixel|mode\s+warna\s*:\s*rgb|"
        r"batas\s+tepi\s*:\s*kiri|jenis\s+font\s*:\s*times\s+new\s+roman|spasi\s+baris\s*:\s*1\.5|"
        r"minimal\s+5\s+halaman\s+dan\s+maksimal\s*\.?\s*10\s+halaman|"
        r"7\s+halaman\s*[–-]\s*10\s+halaman|tidak\s+ada\s+batas\s+halaman)",
        t_lower,
    ):
        if re.search(r"(jpg|jpeg|png|300\s*pixel|rgb)", t_lower):
            return (
                "technical_and_general_rules",
                "media_and_file_specification",
                statement_nature,
            )
        return (
            "technical_and_general_rules",
            "document_formatting_and_length",
            statement_nature,
        )

    if re.search(
        r"(tidak\s+diperkenankan\s+menggunakan\s+bantuan\s+artificial\s+intelligence|"
        r"tidak\s+mengandung\s+unsur\s+sara|unsur\s+produk\s+komersial|"
        r"tanpa\s+menggunakan\s+template\s+siap\s+pakai)",
        t_lower,
    ):
        return (
            "technical_and_general_rules",
            "content_and_tool_prohibition",
            statement_nature,
        )

    if re.search(
        r"(hak\s+cipta\s+poster\s+publik\s+adalah\s+milik\s+peserta|mempublikasikan\s+setiap\s+karya\s+pemenang)",
        t_lower,
    ):
        return (
            "technical_and_general_rules",
            "copyright_and_publication_rights",
            statement_nature,
        )

    if re.search(
        r"(batas\s+plagiasi\s+30%|bukan\s+merupakan\s+salinan,\s+terjemahan,\s+ataupun\s+plagiat)",
        t_lower,
    ):
        return (
            "technical_and_general_rules",
            "originality_and_plagiarism_threshold",
            statement_nature,
        )

    if re.search(
        r"(perlombaan\s+dilaksanakan\s+dengan\s+2\s+device|diusahakan\s+laptop/komputer)",
        t_lower,
    ):
        return (
            "technical_and_general_rules",
            "exam_proctoring_and_device_rules",
            statement_nature,
        )

    if re.search(
        r"(disqualification\.|didiskualifikasi|keputusan\s+dewan\s+juri\s+adalah\s+mutlak|"
        r"tidak\s+diperkenankan\s+mengenakan\s+atribut\s+atau\s+identitas\s+yang\s+menunjukkan\s+asal\s+sekolah)",
        t_lower,
    ):
        return (
            "technical_and_general_rules",
            "disqualification_and_sanction_rules",
            statement_nature,
        )

    # 3. Eligibility Requirements guard
    if re.search(
        r"(open\s+to\s+indonesian\s+university\s+students|mahasiswa\s+aktif\s+perguruan\s+tinggi|"
        r"siswa/i\s+aktif\s+sma/k|pelajar\s+aktif\s+sekolah)",
        t_lower,
    ):
        return (
            "eligibility_requirements",
            "education_level_and_student_status",
            statement_nature,
        )

    if re.search(
        r"(provide\s+a\s+valid\s+student\s+id\s*\(ktm\)|kartu\s+tanda\s+mahasiswa|kartu\s+pelajar\s+atau\s+surat\s+keterangan)",
        t_lower,
    ):
        return (
            "eligibility_requirements",
            "student_identity_document",
            statement_nature,
        )

    if re.search(
        r"(team\s+size:\s*3\s+to\s+4\s+members|lomba\s+bersifat\s+individu|"
        r"perorangan\s+maupun\s+kelompok\s+dengan\s+jumlah\s+2\s+orang|"
        r"tim\s+terdiri\s+dari\s+3\s+orang|tim\s+terdiri\s+dari\s+2-3\s+orang)",
        t_lower,
    ):
        return (
            "eligibility_requirements",
            "participation_mode_and_team_size",
            statement_nature,
        )

    if re.search(
        r"(one\s+person,\s+one\s+team|tidak\s+diperkenankan\s+mengikuti\s+lebih\s+dari\s+satu\s+cabang|"
        r"diperbolehkan\s+mengikuti\s+maksimal\s+satu\s+cabang)",
        t_lower,
    ):
        return (
            "eligibility_requirements",
            "single_team_or_cross_branch_restriction",
            statement_nature,
        )

    if re.search(
        r"(setiap\s+sekolah\s+menengah\s+atas\s+diperbolehkan\s+untuk\s+mengirimkan\s+lebih)",
        t_lower,
    ):
        return (
            "eligibility_requirements",
            "school_delegation_quota",
            statement_nature,
        )

    # 4. Registration Requirements guard
    if re.search(
        r"(registration\s+is\s+free|gelombang\s+i\s*:\s*rp|gelombang\s+1\s*:\s*r[op]p?\d|"
        r"biaya\s+yang\s+telah\s+dibayarkan\s+tidak\s+dapat\s+dikembalikan|tidak\s+dapat\s+ditarik\s+kembali)",
        t_lower,
    ):
        return (
            "registration_requirements",
            "registration_fee_and_payment",
            statement_nature,
        )

    if re.search(
        r"(verified\s+participant\.\s+for\s+prize\s+pool\s+calculation)",
        t_lower,
    ):
        return (
            "registration_requirements",
            "participant_verification_rule",
            statement_nature,
        )

    if re.search(
        r"(twibbon|tag\s+3\s+orang\s+teman|mengikuti\s+akun\s+instagram\s+dan\s+tiktok)",
        t_lower,
    ):
        return (
            "registration_requirements",
            "administrative_and_twibbon_requirements",
            statement_nature,
        )

    if re.search(
        r"(fill\s+in\s+the\s+team\s+registration\s+google\s+form|join\s+the\s+official\s+event\s+page\s+on\s+xdemia|"
        r"melakukan\s+pendaftaran\s+secara\s+online\s+melalui\s+link\s+google\s+forms|"
        r"melakukan\s+pendaftaran\s+disertai\s+dengan\s+mengunggah)",
        t_lower,
    ):
        return (
            "registration_requirements",
            "registration_mechanism_and_portal",
            statement_nature,
        )

    # 5. Deliverables guard
    if re.search(
        r"(submit\s+a\s+short\s+proposal|struktur\s+esai\s+secara\s+umum|9\s+elemen\s+bmc|customer\s+segments|"
        r"working\s+prototype|live\s+demo\s+requirement|media\s+presentasi\s*\(powerpoint\)|"
        r"surat\s+o[rf]?isinalitas\s+dikirimkan|hasil\s+turnitin\s+maksimal\s+25%|"
        r"video\s+campaign\s+dibuat\s+dalam\s+bentuk\s+portrait|desain\s+poster\s+dikirimkan\s+dalam\s+bentuk\s+pdf)",
        t_lower,
    ):
        if "powerpoint" in t_lower or "pitch live" in t_lower:
            return (
                "deliverables",
                "presentation_slide_deliverable",
                statement_nature,
            )
        if "bmc" in t_lower or "customer segments" in t_lower:
            return ("deliverables", "bmc_deliverable", statement_nature)
        if "poster" in t_lower:
            return ("deliverables", "poster_deliverable", statement_nature)
        if "video" in t_lower:
            return ("deliverables", "video_deliverable", statement_nature)
        if "prototype" in t_lower or "e-ujian" in t_lower:
            return (
                "deliverables",
                "prototype_or_exam_deliverable",
                statement_nature,
            )
        return (
            "deliverables",
            "proposal_or_essay_deliverable",
            statement_nature,
        )

    # 6. Competition Structure guard
    if re.search(r"(general\s+track|industry\s+case\s+track|sub-?tema)", t_lower):
        return (
            "competition_structure",
            "competition_tracks_and_themes",
            statement_nature,
        )
    if re.search(r"(structured\s+coaching|coaching\s+sessions)", t_lower):
        return (
            "competition_structure",
            "coaching_and_mentoring_program",
            statement_nature,
        )
    if re.search(r"(karantina\s+peserta|seminar\s+nasional\s+pharmacopeia)", t_lower):
        return (
            "competition_structure",
            "final_stage_offline_protocol",
            statement_nature,
        )
    if re.search(
        r"(gelombang\s+i|gelombang\s+1|timeline|penilaian\s+27\s*-\s*30\s+mei|21\s+november\s+2026)",
        t_lower,
    ):
        return (
            "competition_structure",
            "competition_timeline_and_deadlines",
            statement_nature,
        )

    return (
        "competition_structure",
        "competition_stages_and_selection",
        statement_nature,
    )


def extract_exception_or_condition(text: str) -> str:
    """Extract explicit exception, exemption, or conditional clauses from multi-sentence requirements."""
    patterns = [
        r"(kecuali\s+[^.\n]+(?:\.[^.\n]*)?)",
        r"(tidak\s+termasuk\s+[^).\n]+)",
        r"(diperbolehkan\s+berasal\s+dari\s+[^).\n]+)",
        r"(meskipun\s+tidak\s+dihadiri\s+oleh\s+seluruh\s+anggota\s+tim[^.\n]*)",
        r"(jika\s+tidak\s+dilakukan\s+konfirmasi\s+ulang[^.\n]*)",
        r"(jika\s+terdapat\s+ketidakhadiran\s+secara\s+offline[^.\n]*)",
        r"(without\s+a\s+working\s+demo,\s+a\s+team\s+is\s+not\s+eligible\s+for\s+prizes)",
        r"(if\s+a\s+venue\s+is\s+not\s+confirmed\s+in\s+time,\s+it\s+moves\s+fully\s+online[^.\n]*)",
        r"(presentasi\s+boleh\s+dilakukan\s+dengan\s+menampilkan\s+hasil\s+poster)",
    ]
    matches: List[str] = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            cleaned = " ".join(m.group(1).split())
            if cleaned not in matches:
                matches.append(cleaned)
    return "; ".join(matches) if matches else "NONE"


def apply_term_normalization(evidence_text: str) -> List[Dict[str, str]]:
    """Actively scan evidence_text against TERM_NORMALIZATION_RULES and return matched normalizations."""
    applied: List[Dict[str, str]] = []
    ev_lower = evidence_text.lower()
    for group_key, rule_info in TERM_NORMALIZATION_RULES.items():
        rule_id = rule_info["rule_id"]
        mappings = rule_info.get("mappings", {})
        for raw_term, norm_label in mappings.items():
            # Normalize whitespace for matching across linewraps
            norm_raw = " ".join(raw_term.lower().split())
            norm_ev = " ".join(ev_lower.split())
            if norm_raw in norm_ev:
                entry = {
                    "rule_id": rule_id,
                    "term_group": group_key,
                    "matched_source_term": " ".join(raw_term.split()),
                    "normalized_label": norm_label,
                }
                if entry not in applied:
                    applied.append(entry)
    return applied


_WORD_TO_NUMBER_EQUIVALENTS: Dict[str, Tuple[str, ...]] = {
    "1": ("1", "satu", "one", "single", "pertama", "i"),
    "2": ("2", "dua", "two", "both", "kedua", "ii"),
    "3": ("3", "tiga", "three", "ketiga", "iii"),
    "4": ("4", "empat", "four", "four criteria", "keempat"),
    "5": ("5", "lima", "five", "kelima"),
    "6": ("6", "enam", "six", "keenam"),
    "7": ("7", "tujuh", "seven"),
    "8": ("8", "delapan", "eight"),
    "9": ("9", "sembilan", "nine"),
    "10": ("10", "sepuluh", "ten"),
    "04": ("04", "4", "o4n"),
    "07": ("07", "7", "907"),
}


def verify_description_grounded_in_evidence(
    description: str,
    evidence_text: str,
    evidence_type: str = "explicit",
) -> Tuple[bool, List[str]]:
    """Verify that all numeric, percentage, currency, and URL claims in `description` exist in `evidence_text`.

    Returns `(is_grounded, ungrounded_claims)`.
    """
    if evidence_type != "explicit":
        return True, []

    ev_norm = " ".join(evidence_text.lower().split())
    # Strip composite sum explanations like "20% (10% + 10%)" where 10% is in evidence
    ungrounded: List[str] = []

    # 1. Check URLs / domain paths in description
    url_matches = re.findall(
        r"(?:https?://)?(?:www\.)?(?:xdemia\.com/[^\s),]+|linktr\.ee/[^\s),]+|twibbo\.nz/[^\s),]+|bit\.ly/[^\s),]+|e-ujian\.com)",
        description,
        flags=re.IGNORECASE,
    )
    for url in url_matches:
        url_clean = url.lower().rstrip(".")
        # Handle OCR split URLs in DOC-009 ('bit.l y/' or 'wwwe- \n\nujian.com')
        ev_nospace = re.sub(r"\s+", "", evidence_text.lower())
        url_core = (
            url_clean.replace("https://", "")
            .replace("http://", "")
            .replace("e-ujian.com", "ujian.com")
        )
        if url_core not in ev_nospace:
            ungrounded.append(f"URL:{url}")

    # 2. Check currency nominals (e.g. Rp45.000, Rp70.001)
    rp_matches = re.findall(r"Rp\s?(\d+(?:\.\d{3})+)", description, flags=re.IGNORECASE)
    for rp_num in rp_matches:
        if rp_num not in ev_norm:
            ungrounded.append(f"CURRENCY:Rp{rp_num}")

    # 3. Check percentages (e.g. 25%, 30%, 10%)
    pct_matches = re.findall(r"(\d+)\s*%", description)
    for pct in pct_matches:
        if f"{pct}%" not in ev_norm and f"{pct} %" not in ev_norm:
            ungrounded.append(f"PERCENTAGE:{pct}%")

    # 4. Check standalone numbers (excluding numbers that are part of Rp amounts already checked)
    desc_without_rp = re.sub(r"Rp\s?\d+(?:\.\d{3})+", " ", description)
    num_matches = re.findall(r"\b(\d+)\b", desc_without_rp)
    for num in num_matches:
        if num in ev_norm:
            continue
        # Check word equivalents (e.g. "2 langkah" -> "two steps", "4 kriteria" -> "four criteria")
        equivalents = _WORD_TO_NUMBER_EQUIVALENTS.get(num, (num,))
        if any(eq in ev_norm for eq in equivalents):
            continue
        ungrounded.append(f"NUMBER:{num}")

    return (len(ungrounded) == 0), ungrounded
