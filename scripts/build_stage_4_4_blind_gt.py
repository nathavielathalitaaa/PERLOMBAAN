#!/usr/bin/env python3
"""Build and freeze the manual Stage 4.4 blind held-out ground truth dataset."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path("/home/lalita/Projects/perlombaan")
RAW_TXT_DIR = BASE_DIR / "data" / "raw" / "txt"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

ALLOWED_CATEGORIES = {
    "eligibility_requirements",
    "registration_requirements",
    "competition_structure",
    "deliverables",
    "assessment_criteria",
    "technical_and_general_rules",
}

ALLOWED_SCOPE_LEVELS = {"event_shared", "branch_specific"}

ALLOWED_ANNOTATION_STATUSES = {"verified", "ambiguous_needs_review"}

REQUIRED_FIELDS = [
    "annotation_id",
    "document_id",
    "branch_unit_id",
    "requirement_category",
    "requirement_name",
    "requirement_description",
    "evidence_text",
    "source_char_start",
    "source_char_end",
    "source_page",
    "statement_nature",
    "evidence_type",
    "scope_level",
    "annotation_status",
    "annotator_notes",
]

DOC_METADATA = {
    "DOC-011": {
        "filename": "ENERGY4ME GUIDEBOOK.txt",
        "branch_unit_id": "DOC-011-BU-01",
        "branch_code": "BR_STEM_PROJECT",
        "unit_char_start": 0,
        "unit_char_end": 10686,
        "has_page_numbers": False,
        "expected_not_stated_categories": [
            "registration_fee (not stated in document)",
            "participant_age_limit (not stated in document)",
        ],
    },
    "DOC-017": {
        "filename": "GUIDE BOOK NEXTGEN BMC.txt",
        "branch_unit_id": "DOC-017-BU-01",
        "branch_code": "BR_BMC",
        "unit_char_start": 0,
        "unit_char_end": 7568,
        "has_page_numbers": False,
        "expected_not_stated_categories": [
            "education_level_restriction (open to general public)",
            "participant_age_limit (not stated in document)",
        ],
    },
    "DOC-051": {
        "filename": "Guidebook_Hackathon.txt",
        "branch_unit_id": "DOC-051-BU-01",
        "branch_code": "BR_HACKATHON",
        "unit_char_start": 0,
        "unit_char_end": 29467,
        "has_page_numbers": False,
        "expected_not_stated_categories": [
            "participant_age_limit (not stated in document)",
            "prize_or_awards (not stated in document)",
        ],
    },
    "DOC-070": {
        "filename": "Pedoman EIC - PGTC 2026.txt",
        "branch_unit_id": "DOC-070-BU-01",
        "branch_code": "BR_SCIENTIFIC_PAPER",
        "unit_char_start": 3103,
        "unit_char_end": 66490,
        "has_page_numbers": True,
        "expected_not_stated_categories": [
            "registration_fee (not stated in document)",
            "participant_age_limit (not stated; semester caps S1/D4 max 8, D3 max 6)",
        ],
    },
    "DOC-053": {
        "filename": "Guidebook_Wreck_IT_7.0.txt",
        "branch_unit_id": "DOC-053-BU-01",
        "branch_code": "BR_CYBERSECURITY_CTF",
        "unit_char_start": 0,
        "unit_char_end": 19471,
        "has_page_numbers": False,
        "expected_not_stated_categories": [
            "registration_fee (not stated in document)",
            "participant_age_limit (not stated in document)",
            "ctf_and_hackathon_scoring_weights (exact rubric percentages not stated in document)",
        ],
    },
}


def find_exact_span(
    raw_text: str,
    start_anchor: str,
    end_anchor: str | None = None,
    occurrence: int = 1,
    min_pos: int = 0,
) -> tuple[int, int, str]:
    """Locate an exact substring span in raw_text using start/end anchors."""
    pos = min_pos
    found_idx = -1
    for _ in range(occurrence):
        found_idx = raw_text.find(start_anchor, pos)
        if found_idx == -1:
            raise ValueError(
                f"Start anchor not found (occ={occurrence}, min_pos={min_pos}): {start_anchor!r}"
            )
        pos = found_idx + len(start_anchor)

    if end_anchor is None:
        end_idx = found_idx + len(start_anchor)
    else:
        end_find = raw_text.find(end_anchor, found_idx)
        if end_find == -1:
            raise ValueError(
                f"End anchor not found after start {found_idx}: {end_anchor!r}"
            )
        end_idx = end_find + len(end_anchor)

    return found_idx, end_idx, raw_text[found_idx:end_idx]


def infer_pgtc_page(raw_text: str, char_pos: int) -> int | None:
    """Infer printed page number from PGTC footer lines following char_pos."""
    footer_pattern = re.compile(
        r"Pedoman Energynovation Ideas Competition PGTC 2026[^\n]*?\b(\d{1,2})\s*$"
    )
    tail = raw_text[char_pos:]
    for line in tail.splitlines():
        m = footer_pattern.search(line.strip())
        if m:
            return int(m.group(1))
    return None


def build_raw_annotations() -> list[dict[str, Any]]:
    """Return manual ground-truth specifications for all 5 held-out documents."""
    specs: list[dict[str, Any]] = [
        # =====================================================================
        # DOC-011: ENERGY4ME GUIDEBOOK.txt (SPARK UP 2026 - ENERGY4ME Competition)
        # =====================================================================
        {
            "document_id": "DOC-011",
            "category": "eligibility_requirements",
            "name": "Active Indonesian High School Student Eligibility",
            "description": "Participants must be active high school students or equivalent in Indonesia.",
            "start": "1.Participants must be active high school students in\nIndonesia.",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Explicit eligibility requirement in General Requirements item 1.",
        },
        {
            "document_id": "DOC-011",
            "category": "eligibility_requirements",
            "name": "Unlimited Teams Per School",
            "description": "There is no limit on the number of teams representing a single high school or equivalent.",
            "start": "2.There is no limit on the number of teams representing a\nsingle high school or equivalent.",
            "end": None,
            "nature": "permissive_rule",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Explicit institutional quota rule in General Requirements item 2.",
        },
        {
            "document_id": "DOC-011",
            "category": "eligibility_requirements",
            "name": "Team Size and Single-Team Membership",
            "description": "Each team consists of a maximum of 5 members, and each participant may only be registered in 1 team.",
            "start": "3.Each team consists of a maximum of 5 members.\n4.Each participant may only be registered in 1 team.",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Combines team size cap and single-team membership rule (items 3-4).",
        },
        {
            "document_id": "DOC-011",
            "category": "registration_requirements",
            "name": "Registration Period and Data Upload",
            "description": "Registration form submission and team data upload take place from October 15 to November 8, 2026.",
            "start": "Registration form\nOctober 15 – November 8,\n\nRegistration submission and team\n2026\n\ndata upload",
            "end": None,
            "nature": "schedule_milestone",
            "evidence_type": "explicit_schedule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Registration window and required action from Timeline table.",
        },
        {
            "document_id": "DOC-011",
            "category": "registration_requirements",
            "name": "Twibbon Upload and Social Media Follow",
            "description": "Participants are required to upload the ENERGY4ME competition twibbon and follow Instagram accounts @universitaspertamina and @speupsc.",
            "start": "7.Participants are required to upload the ENERGY4ME\n\ncompetition twibbon.\n8.Participants are required to follow the Instagram accounts\n\n@universitaspertamina and @speupsc.",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Administrative/social media registration obligations (items 7-8).",
        },
        {
            "document_id": "DOC-011",
            "category": "competition_structure",
            "name": "Competition Themes",
            "description": "Participants must design and conduct simple experiments based on one of four committee-determined themes: Hydropower, Solar Energy, Wind Energy, and Petroleum.",
            "start": "In this competition participants will design and\nconduct simple experiments based on themes determined by\nthe committee namely Hydropower Solar Energy Wind Energy\nand Petroleum which represent both renewable and non\nrenewable energy.",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Four official experiment themes.",
        },
        {
            "document_id": "DOC-011",
            "category": "competition_structure",
            "name": "Two-Round Competition Structure and Top 5 Advancement",
            "description": "The competition consists of Preliminary Round (abstract submission) and Final Round (live offline experiment presentation). Top 5 highest-scoring teams qualify for Final Round, and Preliminary scores are not accumulated with Final scores.",
            "start": "The competition is carried out in two rounds namely the\nPreliminary Round and the Final Round.",
            "end": "Preliminary Round scores are used as the basis for\nselection and are not accumulated with Final Round\nscores.",
            "nature": "procedural_rule",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Full competition mechanism and non-accumulation rule.",
        },
        {
            "document_id": "DOC-011",
            "category": "competition_structure",
            "name": "Competition Timeline (Post-Registration Stages)",
            "description": "Timeline lists Preliminary Round Abstract submission (Oct 15 - Nov 8, 2026), Finalist Announcement (Nov 19, 2026), Final Round offline at Universitas Pertamina (Nov 27, 2026), and Awarding at Closing SPARK UP 2026 (Nov 27, 2026).",
            "start": "October 15 – November 8,\nPreliminary Round Abstract submission\n\n2026\n\nAnnouncement of 5\nFinalist Announcement November 19, 2026 teams qualifying for the\n\nfinal round\n\nFinal presentation\nFinal Round November 27, 2026 (offline) at Universitas\n\nPertamina\n\nAwarding November 27, 2026 Closing SPARK UP 2026",
            "end": None,
            "nature": "schedule_milestone",
            "evidence_type": "explicit_schedule",
            "scope": "branch_specific",
            "status": "ambiguous_needs_review",
            "notes": "Internal date conflict: Timeline table states Oct 15 - Nov 8, 2026 for Preliminary Abstract submission, whereas Preliminary Round section 4 states Nov 15, 2026 at 23.59 WIB.",
        },
        {
            "document_id": "DOC-011",
            "category": "competition_structure",
            "name": "Preliminary Abstract Submission Deadline",
            "description": "Abstract submission deadline is November 15, 2026 at 23.59 WIB (GMT+7) via the official online link.",
            "start": "4.Submission Guidelines\nAbstract submission deadline: November 15 2026 at 23.59\nWIB (GMT+7)",
            "end": "no later than November 15\n2026 at 23.59 WIB (GMT+7).",
            "nature": "schedule_milestone",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "ambiguous_needs_review",
            "notes": "Conflicts with Timeline table (Nov 8 vs Nov 15, 2026).",
        },
        {
            "document_id": "DOC-011",
            "category": "competition_structure",
            "name": "Judging Panel Composition and Finality",
            "description": "There will be 3 judges, and their decisions are final and non-negotiable.",
            "start": "Judges\nThere will be 3 judges. The decisions of the judges are final and\nnon negotiable.",
            "end": None,
            "nature": "procedural_rule",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Tournament Officials section.",
        },
        {
            "document_id": "DOC-011",
            "category": "deliverables",
            "name": "Preliminary Round Abstract Content and Formatting",
            "description": "Each team submits 1 structured abstract (experiment plan for Final Round) containing Title, Brief background, Objectives, Experimental design, Expected results/benefits, Keywords; written in English, A4, margins top 3/left 4/right 3/bottom 3 cm, Times New Roman 12 pt, 1.5 line spacing, 250-450 words, APA Style references, PDF format, named SPARKUP2026_ENERGY4ME_Preliminary_TeamName.pdf.",
            "start": "1.General Provisions\nEach team submits 1 abstract according to the chosen\ntheme.",
            "end": "File format: PDF",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Combines Preliminary Round abstract provisions, required sections, formatting specs, and file naming.",
        },
        {
            "document_id": "DOC-011",
            "category": "deliverables",
            "name": "Final Round Live Experiment and Presentation Flow",
            "description": "Finalists must implement their preliminary abstract ideas into real experiments presented live offline in front of judges, covering opening/identity, energy theme, scientific concept, live experiment demonstration, results/findings, and conclusion.",
            "start": "Participants must implement the ideas developed during\nthe Preliminary Round stage into real experiments\npresented live in front of the judges.",
            "end": "Closing or conclusion.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Final Round deliverable and required presentation content flow.",
        },
        {
            "document_id": "DOC-011",
            "category": "deliverables",
            "name": "Final Round Presentation Duration and Equipment",
            "description": "Presentation duration is max 15 minutes followed by 30 minutes Q&A; participants must bring their own experiment tools and materials and may use presentation slides or supporting media.",
            "start": "3.Presentation Technical Provisions\nPresentation duration is a maximum of 15 minutes followed\nby a 30 minute question and answer session with the\njudges.",
            "end": "Participants may use presentation slides or other\nsupporting media to assist in delivering their material.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Final presentation timing, equipment responsibility, and optional media.",
        },
        {
            "document_id": "DOC-011",
            "category": "assessment_criteria",
            "name": "Preliminary Round Judging Criteria",
            "description": "Preliminary Round abstract evaluation weights: Idea clarity 30%, Relevance to theme 30%, Creativity and innovation 20%, Abstract structure compliance 20% (Total 100%).",
            "start": "1.Prelimnary Round\nIn this Preliminary Round participants will compile an abstract",
            "end": "Abstract structure 20% Structured and\ncompliance complete\n\nTotal 100%",
            "nature": "evaluation_criterion",
            "evidence_type": "explicit_rubric",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Preliminary scoring rubric table.",
        },
        {
            "document_id": "DOC-011",
            "category": "assessment_criteria",
            "name": "Final Round Judging Criteria",
            "description": "Final Round live experiment evaluation weights: Alignment with initial abstract ideas 25%, Clarity of delivery 25%, Experiment execution 25%, Presentation creativity 25% (Total 100%).",
            "start": "2.Final Round\n In this Final Round participants will present their experiments",
            "end": "Presentation engaging neat and\n\n25%\ncreativity easy to\n\nunderstand.\n\nTotal 100%",
            "nature": "evaluation_criterion",
            "evidence_type": "explicit_rubric",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Final Round scoring rubric table.",
        },
        {
            "document_id": "DOC-011",
            "category": "technical_and_general_rules",
            "name": "Originality and Guidebook Compliance",
            "description": "Submitted works must be original, unpublished, and not entered into other competitions previously; all technical rules in the Official Guidebook must be followed.",
            "start": "5.Submitted works must be original unpublished and have\n\nnot been entered into other competitions previously.\n6.All technical rules must be followed according to the\n\nOfficial Guidebook.",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "General Requirements items 5-6.",
        },
        {
            "document_id": "DOC-011",
            "category": "technical_and_general_rules",
            "name": "Preliminary Round Penalties and Disqualification",
            "description": "Format non-compliance and late submissions may incur point deductions or non-processing; cheating, data manipulation, or rule violations result in disqualification.",
            "start": "5.Penalties\nFormat non compliance may result in point deductions",
            "end": "Cheating data manipulation or rule violations will result in\ndisqualification.",
            "nature": "prohibition",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Preliminary Round penalties.",
        },
        {
            "document_id": "DOC-011",
            "category": "technical_and_general_rules",
            "name": "Final Round Attendance, Student ID, and Penalties",
            "description": "Finalists must arrive per schedule at Universitas Pertamina Jakarta and bring a student ID card; non-compliant presentations or late arrival may incur point deductions or forfeiture, and cheating/manipulation/rule violations result in disqualification.",
            "start": "Participants must arrive according to the presentation\nsession schedule set by the committee.\nParticipants are required to bring identification student\ncard.",
            "end": "Cheating data manipulation or rule violations will result in\ndisqualification.si.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Final Round implementation provisions and penalties (note minor OCR typo 'disqualification.si.').",
        },
        # =====================================================================
        # DOC-017: GUIDE BOOK NEXTGEN BMC.txt (IBC 2026 - Next Gen BMC 2.0)
        # =====================================================================
        {
            "document_id": "DOC-017",
            "category": "eligibility_requirements",
            "name": "General Public Eligibility and Team Size",
            "description": "Next Gen BMC 2.0 is open to the general public, with 1-5 people per team.",
            "start": "1.Peserta Terbuka untuk umum\n2.Peserta terdiri atas 1–5 orang dalam setiap tim.",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Persyaratan Peserta items 1-2.",
        },
        {
            "document_id": "DOC-017",
            "category": "registration_requirements",
            "name": "Registration Fees and Official Portal",
            "description": "Registration fee is Rp25.000 (Early Bird: 1 Aug - 1 Nov 2026) and Rp50.000 (Normal: 2 Nov - 2 Dec 2026), paid and registered via https://s.id/NextGen (Google Form).",
            "start": "BIAYA PENDAFTARAN\n\n1.Pendaftaran Early Bird: Rp25.000\n2.Pendaftaran Normal: Rp50.000\n\nPembayaran dan proses pendaftaran peserta\ndilakukan melalui website resmi NextGen BMC\nyang dapat diakses melalui tautan berikut: \nhttps://s.id/NextGen.",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Biaya Pendaftaran and portal link.",
        },
        {
            "document_id": "DOC-017",
            "category": "registration_requirements",
            "name": "Registration Schedule Windows",
            "description": "Early Bird registration is 1 August - 1 November 2026; Normal Price registration is 2 November - 2 December 2026.",
            "start": "Pendaftaran Early 1 Agustus - \nBird 1 November 2026\n\nPendaftaran Normal 2 November - \nPrice 2 Desember 2026",
            "end": None,
            "nature": "schedule_milestone",
            "evidence_type": "explicit_schedule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Registration periods in Waktu dan Tempat table.",
        },
        {
            "document_id": "DOC-017",
            "category": "competition_structure",
            "name": "Online Modality, Theme, and Competition Flow",
            "description": "The competition is held fully online under the theme 'Business Innovation for the Future', following the flow: Registration -> BMC Submission -> Join WhatsApp Group -> Winner Announcement.",
            "start": "Alur Lomba:\nRegistrasi → Pengumpulan BMC → Join Grup WhatsApp →\nPengumuman Pemenang",
            "end": None,
            "occ": 1,
            "nature": "procedural_rule",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "ambiguous_needs_review",
            "notes": "Note minor internal ambiguity: Alur Lomba shows single-stage submission to Winner Announcement, while Hadiah dan Benefit lists 'Top 10 Finalis' and 'Top 25 Semifinalis' without explaining semifinal/final stages.",
        },
        {
            "document_id": "DOC-017",
            "category": "competition_structure",
            "name": "BMC Submission and Winner Announcement Dates",
            "description": "BMC submission deadline is 3 December 2026 and winner announcement is 7 December 2026.",
            "start": "Deadline\nPengumpulan BMC 3 Desember 2026\n\nPengumuman\nPemenang 7 Desember 2026\n\nTempat:\nRangkaian lomba Next Gen BMC 2.0 dilaksanakan\nsecara online.",
            "end": None,
            "nature": "schedule_milestone",
            "evidence_type": "explicit_schedule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Submission and announcement milestones.",
        },
        {
            "document_id": "DOC-017",
            "category": "deliverables",
            "name": "BMC PDF Deliverable, Template, Naming, and Submission Procedure",
            "description": "Each participant submits 1 readable, non-corrupted PDF BMC using the official template (https://s.id/NextGen-BMC), named NextGenBMC2.0_NamaPeserta_JudulBisnis, submitted once via Google Form (https://s.id/NextGen-SubmitBMC) with required data.",
            "start": "PROSEDUR\nPENGUMPULAN KARYA\n\n1.Peserta wajib mengumpulkan karya berupa Business\nModel Canvas (BMC) melalui Google Form\nPengumpulan yang disediakan oleh panitia.",
            "end": "Canvas (BMC) yang telah disediakan oleh panitia\nmelalui link berikut: https://s.id/NextGen-BMC.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Full deliverable specification, PDF format, naming convention, template link, and one-time submission rule.",
        },
        {
            "document_id": "DOC-017",
            "category": "assessment_criteria",
            "name": "BMC Judging Criteria and Weights",
            "description": "Judging weights: Kelengkapan Elemen BMC (25%), Kreativitas Ide Bisnis (25%), Kesesuaian Antar Elemen BMC (25%), Potensi Pengembangan Bisnis (15%), Kerapian dan Kejelasan Penyajian (10%) (Total 100%).",
            "start": "KRITERIA PENILAIAN\n\nKriteria Penilaian Bobot Deskripsi",
            "end": "Total 100%",
            "nature": "evaluation_criterion",
            "evidence_type": "explicit_rubric",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Complete assessment rubric table.",
        },
        {
            "document_id": "DOC-017",
            "category": "technical_and_general_rules",
            "name": "Originality, Content Restrictions, Disqualification, and Jury Finality",
            "description": "Max 1 work per participant; BMC must be original/own thinking without plagiarism, SARA, pornography, violence, hate speech, or discrimination; committee may disqualify violators and jury decisions are final.",
            "start": "5.Setiap peserta hanya diperbolehkan\nmengumpulkan 1 karya.\n\n6.Karya BMC harus merupakan hasil pemikiran\nsendiri.\n\n7.Karya tidak boleh mengandung unsur\nplagiarisme.\n\n8.Karya tidak boleh mengandung unsur SARA,\npornografi, kekerasan, ujaran kebencian,\ndiskriminasi, atau konten negatif lainnya.\n\n9.Format file yang dikumpulkan adalah pdf.\n10.Peserta wajib memastikan file yang\n\ndikumpulkan dapat dibuka dan terbaca\ndengan jelas.\n\n11.Panitia berhak mendiskualifikasi peserta\napabila ditemukan pelanggaran terhadap\nketentuan lomba.\n\n12.Keputusan juri bersifat mutlak dan tidak dapat\ndiganggu gugat.",
            "end": None,
            "nature": "prohibition",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Ketentuan dan Peraturan items 5-12.",
        },
        # =====================================================================
        # DOC-051: Guidebook_Hackathon.txt (Milad IT Fest 19 - Hackathon Web Innovation)
        # =====================================================================
        {
            "document_id": "DOC-051",
            "category": "eligibility_requirements",
            "name": "Student Status, Team Size, Cross-Institution, and Single-Team Rule",
            "description": "Participants must be active SMA/SMK/equivalent or D3/D4/S1 students in Indonesia; teams consist of 2-4 members with 1 team leader (same or different institutions allowed); 1 participant may only join 1 team; all data must be accurate.",
            "start": "B. Syarat Peserta & Tim \n\nKetentuan Peserta",
            "end": "7. Seluruh data yang diberikan harus benar dan dapat dipertanggungjawabkan.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Syarat Peserta & Tim items 1-7.",
        },
        {
            "document_id": "DOC-051",
            "category": "registration_requirements",
            "name": "Registration Batches and Fees",
            "description": "Batch 1 (16-31 October 2026) costs Rp160.000,00/team; Batch 2 (1-19 November 2026) costs Rp180.000,00/team.",
            "start": "A. Periode & Biaya Pendaftaran \n\nPeriode Waktu Biaya Pendaftaran \n\nBatch 1 16–31 Oktober 2026 Rp160.000,00/tim \n\nBatch 2 1–19 November 2026 Rp180.000,00/tim",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_table",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Registration periods and fees table.",
        },
        {
            "document_id": "DOC-051",
            "category": "registration_requirements",
            "name": "Online Registration Mechanism, Social Media Follow, and Twibbon",
            "description": "Online registration via Google Form requires filling participant data, assigning leader/members, selecting 1 main SDG subtheme, paying fee, following @miladtiuir and @technofestuir (with proof), and uploading official Twibbon on non-private Instagram tagging both accounts with required caption (applies to ALL team members); committee verifies and grants WhatsApp group access.",
            "start": "C. Mekanisme Pendaftaran \n\nPendaftaran dilakukan secara daring melalui Google Form Pendaftaran yang",
            "end": "3. Jika terdapat data yang belum sesuai, panitia akan menghubungi ketua tim untuk \n\nmelakukan perbaikan.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Full registration steps and verification flow.",
        },
        {
            "document_id": "DOC-051",
            "category": "competition_structure",
            "name": "Theme and Four SDG Subthemes",
            "description": "Theme is 'Technology for Sustainable Impact'; each team must select 1 main subtheme from SDG 3 (Good Health and Well-Being), SDG 4 (Quality Education), SDG 8 (Decent Work and Economic Growth), or SDG 11 (Sustainable Cities and Communities).",
            "start": "B. Tema & Subtema Lomba \n\nHackathon Web Innovation Milad IT Fest 19 mengusung tema “Technology for",
            "end": "bukan jenis aplikasi atau teknologi yang digunakan.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Competition theme and mandatory single-subtheme selection rule.",
        },
        {
            "document_id": "DOC-051",
            "category": "competition_structure",
            "name": "Competition Stages and Schedule",
            "description": "Schedule: Registration Batch 1 (16-31 Oct 2026), Batch 2 (1-19 Nov 2026), Proposal Deadline (19 Nov 2026), Screening (20-27 Nov 2026), Finalist Announcement (28 Nov 2026 via IG), Finalist Prep (28 Nov - 4 Dec 2026), Mandatory Technical Meeting (29 Nov 2026), Hackathon Day offline at Aula Gedung A FT UIR (5 Dec 2026), Pitching & Demo offline (6 Dec 2026), Seminar Nasional & Awarding (10 Dec 2026).",
            "start": "D. Alur Kompetisi \n\nPeriode Agenda",
            "end": "Seminar Nasional & Awarding \n10 Desember 2026 Seminar Nasional serta pengumuman dan penghargaan \n\npemenang.",
            "nature": "schedule_milestone",
            "evidence_type": "explicit_schedule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Complete competition flow and timeline.",
        },
        {
            "document_id": "DOC-051",
            "category": "competition_structure",
            "name": "Finalist Mandatory Participation and Core Principle",
            "description": "Core principle is 'Prepare the Blueprint, Build on Hackathon Day': conceptual/design prep is allowed beforehand, but functional Web Application development starts only on Hackathon Day; finalists must attend Technical Meeting (29 Nov 2026), Hackathon Day, and Pitching & Demo.",
            "start": "Prinsip Utama Kompetisi \n\nPrepare the Blueprint, Build on Hackathon Day.",
            "end": "Namun, pengembangan Web Application untuk proyek kompetisi baru dimulai pada \n\nHackathon Day.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Core competition principle separating blueprint prep from Hackathon Day coding.",
        },
        {
            "document_id": "DOC-051",
            "category": "deliverables",
            "name": "Proposal Content, Formatting, and Submission",
            "description": "Registered teams submit 1 PDF proposal (<NamaTim>_Proposal_Hackathon.pdf) via official link; A4, Times New Roman 12 pt, 1.5 spacing, 1-inch margins, max 10 text pages (excl. cover & wireframe/prototype appendix), containing 10 required sections (team identity, project title, subtheme, background/problem, target users, solution, SDG fit, impact, tech plan, initial product visualization).",
            "start": "Tahap Proposal & Seleksi \n\nA. Ketentuan Proposal",
            "end": "6. Proposal dikumpulkan melalui link Pengumpulan Proposal yang disediakan oleh panitia.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Covers proposal provisions, 10 required sections, formatting, naming, and submission link.",
        },
        {
            "document_id": "DOC-051",
            "category": "deliverables",
            "name": "Finalist Pre-Hackathon Product Blueprint",
            "description": "Before Hackathon Day, finalists are expected to prepare a non-functional product blueprint covering problem/goals, target users, user flow, wireframe/UI/UX, main features/priorities, system architecture, database design, tech stack, and implementation plan.",
            "start": "B. Blueprint Produk \n\nSebelum mengikuti Hackathon Day, setiap finalis diharapkan telah memiliki blueprint",
            "end": "Blueprint merupakan rancangan, bukan produk yang sudah berfungsi.",
            "nature": "procedural_rule",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Expected pre-Hackathon blueprint deliverable.",
        },
        {
            "document_id": "DOC-051",
            "category": "deliverables",
            "name": "Hackathon Day Final Deliverables (Web App, Pitch Deck, GitHub Repo)",
            "description": "Final deliverables: (1) Runnable and demonstrable Web Application performing main solution functions (mobile/PWA optional); (2) Pitch deck (unlimited slides, adjusted to time limit) with 7 required sections; (3) Source code in a GitHub repository accessible to committee/judges (committee account invited at start, regular commits/pushes during Hackathon Day).",
            "start": "C. Deliverables \n\n1. Produk final berupa Web Application yang dapat dijalankan dan didemonstrasikan serta",
            "end": "4. Informasi teknis mengenai format pengumpulan, batas waktu, dan ketentuan tambahan \n\nakan disampaikan pada Technical Meeting finalis.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Official Deliverables section C.1-C.4.",
        },
        {
            "document_id": "DOC-051",
            "category": "assessment_criteria",
            "name": "Proposal Screening Assessment Criteria",
            "description": "Proposal screening weights: Permasalahan 20%, Target Pengguna 10%, Solusi 20%, Kesesuaian SDG 10%, Inovasi 15%, Dampak 15%, Kelayakan 10% (Total 100%).",
            "start": "D. Screening Proposal \n\nSetiap proposal akan melalui proses screening",
            "end": "Total 100%",
            "occ": 1,
            "nature": "evaluation_criterion",
            "evidence_type": "explicit_rubric",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Proposal screening rubric table.",
        },
        {
            "document_id": "DOC-051",
            "category": "assessment_criteria",
            "name": "Hackathon Day & Pitching Assessment Criteria",
            "description": "Final judging weights: Permasalahan & Relevansi 20%, Kualitas Solusi 20%, Inovasi & Kreativitas 15%, UI/UX & Fungsionalitas 15%, Implementasi Teknologi 10%, Dampak & Kesesuaian SDG 10%, Pitching & Q&A 10% (Total 100%).",
            "start": "D. Penilaian \n\nAspek Penilaian Bobot Fokus Penilaian",
            "end": "pertanyaan dewan juri. \n\nTotal 100%",
            "nature": "evaluation_criterion",
            "evidence_type": "explicit_rubric",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Final Hackathon Day & Pitching rubric table.",
        },
        {
            "document_id": "DOC-051",
            "category": "technical_and_general_rules",
            "name": "Pre-Hackathon Development Prohibition and GitHub Verification",
            "description": "Finalists are strictly prohibited from building project-specific frontend, backend, connected DB, API, deployment, source code, functional prototype, or reusing prior projects before Hackathon Day; during Hackathon Day, teams must use GitHub, invite committee account, commit/push regularly, and stop coding when time ends.",
            "start": "Sebaliknya, finalis tidak diperbolehkan melakukan pengembangan proyek kompetisi \nsebelum Hackathon Day, termasuk:",
            "end": "menggunakan proyek yang telah dikembangkan sebelumnya sebagai dasar produk \n\nkompetisi.",
            "nature": "prohibition",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Pre-Hackathon coding prohibition.",
        },
        {
            "document_id": "DOC-051",
            "category": "technical_and_general_rules",
            "name": "GitHub Commit Monitoring and Verification",
            "description": "Teams must host source code on GitHub, invite the committee GitHub account at the start of Hackathon Day, commit and push regularly, and allow commit history and checkpoint inspections.",
            "start": "3. Finalis wajib menjaga riwayat pengembangan proyek selama Hackathon Day sebagai",
            "end": "melakukan pemeriksaan pada checkpoint yang telah ditentukan \n\nselama sesi Hackathon Day.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Hackathon Day verification rules.",
        },
        {
            "document_id": "DOC-051",
            "category": "technical_and_general_rules",
            "name": "AI Usage Policy, Originality, Plagiarism, and Sanctions",
            "description": "Original work required (no prior project reuse; third-party frameworks/APIs allowed per license); AI is optional and allowed for ideation/coding/debugging/docs/design (must be understood/explained, prohibited for project-specific dev before Hackathon Day); no external help, plagiarism, or manipulation; sanctions range from warning and score reduction to submission cancellation and disqualification; decisions are final.",
            "start": "Ketentuan Umum \n\nA. Originalitas dan Hak Kekayaan Intelektual",
            "end": "4. Keputusan panitia dan dewan juri terkait pelanggaran dan hasil kompetisi bersifat final.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Ketentuan Umum sections A-D.",
        },
        # =====================================================================
        # DOC-070: Pedoman EIC - PGTC 2026.txt (Energynovation Ideas Competition)
        # =====================================================================
        {
            "document_id": "DOC-070",
            "category": "eligibility_requirements",
            "name": "Individual Participation and Past Winner Exclusion",
            "description": "Participants compete individually; alumni Juara 1-3 of EIC 2025 are not permitted to participate in EIC 2026.",
            "start": "1.\u200b Peserta bersifat individu \n2.\u200b Alumni Juara 1–3 pada EIC 2025 tidak diperkenankan mengikuti EIC 2026.",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.A Syarat Peserta items 1-2.",
        },
        {
            "document_id": "DOC-070",
            "category": "eligibility_requirements",
            "name": "Active Undergraduate/Diploma Student Status and Degree Restriction",
            "description": "Participants must be active S1/D4 (max semester 8) or D3 (max semester 6) students registered in PD-Dikti, proven by an active student certificate (not on leave), and must never have held an S1/D4/D3 degree.",
            "start": "3.\u200b Peserta adalah mahasiswa aktif  Program Sarjana dan Diploma 4 (maksimal semester \n\ndelapan) atau Diploma 3 (maksimal semester enam)",
            "end": "4.\u200b Peserta adalah mahasiswa yang belum pernah memiliki gelar Sarjana (S1)/sarjana \nTerapan (D4)/Ahli Madya (D3).",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.A items 3-4.",
        },
        {
            "document_id": "DOC-070",
            "category": "eligibility_requirements",
            "name": "Official Institutional Assignment Letter and Quota Rules",
            "description": "Participants must attach an official assignment/recommendation letter from Department/Program Study, Faculty/Dean, or University (unlisted students cannot compete); max 1 paper per participant; unlimited participants per campus.",
            "start": "5.\u200b Peserta wajib melampirkan surat tugas atau surat rekomendasi resmi",
            "end": "8.\u200b Setiap kampus/universitas diperkenankan mengirimkan peserta tanpa batas jumlah.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.A items 5-8.",
        },
        {
            "document_id": "DOC-070",
            "category": "registration_requirements",
            "name": "Social Media Follow and Top 10 Twibbonize",
            "description": "Participants must follow Instagram (@pertamina, @pgtc.id) and TikTok (@pertamina, @pgtc.official); Top 10 finalists must use PGTC 2026 Twibbonize.",
            "start": "9.\u200b Peserta yang lolos ke tahap 10 besar  \n\na.\u200b Menggunakan Twibbonize PGTC 2026.",
            "end": "TikTok @pertamina dan @pgtc.official",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "event_shared",
            "status": "verified",
            "notes": "PGTC 2026 shared social media and Twibbonize obligations.",
        },
        {
            "document_id": "DOC-070",
            "category": "registration_requirements",
            "name": "Online Registration Data and Required Document Uploads",
            "description": "Registration on pgtc.id requires personal data (Full Name, NIM, active WhatsApp & Email, Institution) and uploading before deadline: assignment letter, active student certificate, full paper PDF with appendices, Instagram presentation video URL, signed anti-plagiarism statement (Rp10.000 materai), work usage consent form, and Turnitin similarity index sheet.",
            "start": "12.\u200bBerkas pendaftaran terdiri atas:",
            "end": "g.\u200b Lembar hasil pemeriksaan similarity index Turnitin",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.A item 12 full checklist.",
        },
        {
            "document_id": "DOC-070",
            "category": "competition_structure",
            "name": "Two-Stage Competition Mechanism (Preliminary & Final)",
            "description": "Two main stages: online Preliminary Round (document/paper/video submission, distributed to 5 independent judges with NDA, top 10 finalists selected) and offline Final Round (live presentation + Q&A and scientific poster/prototype exhibition).",
            "start": "B.\u200b  Mekanisme Kompetisi \n\nKompetisi ini dilaksanakan melalui dua tahap seleksi utama: Babak Penyisihan",
            "end": "hanya 10 peserta terbaik yang akan lolos ke Babak Final \ndan diundang secara langsung untuk berkompetisi di hadapan dewan juri.",
            "nature": "procedural_rule",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.B overview and Preliminary selection.",
        },
        {
            "document_id": "DOC-070",
            "category": "competition_structure",
            "name": "Final Round Presentation & Q&A Timing",
            "description": "Final Round includes live presentation (10 minutes) and Q&A session (15 minutes per Bab II.B.2 vs 30 minutes per Bab II.G.2.b), plus scientific poster/prototype exhibition.",
            "start": "a)\u200b Presentasi langsung di hadapan Dewan Juri selama 10 menit dan sesi \n\ntanya-jawab selama 15 menit.",
            "end": None,
            "nature": "procedural_rule",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "ambiguous_needs_review",
            "notes": "Internal conflict: Bab II.B.2.b.a states 15 min Q&A, whereas Bab II.G.2.b.b states 30 min Q&A.",
        },
        {
            "document_id": "DOC-070",
            "category": "competition_structure",
            "name": "Competition Themes and Seven Subthemes",
            "description": "General theme: 'Accelerating Dual Growth Strategy: Integrating Energy Security and Low-Carbon Innovation'. Papers must pick 1 of 7 subthemes (a. Delivering Energy Security by Optimizing and Transforming Legacy Business, b. Developing Low Carbon Business for Energy Transition, c. Investment Strategy for Renewable Energy and Green Technology, d. Creating New Markets/Ecosystems/Value Chains, e. Digitalization/Innovation/Disruptive Business Models, f. Policy Incentives & Regulatory Frameworks, g. Social-Economic-Workforce Transition Impacts).",
            "start": "C.\u200b Tema Karya Tulis \n1.\u200b Tema Umum",
            "end": "menyeimbangkan tujuan lingkungan dengan stabilitas sosial dan ekonomi.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Theme and mandatory single-subtheme selection rule.",
        },
        {
            "document_id": "DOC-070",
            "category": "competition_structure",
            "name": "EIC PGTC 2026 Timeline",
            "description": "Timeline: Open Call (21 May 2026), Registration (21 May - 21 Jul 2026), Submission Deadline (21 Jul 2026), Seleksi Karya 1 (2-15 Aug 2026), Seleksi Karya 2 (22-31 Aug 2026), Top 10 Finalist Announcement (1 Sep 2026), Offline Technical Meeting (5 Sep 2026), Coaching Clinic (8-9 Sep 2026), Final & Awarding (17 Sep 2026).",
            "start": "I.\u200b Lini Masa \n\nWaktu Kegiatan",
            "end": "17 September 2026 Babak Final & Awarding",
            "nature": "schedule_milestone",
            "evidence_type": "explicit_schedule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.I complete timeline table.",
        },
        {
            "document_id": "DOC-070",
            "category": "deliverables",
            "name": "Scientific Paper Formatting, Length, and Naming",
            "description": "Full paper in English, 10-20 pages (excl. cover, bibliography, appendices), A4, margins 4 cm left / 3 cm top-right-bottom, 1.5 spacing, Times New Roman 12 pt, Justify, PDF max 5 MB, filename Namapenulis_Universitas_JudulSingkat_PGTC2026.pdf, APA Style references, signed anti-plagiarism (Rp10.000 materai), usage consent, and Turnitin similarity check.",
            "start": "D.\u200b Ketentuan Penulisan \n1.\u200b Teknis Penulisan (writing mechanics)",
            "end": "d)\u200b Lembar hasil pemeriksaan similarity index Turnitin",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.D writing mechanics, structure (Abstract max 250w, Intro <=20%, Method <=10%, Lit Review <=15%, Results & Discussion <=45%, Conclusion <=5%), and appendices.",
        },
        {
            "document_id": "DOC-070",
            "category": "deliverables",
            "name": "Presentation Video Specifications and Instagram Submission",
            "description": "Mandatory 3-minute English video, Landscape 16:9, min 1080p HD, using provided frame, covering title/author, subtheme, background, general idea, impact, closing; uploaded publicly on participant Instagram with required naming format, hashtags, and copyright caption; URL submitted with paper.",
            "start": "E.\u200b Ketentuan Video \n\n1. Ketentuan Isi Video",
            "end": "tanpa izin dari pemilik \nhak cipta”",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.E complete video content, technical specs, hashtags, and caption requirements.",
        },
        {
            "document_id": "DOC-070",
            "category": "deliverables",
            "name": "Final Round Exhibition Poster and Prototype Display",
            "description": "All finalists must exhibit A1 portrait poster (59.4 x 84.1 cm) summarizing problem/solution/benefits with visuals and no external sponsor logos, and optional prototype/model fitting booth space.",
            "start": "3. Mekanisme display karya \n\nUntuk memastikan partisipasi yang lancar",
            "end": "disesuaikan dengan ruang dan \nkapasitas tempat pameran.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_checklist",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.G.3 poster & prototype exhibition deliverables.",
        },
        {
            "document_id": "DOC-070",
            "category": "assessment_criteria",
            "name": "Preliminary Round Assessment Components and Paper Rubric",
            "description": "Preliminary components: Karya Tulis 100% (Originalitas ide & kebaruan solusi 25%, Ketajaman analisis & argumentasi ilmiah 25%, Kesesuaian tema & subtema 10%, Relevansi data & keakuratan metodologi 15%, Struktur penulisan & sistematika karya 25%), plus Video Presentasi as mandatory prerequisite (ungraded submissions without video are not assessed).",
            "start": "F.\u200b Penilaian Babak Penyisihan \n\n1. Komponen Penilaian",
            "end": "Total 100%",
            "nature": "evaluation_criterion",
            "evidence_type": "explicit_rubric",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Preliminary scoring weights and mandatory video prerequisite.",
        },
        {
            "document_id": "DOC-070",
            "category": "assessment_criteria",
            "name": "Final Round Assessment Components and Weights",
            "description": "Final Round is evaluated by 5 expert judges: Presentasi dan Tanya Jawab (60% — clarity/structure, mastery/argumentation, Q&A relevance, communication) and Pameran/Eksibisi Karya (40% — visual appeal/neatness, clarity of info, visitor interaction, innovation/benefit).",
            "start": "b. Komponen Penilaian Akhir",
            "end": "i)\u200b Juri mengevaluasi finalis menggunakan rubrik penilaian komprehensif",
            "nature": "evaluation_criterion",
            "evidence_type": "explicit_rubric",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.G.2.b Final Round 60%/40% weighting (detailed sub-aspects in Lampiran 4).",
        },
        {
            "document_id": "DOC-070",
            "category": "technical_and_general_rules",
            "name": "Disqualification Rules (Plagiarism, Late Submission, Improper Content, Format)",
            "description": "Disqualification applies for plagiarism (including self/auto-plagiarism), late submission without official notice, improper content (hate speech, SARA, partisan politics, discrimination), or non-compliance with writing guidelines; incomplete/non-compliant papers or missing video are not graded; jury decisions are final.",
            "start": "6. Ketentuan Larangan dan Diskualifikasi",
            "end": "saluran media sosial Pertamina Goes to Campus.",
            "nature": "prohibition",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.F.6-7 prohibitions and finality.",
        },
        {
            "document_id": "DOC-070",
            "category": "technical_and_general_rules",
            "name": "Finalist Dress Code and Exhibition Safety Prohibitions",
            "description": "Finalists must dress neatly and wear institutional almamater jacket; exhibition strictly prohibits heating elements, fire, high-pressure devices/containers, flammable/corrosive/toxic materials, strobe lights, weapons, live animals, sharp unwrapped tools, or smoke/odor/vapor emitters.",
            "start": "c.  Ketentuan peserta: \n\na)\u200b Peserta wajib menjunjung etika, sopan santun, dan profesionalisme \nb)\u200b Peserta wajib berpakaian rapi dan mengenakan jaket/jas almamater",
            "end": "institusinya selama kegiatan",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Finalist ethics & almamater dress code.",
        },
        {
            "document_id": "DOC-070",
            "category": "technical_and_general_rules",
            "name": "Prototype Exhibition Safety Prohibitions",
            "description": "Heating elements, fire, high-pressure devices, flammables, corrosives, toxics, strobe lights, weapons, live animals, aerosol/gas tanks, unwrapped sharp tools, and smoke/odor/vapor items are strictly prohibited at the exhibition booth.",
            "start": "iii)\u200b Elemen pemanas, api, atau perangkat bertekanan tinggi dilarang",
            "end": "mengeluarkan asap, bau, atau uap.",
            "nature": "prohibition",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Bab II.G.3.a.b safety prohibitions.",
        },
        {
            "document_id": "DOC-070",
            "category": "technical_and_general_rules",
            "name": "Copyright, Non-Exclusive License to Pertamina, and Withdrawal Policy",
            "description": "Participants retain copyright but grant PT Pertamina (Persero) a non-exclusive, non-commercial license for education, promotion, publication, and documentation; commercial use requires written consent; submitted works cannot be withdrawn without written committee approval.",
            "start": "H.\u200b Ketentuan Hak Cipta dan Kepemilikan Karya",
            "end": "5.\u200b Penarikan Karya \nSetelah karya dikirimkan dan masuk dalam proses seleksi, peserta tidak dapat \nmenarik kembali karya tanpa alasan yang dapat diterima secara tertulis dan disetujui \noleh panitia.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "event_shared",
            "status": "verified",
            "notes": "PGTC 2026 / Pertamina IP and withdrawal policy.",
        },
        # =====================================================================
        # DOC-053: Guidebook_Wreck_IT_7.0.txt (WRECK-IT 7.0: CTF & Hackathon)
        # Note: Stage 3 placed entire document under DOC-053-BU-01 (BR_CYBERSECURITY_CTF).
        # =====================================================================
        {
            "document_id": "DOC-053",
            "category": "eligibility_requirements",
            "name": "General WRECK-IT 7.0 Participant Exclusions and Single-Team Rule",
            "description": "Participants must not be WRECK-IT 7.0 committee members, must not be Juara 1 WRECK-IT 6.0 winners (stated in CTF section), and may only register in 1 team.",
            "start": "5. Peserta bukan merupakan panit ia WRECK-IT 7.0.\n6. Peserta bukan pemenang Juara 1  WRECK-IT 6.0.\n7 . Set iap peserta hanya boleh terdaftar pada satu t im.",
            "end": None,
            "nature": "prohibition",
            "evidence_type": "explicit_rule",
            "scope": "event_shared",
            "status": "verified",
            "notes": "CTF D.5-7 (Hackathon D.5-6 repeats non-committee & 1-team rule, omits Juara 1 WRECK-IT 6.0 exclusion).",
        },
        {
            "document_id": "DOC-053",
            "category": "eligibility_requirements",
            "name": "General CTF Eligibility and Team Size",
            "description": "General CTF participants must be Indonesian citizens (proven by scanned KTP/SIM/Passport/Student Card), in teams of 1-3 members, not problem authors, and verified without member substitution.",
            "start": "F. KETENTUAN LOMBA GENERAL CTF",
            "end": "tidak dapat digantikan oleh orang la in selama kompetis i\nberlangsung.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Applies specifically to General CTF branch inside DOC-053-BU-01.",
        },
        {
            "document_id": "DOC-053",
            "category": "eligibility_requirements",
            "name": "Junior CTF Eligibility and Team Size",
            "description": "Junior CTF participants must be Indonesian citizens (KTP/SIM/Passport/Student Card) who are SMA/SMK/equivalent students, in teams of 1-3 members, not problem authors, and verified without member substitution.",
            "start": "I .  KETENTUAN LOMBA JUNIOR CTF",
            "end": "tidak dapat digantikan oleh orang la in selama kompetis i\nberlangsung.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Applies specifically to Junior CTF branch inside DOC-053-BU-01.",
        },
        {
            "document_id": "DOC-053",
            "category": "eligibility_requirements",
            "name": "Hackathon Eligibility and Team Size",
            "description": "Hackathon participants must be Indonesian citizens (KTP/SIM/Passport/Student Card) in teams of 3-5 members, verified without member substitution.",
            "start": "F. KETENTUAN LOMBA HACKATHON",
            "end": "tidak dapat digantikan oleh orang la in selama kompetis i\nberlangsung.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "ambiguous_needs_review",
            "notes": "Internal conflict in Hackathon section: Pendahuluan states 'baik individu maupun tim', whereas F.3 requires 'minimal tiga orang dan paling banyak lima orang'. Also Stage 3 bundled Hackathon inside BR_CYBERSECURITY_CTF BU.",
        },
        {
            "document_id": "DOC-053",
            "category": "registration_requirements",
            "name": "WRECK-IT 7.0 Registration Portal, Social Media, and Verification",
            "description": "Registration on https://wreckit.id/ (1 May - 14 June 2026) requires team leader to fill member data and upload combined archive of registration documents; email verification within 1x24h; verified teams cannot change data/composition; participants must follow @poltekssn, @korpstar.poltekssn, and @wreckit.id on Instagram and re-register before competition starts.",
            "start": "D. SYARAT DAN KETENTUAN\n\n1 . Peserta telah mengikuti  mekanisme registrasi  pada website\nresmi WRECK-IT 7.0 di  https://wreckit . id/",
            "end": "4. Peserta waj ib menyelesaikan pengunggahan berkas\nadministrasi  sebelum tahap registrasi  ditutup.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "event_shared",
            "status": "verified",
            "notes": "Shared across CTF and Hackathon in WRECK-IT 7.0.",
        },
        {
            "document_id": "DOC-053",
            "category": "registration_requirements",
            "name": "Registration Mechanism and Lock-In After Verification",
            "description": "During 1 May - 14 June 2026, team leader submits member data and combined archive on https://wreckit.id/; receives verification email within 1x24 hours; verified teams cannot modify data or team lineup.",
            "start": "E. MEKANISME REGISTRASI",
            "end": "6. Tim yang telah terveri f ikasi  t idak diperbolehkan\nmengubah data ataupun mengganti  susunan t im.",
            "occ": 1,
            "nature": "procedural_rule",
            "evidence_type": "explicit_rule",
            "scope": "event_shared",
            "status": "verified",
            "notes": "Identical registration mechanism in CTF E.1-6 and Hackathon E.1-6.",
        },
        {
            "document_id": "DOC-053",
            "category": "competition_structure",
            "name": "CTF Two-Stage Structure (Jeopardy Prelim & Attack/Defense Final) and Finalist Quota",
            "description": "CTF has online Jeopardy Preliminary (20 June 2026, ~8h, scoreboard frozen 1h before end, TM 19 June 2026) and on-site Final (8 July 2026, ~6h) using Attack/Defense (with Jeopardy per Pendahuluan). Pendahuluan states 7 teams enter Final, while G.9/J.9 state 10 teams advance.",
            "start": "Kompetisi CTF terbagi menjadi dua babak, yaitu babak\npenyisihan dan babak final.",
            "end": "diamankan tim pembawa flag sampai mendapatkannya.",
            "nature": "procedural_rule",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "ambiguous_needs_review",
            "notes": "Internal conflict: Pendahuluan mentions 7 teams in Final, whereas G.9 (General CTF) and J.9 (Junior CTF) state 10 teams advance to Final.",
        },
        {
            "document_id": "DOC-053",
            "category": "competition_structure",
            "name": "CTF Timeline",
            "description": "CTF Timeline: Registration & Training open 1 May 2026, Training & Registration close 14 June 2026, Prelim TM 19 June 2026 (online), CTF Prelim 20 June 2026 (online), Final TM 1 July 2026 (online), CTF Final 8 July 2026 (offline), Seminar & Awarding 8 July 2026 (offline).",
            "start": "C. TIMELINE\n \n\nTIMELINE TANGGAL\n\nPembukaan Registrasi CTF",
            "end": "Seminar dan Awarding (luring) 8 Juli 2026",
            "nature": "schedule_milestone",
            "evidence_type": "explicit_schedule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "CTF timeline table.",
        },
        {
            "document_id": "DOC-053",
            "category": "competition_structure",
            "name": "Hackathon Two-Stage Structure and Timeline",
            "description": "Hackathon has online Preliminary (proposal, video, GitHub submission deadline 14 June 2026; judging 15-20 June 2026; top 5 finalists announced 21 June 2026) and on-site Final (8 July 2026: 3h app finalization + ~3h presentation; Final TM 1 July 2026; Seminar & Awarding 8 July 2026).",
            "start": "C. TIMELINE\n \n\nTIMELINE TANGGAL\n\nPembukaan Registrasi Hackathon",
            "end": "Seminar dan Awarding (luring) 8 Juli 2026",
            "occ": 1,
            "nature": "schedule_milestone",
            "evidence_type": "explicit_schedule",
            "scope": "branch_specific",
            "status": "ambiguous_needs_review",
            "notes": "Hackathon section inside DOC-053-BU-01; note typo '1 Juli 2-26' for Final TM.",
        },
        {
            "document_id": "DOC-053",
            "category": "deliverables",
            "name": "General CTF and Junior CTF Preliminary Write-Up Deliverable",
            "description": "Every CTF team must submit a write-up via the provided form within 8 hours after Preliminary ends (21 June 2026 max 14.30 WIB per rundown), following format links https://s.id/WriteupwreckitGeneral (General) and https://s.id/WriteupwreckitJunior (Junior).",
            "start": "6. Setiap t im waj ib mengumpulkan write-up dengan\nbeberapa ketentuan,  yakni :\n\n    a .Pengumpulan write-up pal ing lambat 8 jam setelah\n       selesainya babak penyis ihan.\n    b .Write-up dikumpulkan pada formul ir  yang disediakan\n    c .Ketentuan format pengumpulan write-up dapat diakses  \n       pada tautan https://s . id/WriteupwreckitGeneral",
            "end": None,
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "CTF write-up deliverable (General link shown; Junior link at J.6.c).",
        },
        {
            "document_id": "DOC-053",
            "category": "deliverables",
            "name": "Hackathon Preliminary Deliverables (Proposal, Video, GitHub Repo) and Final Presentation",
            "description": "Hackathon teams submit a proposal, explanation video, and GitHub repository by 14 June 2026; top 5 finalists finalize their application in 3 hours on Final day and deliver a final presentation.",
            "start": "Peserta, baik individu\nmaupun tim, diminta untuk menyampaikan ide dan karya\nkreatif melalui pengumpulan proposal, video penjelasan, dan\nrepository GitHub sebagai dokumentasi implementasi solusi.",
            "end": "Setelah\naplikasi selesai, tim final akan melakukan presentasi final untuk\nmemaparkan solusi, inovasi, dan implementasi karya mereka.",
            "nature": "mandatory_requirement",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Hackathon deliverables inside DOC-053-BU-01.",
        },
        {
            "document_id": "DOC-053",
            "category": "assessment_criteria",
            "name": "CTF Preliminary, Final, and Best Write-Up Evaluation",
            "description": "CTF Prelim winner/advancement is based on highest Jeopardy points + valid write-up + zero violations; Final is scored by flags captured and duration of flag defense across rounds; Best Write-up is selected by jury; decisions are final.",
            "start": "Pemenang ditentukan oleh tim yang paling banyak merebut\nflag dari tim lain serta yang dapat paling lama mengamankan\nflag ketika tim tersebut mendapatkan flag-nya.",
            "end": None,
            "nature": "evaluation_criterion",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Explicit numeric weights are not stated; scoring mechanism is stated.",
        },
        {
            "document_id": "DOC-053",
            "category": "assessment_criteria",
            "name": "Hackathon Final Presentation Evaluation Aspects",
            "description": "Hackathon winners are determined based on final presentation assessment considering creativity, solution effectiveness, relevance to theme, and quality of idea delivery (numeric weights not stated).",
            "start": "Penentuan pemenang dilakukan berdasarkan penilaian\npresentasi, dengan mempertimbangkan aspek kreativitas,\nefektivitas solusi, relevansi terhadap tema, dan kualitas\npenyampaian gagasan.",
            "end": None,
            "nature": "evaluation_criterion",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Hackathon qualitative judging aspects (no numeric weights stated).",
        },
        {
            "document_id": "DOC-053",
            "category": "technical_and_general_rules",
            "name": "CTF Preliminary Prohibitions (DDoS, Disruption, Account Sharing, Flag Sharing)",
            "description": "During CTF Preliminary, participants are prohibited from DDoS against servers, disrupting other participants/committee, collaborating with non-registered parties, sharing accounts outside the team, or sharing flags/cheating.",
            "start": "8 . Terdapat beberapa larangan selama babak penyis ihan\nberlangsung,  yaitu:\na . Melakukan DdoS terhadap server.",
            "end": "berbagi f lag atau melakukan t indakan-t indakan\nkecurangan la innya.",
            "occ": 1,
            "nature": "prohibition",
            "evidence_type": "explicit_rule",
            "scope": "branch_specific",
            "status": "verified",
            "notes": "Identical technical prohibitions appear in both General CTF (G.8) and Junior CTF (J.8).",
        },
        {
            "document_id": "DOC-053",
            "category": "technical_and_general_rules",
            "name": "Mandatory Finalist Attendance, Cheating Sanctions, and Rule Amendments",
            "description": "Finalists must confirm attendance and attend awarding/seminar (or be disqualified); cheating or disruption leads to disqualification and prize/title revocation; committee may amend guidebook rules at any time via email/website.",
            "start": "10. Peserta di larang melakukan kecurangan dalam bentuk apapun\n\ndan menimbulkan gangguan yang disengaja untuk merugikan\npanit ia dan/atau peserta la in .",
            "end": "Segala perubahan yang ter jadi  akan disampaikan melalui  e-mai l\ndan/atau website.",
            "occ": 1,
            "nature": "prohibition",
            "evidence_type": "explicit_rule",
            "scope": "event_shared",
            "status": "verified",
            "notes": "Shared WRECK-IT 7.0 disciplinary, attendance, and amendment rules (CTF D.10-15, repeated in Hackathon D.8-13).",
        },
    ]
    return specs


def main() -> None:
    specs = build_raw_annotations()
    raw_texts: dict[str, str] = {}
    for doc_id, meta in DOC_METADATA.items():
        path = RAW_TXT_DIR / meta["filename"]
        raw_texts[doc_id] = path.read_text(encoding="utf-8")

    per_doc_counter: Counter[str] = Counter()
    records: list[dict[str, Any]] = []

    for spec in specs:
        doc_id = spec["document_id"]
        meta = DOC_METADATA[doc_id]
        raw_text = raw_texts[doc_id]
        occ = spec.get("occ", 1)
        min_pos = meta["unit_char_start"]

        char_start, char_end, evidence_text = find_exact_span(
            raw_text,
            spec["start"],
            spec.get("end"),
            occurrence=occ,
            min_pos=min_pos,
        )

        # Verify exact substring invariant
        assert raw_text[char_start:char_end] == evidence_text, (
            f"Mismatch in {doc_id}: {spec['name']}"
        )
        assert char_start >= meta["unit_char_start"] and char_end <= meta["unit_char_end"], (
            f"Span out of branch unit range for {doc_id}: {char_start}..{char_end}"
        )
        assert spec["category"] in ALLOWED_CATEGORIES
        assert spec["scope"] in ALLOWED_SCOPE_LEVELS
        assert spec["status"] in ALLOWED_ANNOTATION_STATUSES

        per_doc_counter[doc_id] += 1
        ann_id = f"GT-{doc_id}-{per_doc_counter[doc_id]:03d}"

        source_page = (
            infer_pgtc_page(raw_text, char_start) if meta["has_page_numbers"] else None
        )

        record = {
            "annotation_id": ann_id,
            "document_id": doc_id,
            "branch_unit_id": meta["branch_unit_id"],
            "requirement_category": spec["category"],
            "requirement_name": spec["name"],
            "requirement_description": spec["description"],
            "evidence_text": evidence_text,
            "source_char_start": char_start,
            "source_char_end": char_end,
            "source_page": source_page,
            "statement_nature": spec["nature"],
            "evidence_type": spec["evidence_type"],
            "scope_level": spec["scope"],
            "annotation_status": spec["status"],
            "annotator_notes": spec["notes"],
        }
        for field in REQUIRED_FIELDS:
            assert field in record, f"Missing required field {field}"
        records.append(record)

    # Check duplicate / overlapping spans within same document
    overlaps: list[dict[str, Any]] = []
    by_doc: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        by_doc.setdefault(rec["document_id"], []).append(rec)

    for doc_id, doc_recs in by_doc.items():
        sorted_recs = sorted(doc_recs, key=lambda r: (r["source_char_start"], r["source_char_end"]))
        for i in range(len(sorted_recs) - 1):
            a, b = sorted_recs[i], sorted_recs[i + 1]
            if a["source_char_end"] > b["source_char_start"]:
                overlaps.append(
                    {
                        "document_id": doc_id,
                        "ann_a": a["annotation_id"],
                        "ann_b": b["annotation_id"],
                        "span_a": [a["source_char_start"], a["source_char_end"]],
                        "span_b": [b["source_char_start"], b["source_char_end"]],
                    }
                )

    assert not overlaps, f"Overlapping spans detected: {overlaps}"

    # Build summary statistics
    cat_counts = Counter(r["requirement_category"] for r in records)
    scope_counts = Counter(r["scope_level"] for r in records)
    status_counts = Counter(r["annotation_status"] for r in records)

    gt_payload = {
        "stage": "4.4",
        "artifact_type": "blind_held_out_ground_truth",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_documents": len(DOC_METADATA),
        "total_annotations": len(records),
        "documents": {
            doc_id: {
                "filename": meta["filename"],
                "branch_unit_id": meta["branch_unit_id"],
                "branch_code": meta["branch_code"],
                "unit_char_range": [meta["unit_char_start"], meta["unit_char_end"]],
                "annotation_count": per_doc_counter[doc_id],
                "expected_not_stated_categories": meta["expected_not_stated_categories"],
            }
            for doc_id, meta in DOC_METADATA.items()
        },
        "summary_counts": {
            "by_document": dict(per_doc_counter),
            "by_category": dict(cat_counts),
            "by_scope_level": dict(scope_counts),
            "by_annotation_status": dict(status_counts),
        },
        "annotations": records,
    }

    gt_path = PROCESSED_DIR / "stage_4_4_blind_held_out_ground_truth.json"
    gt_json_bytes = (json.dumps(gt_payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    gt_path.write_bytes(gt_json_bytes)

    gt_file_sha256 = hashlib.sha256(gt_json_bytes).hexdigest()
    annotations_canonical_sha256 = hashlib.sha256(
        json.dumps(records, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    freeze_payload = {
        "stage": "4.4",
        "artifact_type": "ground_truth_freeze_manifest",
        "freeze_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_status": "GROUND_TRUTH_FROZEN_WITH_LIMITATIONS",
        "ground_truth_file": str(gt_path.relative_to(BASE_DIR)),
        "ground_truth_file_sha256": gt_file_sha256,
        "annotations_canonical_sha256": annotations_canonical_sha256,
        "total_documents": len(DOC_METADATA),
        "total_annotations": len(records),
        "validation_checks": {
            "exact_char_span_match_all_passed": True,
            "branch_unit_bounds_all_passed": True,
            "required_fields_all_present": True,
            "zero_overlapping_or_duplicate_spans": len(overlaps) == 0,
            "used_old_extractor_or_generic_parser": False,
        },
        "counts_summary": gt_payload["summary_counts"],
        "limitations": [
            "DOC-053 (Guidebook_Wreck_IT_7.0.txt) was segmented in Stage 3 as a single branch unit DOC-053-BU-01 (BR_CYBERSECURITY_CTF), even though the raw document contains both CTF (General & Junior) and Hackathon technical guides.",
            "Internal document inconsistencies were preserved as 'ambiguous_needs_review' rather than resolved by assumption (DOC-011 Prelim deadline Nov 8 vs Nov 15; DOC-017 Top 10 Finalis/Top 25 Semifinalis vs single-stage flow; DOC-070 Final Q&A 15 min vs 30 min; DOC-053 CTF 7 vs 10 finalists and Hackathon individual vs 3-5 team).",
            "Only DOC-070 includes printed page footers in the raw TXT; source_page is null for DOC-011, DOC-017, DOC-051, and DOC-053.",
        ],
    }

    freeze_path = PROCESSED_DIR / "stage_4_4_ground_truth_freeze.json"
    freeze_path.write_text(
        json.dumps(freeze_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {gt_path} ({len(records)} annotations across {len(DOC_METADATA)} docs)")
    print(f"Wrote {freeze_path}")
    print(f"GT File SHA-256: {gt_file_sha256}")
    print(f"Annotations Canonical SHA-256: {annotations_canonical_sha256}")
    print("By document:", dict(per_doc_counter))
    print("By category:", dict(cat_counts))
    print("By scope:", dict(scope_counts))
    print("By status:", dict(status_counts))


if __name__ == "__main__":
    main()
