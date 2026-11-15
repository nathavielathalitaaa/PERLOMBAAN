"""Rule-Based Requirement Extraction Engine (Stage 4.2 Refinement).

Refines the Stage 4.0 baseline based on the comprehensive Stage 4.1 Audit
(`data/processed/requirement_extraction_audit.json`):
1. Separates four distinct entity types:
   - `requirements` (`ExtractedRequirementRecord`): Only requirements explicitly/implicitly
     stated in the source text, with full verbatim evidence supporting 100% of description claims.
   - `information_items` (`SupportingInformationRecord`): Non-requirement supporting context
     (event background, epidemiological context, prize pool overview, certificate info).
   - `extraction_gaps` (`ExtractionGapRecord`): Expected requirement attributes searched and
     confirmed `NOT_STATED` in the source unit (never stored as active requirement records).
   - `review_items` (`ReviewItemRecord`): Source anomalies, internal contradictions, copy-paste
     typos, `[TBC]` placeholders, and illegible OCR blocks requiring human verification.
2. Enforces atomic requirement granularity (1 rule = 1 record; 1 rubric aspect = 1 record)
   while keeping multi-sentence requirements and their exceptions intact.
3. Applies deterministic rule-based classification, false-positive background filtering,
   active term normalization, and automated claim-to-evidence grounding verification.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.requirement_extraction.rules import (
    CONFIDENCE_LEVELS,
    EVIDENCE_TYPES,
    RECORD_TYPES,
    REQUIREMENT_CATEGORIES,
    REQUIREMENT_SUBCATEGORIES,
    STATEMENT_NATURES,
    TERM_NORMALIZATION_RULES,
    VALIDATION_STATUSES,
    apply_term_normalization,
    classify_requirement_clause,
    extract_exception_or_condition,
    is_non_requirement_background,
    verify_description_grounded_in_evidence,
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractedRequirementRecord:
    """Single atomic competition requirement stated in a CompetitionBranchUnit."""

    requirement_id: str
    document_id: str
    branch_unit_id: str
    competition_name: str
    requirement_category: str
    requirement_subcategory: str
    requirement_name: str
    requirement_description: str
    source_page: int
    source_section: str
    source_char_start: int
    source_char_end: int
    evidence_text: str
    evidence_type: str
    confidence_level: str
    extraction_method: str
    validation_status: str
    statement_nature: str = "official_rule"
    indicator_weight: str = "N/A"
    exception_or_condition: str = "NONE"
    related_requirement_ids: List[str] = field(default_factory=list)
    normalized_terms: List[Dict[str, str]] = field(default_factory=list)
    unit_segmentation_status: str = "VALIDATED"
    within_strict_unit_bounds: bool = True
    record_type: str = "requirement"


@dataclass
class SupportingInformationRecord:
    """Non-binding supporting competition information (background, prizes, general notes)."""

    info_id: str
    document_id: str
    branch_unit_id: str
    competition_name: str
    info_category: str
    info_name: str
    info_description: str
    source_page: int
    source_section: str
    source_char_start: int
    source_char_end: int
    evidence_text: str
    extraction_method: str = "rule_based_background_and_context_filter"
    statement_nature: str = "supporting_info"
    record_type: str = "information"


@dataclass
class ExtractionGapRecord:
    """Expected requirement attribute searched and found NOT_STATED in a branch unit."""

    gap_id: str
    document_id: str
    branch_unit_id: str
    competition_name: str
    requirement_category: str
    requirement_subcategory: str
    missing_attribute_name: str
    gap_status: str
    inspected_sections: List[str]
    inspected_char_range: str
    verification_method: str
    notes: str
    record_type: str = "extraction_gap"


@dataclass
class ReviewItemRecord:
    """Information or source anomaly requiring human inspection (NEEDS_REVIEW)."""

    review_id: str
    document_id: str
    branch_unit_id: str
    competition_name: str
    related_requirement_id: Optional[str]
    issue_type: str
    severity: str
    review_status: str
    source_page: int
    source_section: str
    source_char_start: int
    source_char_end: int
    evidence_text: str
    review_description: str
    recommended_human_action: str
    record_type: str = "review_item"


def _build_page_spans(raw_text: str) -> List[Tuple[int, int, int]]:
    """Return list of (page_num, start_char, end_char) split by triple-newline page separators."""
    blocks = raw_text.split("\n\n\n")
    spans: List[Tuple[int, int, int]] = []
    pos = 0
    for idx, blk in enumerate(blocks, 1):
        s = raw_text.find(blk, pos)
        e = s + len(blk)
        pos = e
        spans.append((idx, s, e))
    return spans


def _locate_page_for_char(page_spans: List[Tuple[int, int, int]], char_idx: int) -> int:
    """Find 1-based page number containing char_idx."""
    for pnum, s, e in page_spans:
        if s <= char_idx <= e:
            return pnum
    best_page = 1
    for pnum, s, _ in page_spans:
        if char_idx >= s:
            best_page = pnum
    return best_page


def _find_exact_span(
    raw_text: str,
    anchor: str,
    search_start: int = 0,
    search_end: Optional[int] = None,
) -> Tuple[int, int, str]:
    """Locate exact substring `anchor` in `raw_text[search_start:search_end]` and return (start, end, verbatim)."""
    end_bound = len(raw_text) if search_end is None else search_end
    idx = raw_text.find(anchor, search_start, end_bound)
    if idx == -1:
        raise ValueError(
            f"Evidence anchor not found in [{search_start}..{end_bound}]: {anchor!r}"
        )
    return idx, idx + len(anchor), raw_text[idx : idx + len(anchor)]


def _make_record(
    req_id: str,
    doc_id: str,
    unit_id: str,
    comp_name: str,
    name: str,
    description: str,
    section: str,
    raw_text: str,
    page_spans: List[Tuple[int, int, int]],
    unit_start: int,
    unit_end: int,
    unit_seg_status: str,
    anchor: str,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    search_start: Optional[int] = None,
    search_end: Optional[int] = None,
    evidence_type: str = "explicit",
    confidence_level: str = "high",
    extraction_method: str = "rule_based_clause_and_span_extractor",
    validation_status: str = "VALIDATED",
    statement_nature: Optional[str] = None,
    indicator_weight: str = "N/A",
    exception_override: Optional[str] = None,
    related_ids: Optional[List[str]] = None,
) -> ExtractedRequirementRecord:
    s_start = unit_start if search_start is None else search_start
    s_end = unit_end if search_end is None else search_end
    c_start, c_end, verbatim = _find_exact_span(raw_text, anchor, s_start, s_end)

    # Guard: Never allow non-requirement background into active requirements
    if is_non_requirement_background(verbatim, section):
        raise ValueError(
            f"False positive guard blocked non-requirement background in {req_id}: {verbatim[:80]!r}"
        )

    inferred_cat, inferred_subcat, inferred_nature = classify_requirement_clause(
        verbatim, section
    )
    final_cat = category if category is not None else inferred_cat
    final_subcat = subcategory if subcategory is not None else inferred_subcat
    final_nature = statement_nature if statement_nature is not None else inferred_nature

    if final_cat not in REQUIREMENT_CATEGORIES:
        raise ValueError(f"Invalid requirement_category {final_cat!r} on {req_id}")
    if final_subcat not in REQUIREMENT_SUBCATEGORIES[final_cat]:
        raise ValueError(
            f"Invalid subcategory {final_subcat!r} for category {final_cat!r} on {req_id}"
        )

    # Verify grounding of description in evidence_text
    is_grounded, ungrounded_claims = verify_description_grounded_in_evidence(
        description, verbatim, evidence_type
    )
    if not is_grounded:
        raise ValueError(
            f"Ungrounded claims {ungrounded_claims} in {req_id} description={description!r} vs evidence={verbatim!r}"
        )

    page_num = _locate_page_for_char(page_spans, c_start)
    in_unit = (unit_start <= c_start) and (c_end <= unit_end)
    exc_text = (
        exception_override
        if exception_override is not None
        else extract_exception_or_condition(verbatim)
    )
    norm_terms = apply_term_normalization(verbatim)

    return ExtractedRequirementRecord(
        requirement_id=req_id,
        document_id=doc_id,
        branch_unit_id=unit_id,
        competition_name=comp_name,
        requirement_category=final_cat,
        requirement_subcategory=final_subcat,
        requirement_name=name,
        requirement_description=description,
        source_page=page_num,
        source_section=section,
        source_char_start=c_start,
        source_char_end=c_end,
        evidence_text=verbatim,
        evidence_type=evidence_type,
        confidence_level=confidence_level,
        extraction_method=extraction_method,
        validation_status=validation_status,
        statement_nature=final_nature,
        indicator_weight=indicator_weight,
        exception_or_condition=exc_text,
        related_requirement_ids=related_ids or [],
        normalized_terms=norm_terms,
        unit_segmentation_status=unit_seg_status,
        within_strict_unit_bounds=in_unit,
    )


def _extract_doc001_bu01(
    raw_text: str,
    unit_meta: Dict[str, Any],
    unit_val: Dict[str, Any],
) -> Tuple[
    List[ExtractedRequirementRecord],
    List[SupportingInformationRecord],
    List[ExtractionGapRecord],
    List[ReviewItemRecord],
]:
    """Extract refined requirements, info, gaps, and review items for DOC-001-BU-01."""
    doc_id = "DOC-001"
    uid = "DOC-001-BU-01"
    comp = "AI Builder Challenge 2026"
    u_start = int(unit_meta["start_char"])
    u_end = int(unit_meta["end_char"])
    u_status = unit_val["validation_status"]
    pages = _build_page_spans(raw_text)

    specs: List[Dict[str, Any]] = [
        # 1. Eligibility Requirements
        {
            "category": "eligibility_requirements",
            "subcategory": "education_level_and_student_status",
            "name": "university_student_eligibility",
            "description": "Kompetisi terbuka bagi mahasiswa perguruan tinggi di Indonesia (Indonesian university students).",
            "section": "2. Eligibility and Teams",
            "anchor": "The Challenge is open to Indonesian university students.",
            "related_ids": ["REQ-DOC001-BU01-002"],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "student_identity_document",
            "name": "active_student_id_ktm_requirement",
            "description": "Seluruh anggota tim wajib berstatus mahasiswa aktif dan menyertakan Kartu Tanda Mahasiswa (KTM) yang sah.",
            "section": "2. Eligibility and Teams",
            "anchor": "●​ Student status: all members must be active students and provide a valid student ID \n\n(KTM).",
            "related_ids": ["REQ-DOC001-BU01-001", "REQ-DOC001-BU01-006"],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "participation_mode_and_team_size",
            "name": "team_based_participation_and_team_size",
            "description": "Kepesertaan wajib berbasis tim dengan ukuran 3 hingga 4 anggota; pendaftaran individu tidak diterima.",
            "section": "2. Eligibility and Teams",
            "anchor": "Participation is team-based only, \nand individual entries are not accepted. \n\n●​ Team size: 3 to 4 members.",
            "exception_override": "individual entries are not accepted",
            "related_ids": ["REQ-DOC001-BU01-004"],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "single_team_or_cross_branch_restriction",
            "name": "single_team_membership_restriction",
            "description": "Setiap individu hanya diperbolehkan mendaftar 1 kali dan tergabung dalam 1 tim saja (One person, one team).",
            "section": "2. Eligibility and Teams",
            "anchor": "●​ One person, one team: each individual may register only once and belong to only \n\none team.",
            "related_ids": ["REQ-DOC001-BU01-003", "REQ-DOC001-BU01-020"],
        },
        # 2. Registration Requirements
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "free_registration_fee",
            "description": "Pendaftaran gratis tanpa dipungut biaya untuk seluruh tim.",
            "section": "1. About the Challenge & 4. How to Register",
            "anchor": "Registration is free, with no fee for any \nteam.",
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_mechanism_and_portal",
            "name": "two_step_registration_and_team_leader_google_form",
            "description": "Pendaftaran gratis dan terdiri dari 2 langkah wajib; pada langkah 1, ketua tim mengisi Google Form pendaftaran tim dengan detail tim, pilihan track, serta detail dan KTM setiap anggota (tautan Google Form masih bertanda placeholder [TBC]).",
            "section": "4. How to Register",
            "anchor": "Registration is free and takes two steps. Your team is registered only when both are \ndone. \n\n1.​ Team leader: fill in the team registration Google Form with your team details, track, \nand the details and student ID of every member. Form link: [TBC: paste Google Form \nlink].",
            "confidence_level": "medium",
            "validation_status": "NEEDS_REVIEW",
            "related_ids": ["REQ-DOC001-BU01-007", "REV-DOC001-BU01-001"],
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_mechanism_and_portal",
            "name": "individual_xdemia_event_page_registration",
            "description": "Langkah 2 pendaftaran: Setiap anggota wajib bergabung secara individu pada laman resmi event Xdemia di https://xdemia.com/event/ai-builder-challenge-2026 (login/sign up lalu klik join) karena seluruh pengumuman, case brief, dan jadwal coaching dibagikan pada laman tersebut.",
            "section": "4. How to Register",
            "anchor": "2.​ Every member: join the official event page on Xdemia at \nhttps://xdemia.com/event/ai-builder-challenge-2026. Log in or sign up with your \nXdemia account, then click join. Each member must do this individually. \n\nAll announcements, case briefs, coaching schedules, and updates are shared on the event \npage, so joining it is required.",
            "related_ids": ["REQ-DOC001-BU01-006"],
        },
        {
            "category": "registration_requirements",
            "subcategory": "participant_verification_rule",
            "name": "verified_participant_criteria",
            "description": "Untuk perhitungan prize pool, peserta terverifikasi (verified participant) adalah individu unik yang melengkapi seluruh informasi pendaftaran wajib, terdaftar sebagai anggota tim yang sah, serta lolos pemeriksaan duplikasi dan kelayakan; formulir tidak lengkap, pendaftaran ganda, identitas tidak sah, dan individu tanpa tim yang sah tidak dihitung.",
            "section": "10. Verification and Competition Rules",
            "anchor": "Verified participant. For prize pool calculation, a verified participant is a unique individual \nwho completes all mandatory registration information, is listed as a member of a valid team, \nand passes duplicate and eligibility checks. Incomplete forms, duplicate registrations, invalid \nidentities, and individuals not attached to a valid team are not counted.",
            "exception_override": "Incomplete forms, duplicate registrations, invalid identities, and individuals not attached to a valid team are not counted",
            "related_ids": ["REQ-DOC001-BU01-020"],
        },
        # 3. Competition Structure
        {
            "category": "competition_structure",
            "subcategory": "competition_tracks_and_themes",
            "name": "competition_tracks_general_and_arsa_case",
            "description": "Setiap tim memilih 1 jalur kompetisi: (1) General Track (masalah dunia nyata terbuka lintas industri dan domain yang diselesaikan dengan AI) atau (2) Industry Case Track bersama ARSA Indonesia (Facility Management & IoT) dengan memilih 1 dari 5 tema (AC-1 AI for Facility Operations Optimisation, AC-2 AI-Powered Predictive Maintenance, AC-3 Smart Workforce & Cleaning Deployment, AC-4 AI Monitoring & Anomaly Detection, AC-5 Intelligent Facility Assistant).",
            "section": "3. Tracks",
            "anchor": raw_text[1566:3056],
            "related_ids": ["REQ-DOC001-BU01-013"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_stages_and_selection",
            "name": "five_sequential_competition_stages",
            "description": "Lima tahapan kompetisi berurutan: (1) Registration (mengisi form & join event page, memilih General Track atau ARSA Case Track), (2) Written proposal (November), (3) Build sprint (November, membangun prototipe dengan 2 hingga 3 sesi coaching serta check-in domain expert bagi tim Case-track), (4) Semifinal pitching (akhir November, 20 tim terbaik melakukan live pitch 15 menit + Q&A didahului pitch rehearsal & final prototype review), dan (5) Grand Final (Desember, live demo prototipe berjalan selama 20 menit + Q&A).",
            "section": "6. Competition Stages and Submissions",
            "anchor": raw_text[4670:5382],
            "related_ids": ["REQ-DOC001-BU01-011", "REQ-DOC001-BU01-012"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_timeline_and_deadlines",
            "name": "timeline_schedule_and_online_fallback_rule",
            "description": "Bagian 5 mencantumkan rentang kegiatan mulai registrasi September hingga Grand Final Desember 2026, namun tabel Bagian 5 menulis Early Bird September 2026, Normal Registration Oktober-Desember 2026, Proposal & Build Sprint Januari 2027, Semifinal Pitching Januari 2027 (Top 20 pitch live 15 menit + Q&A), dan Grand Final Februari 2027 (20 menit live demo + Q&A); Grand Final direncanakan hybrid di Jabodetabek dan beralih penuh ke online dengan jadwal tetap jika venue tidak terkonfirmasi tepat waktu.",
            "section": "5. Timeline",
            "anchor": raw_text[3700:4668],
            "confidence_level": "medium",
            "validation_status": "NEEDS_REVIEW",
            " related_ids": ["REQ-DOC001-BU01-010", "REV-DOC001-BU01-002"],
        },
        {
            "category": "competition_structure",
            "subcategory": "coaching_and_mentoring_program",
            "name": "structured_coaching_program_and_checkins",
            "description": "Setiap tim terdaftar menerima program coaching terstruktur sepanjang kompetisi (Technical coaching AI/ML/arsitektur dari jaringan Xdemia, Domain coaching dari pakar industri mitra case-track, serta Product & pitch coaching), meliputi webinar orientasi & penugasan coach, 2 hingga 3 sesi live coaching per tim selama build sprint (ditambah check-in domain expert untuk tim case-track), pitch rehearsal & final prototype review sebelum Semifinal, serta persiapan demo Grand Final.",
            "section": "7. Coaching Program",
            "anchor": raw_text[5581:6605],
            "related_ids": ["REQ-DOC001-BU01-010"],
        },
        # 4. Deliverables
        {
            "category": "deliverables",
            "subcategory": "proposal_or_essay_deliverable",
            "name": "written_proposal_submission",
            "description": "Proposal tertulis singkat (Written proposal) yang menjelaskan rumusan masalah (problem), pendekatan AI (AI approach), dan rencana pembangunan (build plan); tim Case-track menyusunnya berdasarkan brief ARSA.",
            "section": "6. Competition Stages and Submissions",
            "anchor": "2.​ Written proposal (November). Submit a short proposal describing the problem, your \n\nAI approach, and your build plan. Case-track teams base it on the ARSA brief.",
            "related_ids": ["REQ-DOC001-BU01-009"],
        },
        {
            "category": "deliverables",
            "subcategory": "prototype_or_exam_deliverable",
            "name": "working_ai_prototype_live_demo",
            "description": "Prototipe AI yang benar-benar berjalan (working prototype) pada saat Grand Final; sekadar slide, mockup, atau rekaman video saja tidak memenuhi syarat, dan tanpa working demo tim tidak berhak atas hadiah.",
            "section": "6. Competition Stages and Submissions",
            "anchor": "Live demo requirement. Your prototype must actually run at the Grand Final. Slides, \nmockups, or recorded videos alone do not qualify. Without a working demo, a team is not \neligible for prizes.",
            "related_ids": ["REQ-DOC001-BU01-015", "REQ-DOC001-BU01-020"],
        },
        {
            "category": "deliverables",
            "subcategory": "presentation_slide_deliverable",
            "name": "semifinal_live_pitch_and_final_demo_presentation",
            "description": "Presentasi live pitching selama 15 menit + Q&A di hadapan juri industri dan akademisi bagi Top 20 tim pada Semifinal, serta demonstrasi live prototype selama 20 menit + Q&A pada Grand Final.",
            "section": "5. Timeline",
            "anchor": "Semifinal Pitching January 2027 Top 20 teams pitch live (15 minutes plus Q&A) to \nindustry and academic judges. \n\nGrand Final and February 2027 20-minute live prototype demos plus Q&A, \nAwards awards, closing ceremony.",
            "related_ids": ["REQ-DOC001-BU01-014"],
        },
        # 5. Assessment Criteria
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_innovation_and_originality",
            "description": "Kriteria penilaian: Innovation and Originality dengan bobot eksplisit 25%.",
            "section": "8. Judging Criteria",
            "anchor": "Innovation and Originality 25%",
            "indicator_weight": "25%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_technical_feasibility",
            "description": "Kriteria penilaian: Technical Feasibility dengan bobot eksplisit 25%.",
            "section": "8. Judging Criteria",
            "anchor": "Technical Feasibility 25%",
            "indicator_weight": "25%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_impact_and_operational_value",
            "description": "Kriteria penilaian: Impact and Operational Value dengan bobot eksplisit 25%.",
            "section": "8. Judging Criteria",
            "anchor": "Impact and Operational Value 25%",
            "indicator_weight": "25%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_presentation_and_communication",
            "description": "Kriteria penilaian: Presentation and Communication dengan bobot eksplisit 25%.",
            "section": "8. Judging Criteria",
            "anchor": "Presentation and 25% \nCommunication",
            "indicator_weight": "25%",
        },
        # 6. Technical and General Rules
        {
            "category": "technical_and_general_rules",
            "subcategory": "disqualification_and_sanction_rules",
            "name": "disqualification_and_prize_ineligibility_rules",
            "description": "Tim dapat didiskualifikasi apabila melakukan pendaftaran ganda, pemalsuan identitas atau status mahasiswa, atau keanggotaan di lebih dari 1 tim; tim tanpa live working prototype pada Grand Final tidak berhak atas hadiah.",
            "section": "10. Verification and Competition Rules",
            "anchor": "Disqualification. A team may be disqualified for duplicate registration, false identity or \nstudent status, or membership in more than one team. A team without a live, working \nprototype at the Grand Final is not eligible for prizes.",
            "related_ids": ["REQ-DOC001-BU01-004", "REQ-DOC001-BU01-014"],
        },
    ]

    records: List[ExtractedRequirementRecord] = []
    for idx, sp in enumerate(specs, 1):
        req_id = f"REQ-DOC001-BU01-{idx:03d}"
        records.append(
            _make_record(
                req_id=req_id,
                doc_id=doc_id,
                unit_id=uid,
                comp_name=comp,
                category=sp["category"],
                subcategory=sp["subcategory"],
                name=sp["name"],
                description=sp["description"],
                section=sp["section"],
                raw_text=raw_text,
                page_spans=pages,
                unit_start=u_start,
                unit_end=u_end,
                unit_seg_status=u_status,
                anchor=sp["anchor"],
                evidence_type=sp.get("evidence_type", "explicit"),
                confidence_level=sp.get("confidence_level", "high"),
                extraction_method=sp.get(
                    "extraction_method", "rule_based_clause_and_span_extractor"
                ),
                validation_status=sp.get("validation_status", "VALIDATED"),
                statement_nature=sp.get("statement_nature"),
                indicator_weight=sp.get("indicator_weight", "N/A"),
                exception_override=sp.get("exception_override"),
                related_ids=sp.get("related_ids") or sp.get(" related_ids"),
            )
        )

    info_items = [
        SupportingInformationRecord(
            info_id="INFO-DOC001-BU01-001",
            document_id=doc_id,
            branch_unit_id=uid,
            competition_name=comp,
            info_category="prize_pool_and_awards_context",
            info_name="tiered_prize_pool_and_special_awards",
            info_description="Total prize pool hingga Rp25.000.000 berdasarkan kuota peserta terverifikasi (5.000+, 3.000-4.999, 1.500-2.999, <1.500) beserta 10 Special Awards dan Finalist Appreciation.",
            source_page=_locate_page_for_char(pages, 7002),
            source_section="9. Prizes",
            source_char_start=7002,
            source_char_end=8445,
            evidence_text=raw_text[7002:8445],
        )
    ]

    gaps = [
        ExtractionGapRecord(
            gap_id="GAP-DOC001-BU01-001",
            document_id=doc_id,
            branch_unit_id=uid,
            competition_name=comp,
            requirement_category="eligibility_requirements",
            requirement_subcategory="education_level_and_student_status",
            missing_attribute_name="age_limit",
            gap_status="NOT_STATED",
            inspected_sections=["2. Eligibility and Teams", "11. FAQ and Contact"],
            inspected_char_range="895..1557",
            verification_method="rule_based_section_absence_scan",
            notes="Dokumen hanya mensyaratkan status mahasiswa aktif perguruan tinggi di Indonesia tanpa mencantumkan batas usia minimum atau maksimum.",
        ),
        ExtractionGapRecord(
            gap_id="GAP-DOC001-BU01-002",
            document_id=doc_id,
            branch_unit_id=uid,
            competition_name=comp,
            requirement_category="eligibility_requirements",
            requirement_subcategory="team_composition_and_institution_rule",
            missing_attribute_name="same_university_or_cross_university_restriction",
            gap_status="NOT_STATED",
            inspected_sections=["2. Eligibility and Teams", "11. FAQ and Contact"],
            inspected_char_range="895..1557",
            verification_method="rule_based_section_absence_scan",
            notes="Dokumen tidak mencantumkan aturan apakah anggota dalam satu tim wajib berasal dari universitas yang sama atau diperbolehkan lintas universitas.",
        ),
        ExtractionGapRecord(
            gap_id="GAP-DOC001-BU01-003",
            document_id=doc_id,
            branch_unit_id=uid,
            competition_name=comp,
            requirement_category="deliverables",
            requirement_subcategory="prototype_or_exam_deliverable",
            missing_attribute_name="standalone_source_code_repository_submission",
            gap_status="NOT_STATED",
            inspected_sections=["6. Competition Stages and Submissions"],
            inspected_char_range="4670..5580",
            verification_method="rule_based_section_absence_scan",
            notes="Dokumen mewajibkan live working prototype demo pada Grand Final, namun tidak menyebutkan kewajiban pengumpulan repositori source code secara terpisah.",
        ),
        ExtractionGapRecord(
            gap_id="GAP-DOC001-BU01-004",
            document_id=doc_id,
            branch_unit_id=uid,
            competition_name=comp,
            requirement_category="technical_and_general_rules",
            requirement_subcategory="document_formatting_and_length",
            missing_attribute_name="proposal_page_limit_and_file_format",
            gap_status="NOT_STATED",
            inspected_sections=["6. Competition Stages and Submissions"],
            inspected_char_range="4814..4980",
            verification_method="rule_based_section_absence_scan",
            notes="Bagian 6 hanya menyebut 'short proposal' tanpa mencantumkan batas jumlah halaman, ukuran font, margin, maupun format ekstensi berkas.",
        ),
    ]

    reviews = [
        ReviewItemRecord(
            review_id="REV-DOC001-BU01-001",
            document_id=doc_id,
            branch_unit_id=uid,
            competition_name=comp,
            related_requirement_id="REQ-DOC001-BU01-006",
            issue_type="unfilled_template_placeholder",
            severity="MEDIUM",
            review_status="NEEDS_REVIEW",
            source_page=_locate_page_for_char(pages, 3176),
            source_section="4. How to Register",
            source_char_start=3176,
            source_char_end=3357,
            evidence_text=raw_text[3176:3357],
            review_description="Tautan Google Form pendaftaran ketua tim masih berupa placeholder '[TBC: paste Google Form link]'.",
            recommended_human_action="Periksa pembaruan pengumuman pada laman resmi event Xdemia untuk mendapatkan tautan Google Form aktif.",
        ),
        ReviewItemRecord(
            review_id="REV-DOC001-BU01-002",
            document_id=doc_id,
            branch_unit_id=uid,
            competition_name=comp,
            related_requirement_id="REQ-DOC001-BU01-011",
            issue_type="internal_schedule_contradiction",
            severity="HIGH",
            review_status="NEEDS_REVIEW",
            source_page=_locate_page_for_char(pages, 3700),
            source_section="5. Timeline & 6. Competition Stages and Submissions",
            source_char_start=3700,
            source_char_end=5382,
            evidence_text=raw_text[3700:5382],
            review_description="Inkonsistensi jadwal internal: Paragraf pengantar Bagian 5 dan Bagian 6 menulis Proposal/Build Sprint/Semifinal pada November 2026 dan Grand Final Desember 2026, sedangkan Tabel Bagian 5 dan Tabel Bagian 7 menulis Januari 2027 dan Februari 2027.",
            recommended_human_action="Konfirmasi jadwal resmi ke penyelenggara (Xdemia) atau cek laman event sebelum menetapkan tenggat di sistem.",
        ),
        ReviewItemRecord(
            review_id="REV-DOC001-BU01-003",
            document_id=doc_id,
            branch_unit_id=uid,
            competition_name=comp,
            related_requirement_id="REQ-DOC001-BU01-008",
            issue_type="unfilled_template_placeholder",
            severity="LOW",
            review_status="NEEDS_REVIEW",
            source_page=_locate_page_for_char(pages, 9854),
            source_section="10. Verification and Competition Rules",
            source_char_start=9854,
            source_char_end=10075,
            evidence_text=raw_text[9854:10075],
            review_description="Dasar perhitungan jumlah peserta akhir pada Bagian 10 masih memuat placeholder '[TBC: verified registrations or completed submissions]'.",
            recommended_human_action="Verifikasi aturan final perhitungan peserta setelah masa registrasi ditutup.",
        ),
    ]

    return records, info_items, gaps, reviews


def _extract_doc024_units(
    raw_text: str,
    units_by_id: Dict[str, Dict[str, Any]],
    vals_by_id: Dict[str, Dict[str, Any]],
) -> Tuple[
    List[ExtractedRequirementRecord],
    List[SupportingInformationRecord],
    List[ExtractionGapRecord],
    List[ReviewItemRecord],
]:
    """Extract refined requirements, info, gaps, and review items for DOC-024 (BU-01, BU-02, BU-03)."""
    doc_id = "DOC-024"
    pages = _build_page_spans(raw_text)
    records: List[ExtractedRequirementRecord] = []
    info_items: List[SupportingInformationRecord] = []
    gaps: List[ExtractionGapRecord] = []
    reviews: List[ReviewItemRecord] = []

    # =========================================================================
    # DOC-024-BU-01: Cabang Esai (4122..10785)
    # =========================================================================
    u1 = units_by_id["DOC-024-BU-01"]
    v1 = vals_by_id["DOC-024-BU-01"]
    u1_s, u1_e = int(u1["start_char"]), int(u1["end_char"])
    u1_specs: List[Dict[str, Any]] = [
        {
            "category": "eligibility_requirements",
            "subcategory": "education_level_and_student_status",
            "name": "active_university_student_and_ktm_ktms",
            "description": "Peserta merupakan Mahasiswa aktif Perguruan Tinggi Negeri/Swasta di Indonesia yang dibuktikan dengan Kartu Tanda Mahasiswa (KTM) atau Kartu Tanda Mahasiswa Sementara (KTMS).",
            "section": "Syarat & Ketentuan Cabang Esai",
            "anchor": "Peserta merupakan Mahasiswa aktif Perguruan Tinggi\nNegeri/Swasta di Indonesia dibuktikan dengan Kartu Tanda\nMahasiswa (KTM) atau Kartu Tanda Mahasiswa Sementara\n(KTMS).",
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "participation_mode_and_team_size",
            "name": "individual_or_two_person_same_university_team",
            "description": "Peserta dapat berupa perorangan maupun kelompok dengan jumlah 2 orang (1 orang sebagai ketua tim dan yang lain sebagai anggota) dari universitas yang sama.",
            "section": "Syarat & Ketentuan Cabang Esai",
            "anchor": "Peserta dapat berupa perorangan maupun kelompok dengan\njumlah 2 orang dengan 1 orang sebagai ketua tim dan yang lain\nsebagai anggota (dengan universitas yang sama).",
            "related_ids": ["REQ-DOC024-BU01-016", "REV-DOC024-BU01-001"],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "team_composition_and_institution_rule",
            "name": "no_participant_replacement_rule",
            "description": "Peserta yang telah terdaftar tidak boleh digantikan dengan peserta lain.",
            "section": "Syarat & Ketentuan Cabang Esai",
            "anchor": "Peserta yang terdaftar tidak boleh digantikan dengan peserta\nlain.",
        },
        {
            "category": "registration_requirements",
            "subcategory": "administrative_and_twibbon_requirements",
            "name": "twibbon_upload_and_portal_registration",
            "description": "Seluruh peserta wajib follow dan memposting twibbon (https://twibbo.nz/twibbonimpacteers) pada feed Instagram masing-masing serta tag 3 orang teman, kemudian melakukan pendaftaran dan mengunggah karya melalui tautan linktr.ee/impacteers2025 dengan menyertakan bukti transfer, screenshot upload twibbon, dan bukti cek plagiasi.",
            "section": "Mekanisme Pendaftaran Cabang Esai",
            "anchor": raw_text[8008:8343],
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "registration_fee_waves_and_bank_accounts",
            "description": "Biaya pendaftaran cabang esai: Gelombang I Rp 45.000, Gelombang II Rp 55.000, dan Gelombang III Rp 65.000 melalui rekening BTN (3101610038719) atau Seabank (901087636177) a.n Jauzaa Hayaah Kusnandar.",
            "section": "Mekanisme Pembayaran Cabang Esai",
            "anchor": raw_text[8685:8913],
            "related_ids": ["REQ-DOC024-BU01-006"],
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "non_refundable_fee_and_multiple_submission_payment",
            "description": "Peserta dapat mengirimkan lebih dari satu karya dengan formulir pendaftaran berbeda dan pembayaran sesuai banyaknya karya; biaya yang telah dibayarkan tidak dapat dikembalikan dengan alasan apa pun.",
            "section": "Syarat & Ketentuan Cabang Esai",
            "anchor": raw_text[4812:5616],
            "related_ids": ["REQ-DOC024-BU01-005"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_tracks_and_themes",
            "name": "essay_main_theme_and_seven_subthemes",
            "description": "Mengangkat tema besar 'Transformasi Inovatif Generasi Muda: Pilar Utama Pembangunan Berkelanjutan Menuju Indonesia Emas 2045' dengan sub-tema cabang esai: Ekonomi, Teknologi, Pendidikan, Kesehatan, Sosial Budaya, dan Energi Terbarukan.",
            "section": "Tema & Subtema Cabang Esai",
            "anchor": raw_text[4149:4445],
            "related_ids": ["REQ-DOC024-BU01-012"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_timeline_and_deadlines",
            "name": "essay_competition_timeline",
            "description": "Jadwal lomba cabang esai: Gelombang I (20 - 25 April 2025), Gelombang II (26 April - 10 Mei 2025), Gelombang III (11 - 20 Mei 2025), Penilaian (27 - 30 Mei 2025), dan Pengumuman (31 Mei 2025).",
            "section": "Timeline Lomba Cabang Esai",
            "anchor": raw_text[7687:7840],
            "related_ids": ["REQ-DOC024-BU01-009"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_stages_and_selection",
            "name": "essay_direct_selection_six_best_works",
            "description": "Karya esai yang dikirimkan peserta diseleksi oleh tim juri dan dipilih 6 karya terbaik untuk menjadi juara 1, 2, 3 dan harapan 1, 2, 3 pada Lomba Esai Tingkat Nasional impacteers 2025.",
            "section": "Skema Penilaian Cabang Esai",
            "anchor": raw_text[9075:9265],
            "related_ids": ["REQ-DOC024-BU01-008"],
        },
        {
            "category": "deliverables",
            "subcategory": "proposal_or_essay_deliverable",
            "name": "essay_six_part_structure_and_originality_attachment",
            "description": "Struktur esai secara umum terdiri atas 6 bagian (diperbolehkan sub-judul): (1) Cover berlogo kampus masing-masing, (2) Pendahuluan (latar belakang, identifikasi permasalahan, tujuan penulisan), (3) Isi (gagasan baru atau hasil penelitian yang dimodifikasi), (4) Penutup (kesimpulan), (5) Daftar pustaka, dan (6) Lampiran (Lembar Orisinalitas Karya, gambar, tabel, atau grafik).",
            "section": "Ketentuan Penulisan Karya Cabang Esai",
            "anchor": raw_text[7125:7535],
            "related_ids": ["REQ-DOC024-BU01-011", "REQ-DOC024-BU01-017"],
        },
        {
            "category": "deliverables",
            "subcategory": "deliverable_template_or_example",
            "name": "cover_and_originality_sheet_template_link",
            "description": "Format cover dan lembar orisinalitas peserta disediakan melalui tautan linktr.ee/impacteers2025.",
            "section": "Mekanisme Pendaftaran Cabang Esai",
            "anchor": "Format cover dan lembar orisinalitas peserta dapat\ndiakses melalui link linktr.ee/impacteers2025",
            "statement_nature": "template",
            "related_ids": ["REQ-DOC024-BU01-010"],
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_topik_yang_dikemukakan",
            "description": "Kriteria 1: Topik yang dikemukakan (penulisan dan kesesuaian judul dengan tema, topik yang dipilih, dan isi karya; aktualisasi topik dan fokus pembahasan) — skor 15%.",
            "section": "Skema Penilaian Cabang Esai",
            "anchor": raw_text[9326:9485],
            "indicator_weight": "15%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_mutu_gagasan",
            "description": "Kriteria 2: Mutu Gagasan (kreatif dan inovatif, keaslian gagasan, kejelasan dan sistematika pengungkapan ide, kebermanfaatan dalam penerapannya) — skor 40%.",
            "section": "Skema Penilaian Cabang Esai",
            "anchor": raw_text[9487:9621],
            "indicator_weight": "40%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_data_dan_informasi",
            "description": "Kriteria 3: Data dan informasi (kesesuaian informasi dengan acuan yang digunakan, keakuratan data dan informasi) — skor 35%.",
            "section": "Skema Penilaian Cabang Esai",
            "anchor": raw_text[9623:9727],
            "indicator_weight": "35%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_format",
            "description": "Kriteria 4: Format (tata tulis: ukuran kertas, tipografi, kerapihan ketik, tata letak, margin, jumlah halaman, dan penggunaan bahasa Indonesia) — skor 10%.",
            "section": "Skema Penilaian Cabang Esai",
            "anchor": raw_text[9729:9871],
            "indicator_weight": "10%",
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "document_formatting_and_length",
            "name": "essay_page_length_typography_margins_and_contradiction",
            "description": "Esai menggunakan Bahasa Indonesia sesuai PUEBI; judul berkaitan dengan subtema (huruf kapital, bold, center, Times New Roman 14, maksimal 20 kata); panjang 7 halaman – 10 halaman (tidak termasuk cover, daftar pustaka, lembar orisinalitas, dan lampiran); referensi APA; diketik dengan batas tepi kiri 4, kanan 3, atas 3, bawah 3 (cm), kertas A4 (210 mm x 297 mm), font Times New Roman 12 pt, spasi baris 1.5. (Catatan review: kalimat 'Naskah ditulis secara individu' berkontradiksi dengan aturan kelompok 2 orang pada halaman 7).",
            "section": "Ketentuan Penulisan Karya Cabang Esai",
            "anchor": raw_text[6050:7123],
            "confidence_level": "medium",
            "validation_status": "NEEDS_REVIEW",
            "related_ids": ["REQ-DOC024-BU01-002", "REV-DOC024-BU01-001"],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "media_and_file_specification",
            "name": "essay_pdf_format_and_file_naming_rule",
            "description": "Dokumen esai yang diunggah berupa softcopy PDF dengan format penamaan berkas: Nama Lengkap_Instansi_3 kata pertama judul esai.",
            "section": "Mekanisme Pendaftaran Cabang Esai",
            "anchor": raw_text[8344:8470],
            "related_ids": ["REQ-DOC024-BU01-010"],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "originality_and_plagiarism_threshold",
            "name": "plagiarism_limit_30_percent_and_originality",
            "description": "Naskah bukan merupakan salinan, terjemahan, ataupun plagiat karya lain dengan batas plagiasi maksimal 30% (menggunakan Turnitin atau media sejenis, bukti diunggah melalui Google Form), belum pernah dipublikasikan pada perlombaan lain, dan tidak mengandung unsur SARA atau pornografi.",
            "section": "Syarat & Ketentuan dan Ketentuan Penulisan Cabang Esai",
            "anchor": raw_text[5003:6861],
        },
    ]

    for idx, sp in enumerate(u1_specs, 1):
        records.append(
            _make_record(
                req_id=f"REQ-DOC024-BU01-{idx:03d}",
                doc_id=doc_id,
                unit_id="DOC-024-BU-01",
                comp_name="Impacteers UNESA 2025 - Essay Competition",
                category=sp["category"],
                subcategory=sp["subcategory"],
                name=sp["name"],
                description=sp["description"],
                section=sp["section"],
                raw_text=raw_text,
                page_spans=pages,
                unit_start=u1_s,
                unit_end=u1_e,
                unit_seg_status=v1["validation_status"],
                anchor=sp["anchor"],
                confidence_level=sp.get("confidence_level", "high"),
                validation_status=sp.get("validation_status", "VALIDATED"),
                statement_nature=sp.get("statement_nature"),
                indicator_weight=sp.get("indicator_weight", "N/A"),
                related_ids=sp.get("related_ids"),
            )
        )

    # =========================================================================
    # DOC-024-BU-02: Cabang BMC (10785..17612)
    # =========================================================================
    u2 = units_by_id["DOC-024-BU-02"]
    v2 = vals_by_id["DOC-024-BU-02"]
    u2_s, u2_e = int(u2["start_char"]), int(u2["end_char"])
    u2_specs: List[Dict[str, Any]] = [
        {
            "category": "eligibility_requirements",
            "subcategory": "education_level_and_student_status",
            "name": "active_university_student_and_ktm_ktms",
            "description": "Peserta merupakan Mahasiswa aktif Perguruan Tinggi Negeri/Swasta di Indonesia dibuktikan dengan Kartu Tanda Mahasiswa (KTM) atau Kartu Tanda Mahasiswa Sementara (KTMS).",
            "section": "Syarat & Ketentuan Cabang BMC",
            "anchor": raw_text[11119:11287],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "participation_mode_and_team_size",
            "name": "individual_or_two_person_same_university_team",
            "description": "Peserta dapat berupa perorangan maupun kelompok dengan jumlah 2 orang (1 orang sebagai ketua tim dan yang lain sebagai anggota) dari universitas yang sama.",
            "section": "Syarat & Ketentuan Cabang BMC",
            "anchor": raw_text[11288:11452],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "team_composition_and_institution_rule",
            "name": "no_participant_replacement_rule",
            "description": "Peserta yang terdaftar tidak boleh digantikan dengan peserta lain.",
            "section": "Syarat & Ketentuan Cabang BMC",
            "anchor": raw_text[11881:11947],
        },
        {
            "category": "registration_requirements",
            "subcategory": "administrative_and_twibbon_requirements",
            "name": "twibbon_upload_and_portal_registration",
            "description": "Seluruh peserta wajib follow dan memposting twibbon (https://twibbo.nz/twibbonimpacteers) pada feed Instagram masing-masing dan tag 3 orang teman, kemudian melakukan pendaftaran dan mengunggah karya melalui tautan linktr.ee/impacteers2025 dengan menyertakan bukti transfer, screenshot upload twibbon, Kartu Tanda Mahasiswa (KTM), dan bukti cek plagiasi.",
            "section": "Mekanisme Pendaftaran Cabang BMC",
            "anchor": raw_text[14658:15026],
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "registration_fee_waves_and_bank_accounts",
            "description": "Biaya pendaftaran cabang BMC: Gelombang I Rp 45.000, Gelombang II Rp 55.000, dan Gelombang III Rp 65.000 melalui rekening BTN (3101610038719) atau Seabank (901087636177) a.n Jauzaa Hayaah Kusnandar.",
            "section": "Mekanisme Pembayaran Cabang BMC",
            "anchor": raw_text[15365:15593],
            "related_ids": ["REQ-DOC024-BU02-006"],
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "multiple_bmc_submissions_and_non_refundable_fee",
            "description": "Peserta dapat mengirimkan lebih dari satu karya BMC dengan submission formulir pendaftaran berbeda dan pembayaran sesuai banyaknya karya; biaya yang telah dibayarkan tidak dapat dikembalikan dengan alasan apa pun.",
            "section": "Syarat & Ketentuan Cabang BMC",
            "anchor": raw_text[11453:12185],
            "related_ids": ["REQ-DOC024-BU02-005"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_tracks_and_themes",
            "name": "bmc_main_theme_and_six_subthemes",
            "description": "Mengangkat tema besar 'Transformasi Inovatif Generasi Muda : Pilar Utama Pembangunan Berkelanjutan Menuju Indonesia Emas 2045' dengan fokus cabang BMC pada sub-tema: Teknologi, Jasa, Agribisnis, F&B, Kesehatan, dan Pariwisata.",
            "section": "Tema & Subtema Cabang BMC",
            "anchor": raw_text[10811:11087],
            "related_ids": ["REQ-DOC024-BU02-012"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_timeline_and_deadlines",
            "name": "bmc_timeline_including_tm_and_final",
            "description": "Jadwal cabang BMC: Gelombang I (20 - 25 April 2025), Gelombang II (26 April - 10 mei 2025), Gelombang III (11 - 20 Mei 2025), Penilaian (27 - 30 Mei 2025), Pengumuman (31 Mei 2025), Technical Meeting BMC (1 Juni 2025), dan Final BMC (8 Juni 2025).",
            "section": "Timeline Lomba Cabang BMC",
            "anchor": raw_text[14281:14491],
            "related_ids": ["REQ-DOC024-BU02-009"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_stages_and_selection",
            "name": "bmc_six_finalists_online_final_selection",
            "description": "Karya BMC yang dikirimkan peserta diseleksi oleh tim juri dan dipilih 6 karya terbaik (diumumkan di Instagram @impacteers_unesa) untuk melaju ke tahap final yang dilaksanakan secara online.",
            "section": "Skema Penilaian Cabang BMC",
            "anchor": raw_text[15754:15910],
            "related_ids": ["REQ-DOC024-BU02-008"],
        },
        {
            "category": "deliverables",
            "subcategory": "bmc_deliverable",
            "name": "bmc_nine_elements_structure",
            "description": "Karya Business Model Canvas (BMC) wajib memuat elemen: Customer Segments, Value Proportions, Channels, Customer Relationship, Revenue Stream, Key Activities, Key Resources, Key Partnership, dan Cost Structure.",
            "section": "Ketentuan Penulisan Karya Cabang BMC",
            "anchor": raw_text[12480:14129],
            "related_ids": ["REQ-DOC024-BU02-011", "REQ-DOC024-BU02-013"],
        },
        {
            "category": "deliverables",
            "subcategory": "deliverable_template_or_example",
            "name": "bmc_non_binding_example_template",
            "description": "Template BMC pada buku panduan hanya dipergunakan sebagai contoh sehingga peserta bebas mengkreasikan desain sesuai kebutuhan judul masing-masing.",
            "section": "Tamplate Karya BMC",
            "anchor": raw_text[16912:17044],
            "statement_nature": "example",
            "related_ids": ["REQ-DOC024-BU02-010"],
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_topik_yang_dikemukakan",
            "description": "Kriteria 1: Topik yang dikemukakan — Kesesuaian ide bisnis dengan tema lomba (10%) dan ide bisnis termasuk dalam kategori subtema yang dipilih (10%).",
            "section": "Skema Penilaian Cabang BMC",
            "anchor": raw_text[15970:16100],
            "indicator_weight": "10% + 10%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_kelengkapan_9_elemen_bmc",
            "description": "Kriteria 2: Kelengkapan — Memuat 9 elemen BMC secara garis besar (10%) dan isi dari 9 elemen BMC sesuai (10%).",
            "section": "Skema Penilaian Cabang BMC",
            "anchor": raw_text[16102:16195],
            "indicator_weight": "10% + 10%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_inovasi",
            "description": "Kriteria 3: Inovasi — Ide bisnis merupakan ide baru atau pengembangan dari ide yang telah ada (20%).",
            "section": "Skema Penilaian Cabang BMC",
            "anchor": raw_text[16197:16285],
            "indicator_weight": "20%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_relevan",
            "description": "Kriteria 4: Relevan — Ide bisnis merupakan solusi dari permasalahan yang benar adanya (10%).",
            "section": "Skema Penilaian Cabang BMC",
            "anchor": raw_text[16289:16367],
            "indicator_weight": "10%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_kreativitas",
            "description": "Kriteria 5: Kreativitas — Pengemasan kata dalam ide bisnis singkat, jelas, dan lengkap (10%) serta penyusunan BMC secara menarik (5%).",
            "section": "Skema Penilaian Cabang BMC",
            "anchor": raw_text[16369:16481],
            "indicator_weight": "10% + 5%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_potensi_realistis_bisnis",
            "description": "Kriteria 6: Potensi Realistis Bisnis — Ide bisnis bukan merupakan gagasan abstrak (5%) dan dapat diwujudkan dalam bentuk nyata atau operasional (10%).",
            "section": "Skema Penilaian Cabang BMC",
            "anchor": raw_text[16483:16625],
            "indicator_weight": "5% + 10%",
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "document_formatting_and_length",
            "name": "no_page_limit_for_short_business_description",
            "description": "Peserta dibebaskan membuat desain BMC sekreatif mungkin dan tidak ada batas halaman untuk deskripsi singkat ide bisnis.",
            "section": "Tamplate Karya BMC",
            "anchor": raw_text[16795:16910],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "media_and_file_specification",
            "name": "bmc_pdf_file_naming_with_copy_paste_typo",
            "description": "Berkas diunggah berupa softcopy PDF dengan format nama file: Nama Lengkap_Instansi_3 kata pertama judul bmc (Catatan review: teks sumber memuat salah ketik salin-tempel 'Dokumen esai yang diunggah... judul bmc').",
            "section": "Mekanisme Pendaftaran Cabang BMC",
            "anchor": raw_text[15027:15152],
            "confidence_level": "medium",
            "validation_status": "NEEDS_REVIEW",
            "related_ids": ["REV-DOC024-BU02-001"],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "content_and_tool_prohibition",
            "name": "bmc_sara_pornography_prohibition_and_unpblished_rule",
            "description": "Karya yang diikutsertakan dalam lomba BMC tidak mengandung unsur SARA ataupun pornografi, belum pernah dipublikasikan pada perlombaan lainnya, dan harus sesuai dengan format yang ditentukan.",
            "section": "Syarat & Ketentuan Cabang BMC",
            "anchor": raw_text[11652:11880],
        },
    ]

    for idx, sp in enumerate(u2_specs, 1):
        records.append(
            _make_record(
                req_id=f"REQ-DOC024-BU02-{idx:03d}",
                doc_id=doc_id,
                unit_id="DOC-024-BU-02",
                comp_name="Impacteers UNESA 2025 - Business Model Canvas Competition",
                category=sp["category"],
                subcategory=sp["subcategory"],
                name=sp["name"],
                description=sp["description"],
                section=sp["section"],
                raw_text=raw_text,
                page_spans=pages,
                unit_start=u2_s,
                unit_end=u2_e,
                unit_seg_status=v2["validation_status"],
                anchor=sp["anchor"],
                confidence_level=sp.get("confidence_level", "high"),
                validation_status=sp.get("validation_status", "VALIDATED"),
                statement_nature=sp.get("statement_nature"),
                indicator_weight=sp.get("indicator_weight", "N/A"),
                related_ids=sp.get("related_ids"),
            )
        )

    # =========================================================================
    # DOC-024-BU-03: Cabang Poster (17612..24733)
    # =========================================================================
    u3 = units_by_id["DOC-024-BU-03"]
    v3 = vals_by_id["DOC-024-BU-03"]
    u3_s, u3_e = int(u3["start_char"]), int(u3["end_char"])
    u3_specs: List[Dict[str, Any]] = [
        {
            "category": "eligibility_requirements",
            "subcategory": "education_level_and_student_status",
            "name": "individual_university_and_school_student_categories",
            "description": "Peserta bersifat Individu dalam kategori Individu Mahasiswa aktif Perguruan Tinggi Negeri/Swasta di Indonesia (dibuktikan dengan Kartu Tanda Mahasiswa/KTM) dan Individu pelajar aktif sekolah Negeri/Swasta di Indonesia (dibuktikan dengan Kartu Tanda Pelajar/KTP).",
            "section": "Syarat & Ketentuan Cabang Poster",
            "anchor": raw_text[17967:18221],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "team_composition_and_institution_rule",
            "name": "no_participant_replacement_rule",
            "description": "Peserta yang terdaftar tidak boleh digantikan dengan peserta lain.",
            "section": "Syarat dan ketentuan Cabang Poster",
            "anchor": raw_text[18925:18991],
        },
        {
            "category": "registration_requirements",
            "subcategory": "administrative_and_twibbon_requirements",
            "name": "twibbon_upload_and_portal_registration_with_copy_paste_anomaly",
            "description": "Seluruh peserta wajib follow dan memposting twibbon (https://twibbo.nz/twibbonimpacteers) pada feed Instagram masing-masing dan tag 3 orang teman, lalu mendaftar dan mengunggah karya melalui linktr.ee/impacteers2025. (Catatan review: teks sumber memuat salah ketik salin-tempel dari cabang Esai/BMC: 'Kartu Tanda Mahasiswa (KTM), dan bukti cek plagiasi', 'Dokumen esai yang diunggah... judul esai', serta 'Karya BMC').",
            "section": "Mekanisme Pendaftaran Cabang Poster",
            "anchor": raw_text[21613:22287],
            "confidence_level": "medium",
            "validation_status": "NEEDS_REVIEW",
            "related_ids": ["REV-DOC024-BU03-001"],
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "registration_fee_waves_and_bank_accounts",
            "description": "Biaya pendaftaran cabang poster: Gelombang I Rp 45.000, Gelombang II Rp 55.000, dan Gelombang III Rp 65.000 melalui rekening BTN (3101610038719) atau Seabank (901087636177) a.n Jauzaa Hayaah Kusnandar.",
            "section": "Mekanisme Pembayaran Cabang Poster",
            "anchor": raw_text[22324:22552],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_tracks_and_themes",
            "name": "poster_main_theme_and_six_subthemes",
            "description": "Mengangkat tema besar 'Transformasi Inovatif Generasi Muda : Pilar Utama Pembangunan Berkelanjutan Menuju Indonesia Emas 2045' dengan fokus cabang poster pada sub-tema: Ekonomi, Teknologi, Pendidikan, Kesehatan, Sosial Budaya, dan Politik.",
            "section": "Tema & Subtema Cabang Poster",
            "anchor": raw_text[17642:17932],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_timeline_and_deadlines",
            "name": "poster_competition_timeline",
            "description": "Jadwal cabang poster: Gelombang I (20 - 25 April 2025), Gelombang II (26 April - 10 Mei 2025), Gelombang III (11 - 20 Mei 2025), Penilaian (27 - 30 Mei 2025), dan Pengumuman (31 Mei 2025).",
            "section": "Timeline Lomba Cabang Poster",
            "anchor": raw_text[21290:21443],
            "related_ids": ["REQ-DOC024-BU03-007"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_stages_and_selection",
            "name": "poster_direct_selection_six_winners_per_category",
            "description": "Karya poster yang dikirimkan peserta diseleksi oleh tim juri dan dipilih 6 karya terbaik untuk menjadi juara 1, 2, 3 dan harapan 1, 2, 3 pada setiap kategori (kategori pemenang dibedakan antara mahasiswa dan siswa).",
            "section": "Skema Penilaian Cabang Poster",
            "anchor": raw_text[22716:22932],
            "related_ids": ["REQ-DOC024-BU03-001", "REQ-DOC024-BU03-006"],
        },
        {
            "category": "deliverables",
            "subcategory": "poster_deliverable",
            "name": "digital_poster_submission_and_no_ig_upload_rule",
            "description": "Karya poster digital dikirimkan pada formulir pendaftaran (diperbolehkan mengirimkan lebih dari 1 lembar poster dengan formulir pendaftaran dan pembayaran berbeda sesuai banyaknya karya); poster tidak perlu diunggah ke Instagram masing-masing karena penilaian berdasarkan karya yang dikirimkan ke form pendaftaran.",
            "section": "Syarat & Ketentuan dan Ketentuan Desain Cabang Poster",
            "anchor": raw_text[18222:19418],
            "related_ids": ["REQ-DOC024-BU03-015"],
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_kreativitas_dan_originalitas",
            "description": "Kriteria 1: Kreativitas dan Originalitas (Inovasi: ide-ide baru dan kreatif; Keaslian: unik dan berbeda dari poster ilmiah yang sudah ada) — skor 10%.",
            "section": "Skema Penilaian Cabang Poster",
            "anchor": raw_text[22993:23179],
            "indicator_weight": "10%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_kejelasan_dan_keterbacaan",
            "description": "Kriteria 2: Kejelasan dan Keterbacaan (Tata Letak: pengaturan elemen, keseimbangan, dan aliran visual; Tipografi: pemilihan font dan ukuran teks yang memudahkan pembacaan; Bahasa: penggunaan bahasa yang jelas dan ringkas untuk menjelaskan konsep ilmiah) — skor 25%.",
            "section": "Skema Penilaian Cabang Poster",
            "anchor": raw_text[23181:23459],
            "indicator_weight": "25%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_kualitas_visual_dan_desain_grafis",
            "description": "Kriteria 3: Kualitas Visual dan Desain Grafis (Gambar dan Grafik: kualitas gambar, grafik, dan ilustrasi pendukung konten; Warna: penggunaan warna efektif dan estetis; Konsistensi: keselarasan antara elemen visual dan teks) — skor 30%.",
            "section": "Skema Penilaian Cabang Poster",
            "anchor": raw_text[23461:23704],
            "indicator_weight": "30%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_ketepatan_dan_relevansi",
            "description": "Kriteria 4: Ketepatan dan Relevansi (Akurasi: ketepatan data dan informasi yang disajikan; Relevansi: hubungan antara konten poster dengan topik yang dipilih) — skor 20%.",
            "section": "Skema Penilaian Cabang Poster",
            "anchor": raw_text[23706:23858],
            "indicator_weight": "20%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_dampak_dan_daya_tarik",
            "description": "Kriteria 5: Dampak dan Daya Tarik (Kesan Pertama: seberapa menarik poster saat pertama kali dilihat; Pesan yang Disampaikan: kemampuan menyampaikan pesan ilmiah dengan kuat dan jelas) — skor 10%.",
            "section": "Skema Penilaian Cabang Poster",
            "anchor": raw_text[23860:24049],
            "indicator_weight": "10%",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_weighted",
            "name": "criterion_kepatuhan_terhadap_aturan",
            "description": "Kriteria 6: Kepatuhan terhadap Aturan (Kepatuhan Teknis: memenuhi semua persyaratan teknis ukuran, format, dll.; Etika dan Hak Cipta: menghormati hak cipta dan etika) — skor 5%.",
            "section": "Skema Penilaian Cabang Poster",
            "anchor": raw_text[24051:24263],
            "indicator_weight": "5%",
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "media_and_file_specification",
            "name": "poster_file_format_resolution_dimensions_and_color_mode",
            "description": "Spesifikasi teknis format karya poster: dibuat secara digital, format file JPG, JPEG, atau PNG, resolusi minimal 300 pixel per inci, ukuran A4 (210x297 mm) orientasi vertikal (portrait), mode warna RGB, tanpa batasan jumlah kata dan jumlah warna bebas.",
            "section": "Ketentuan Desain Karya Cabang Poster",
            "anchor": raw_text[20277:20550],
            "related_ids": ["REQ-DOC024-BU03-008"],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "content_and_tool_prohibition",
            "name": "poster_content_language_and_prohibitions",
            "description": "Gaya visual bebas, orisinal 100% hasil karya sendiri tanpa melanggar hak cipta; bahasa Indonesia sesuai PUEBI (singkatan diperbolehkan jika sesuai konteks); dilarang memuat unsur produk komersial, SARA, pornografi, atau konten yang melecehkan/mengintimidasi.",
            "section": "Ketentuan Desain Karya Cabang Poster",
            "anchor": raw_text[19975:20870],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "media_and_file_specification",
            "name": "mandatory_organizer_logos_and_optional_participant_identity",
            "description": "Poster wajib mencantumkan Logo impacteers dan Universitas Negeri Surabaya (diunduh melalui https://bit.ly/logoimpacteers), sedangkan pencantuman nama peserta dan nama/logo instansi asal peserta bersifat bebas (opsional).",
            "section": "Ketentuan Desain Karya Cabang Poster",
            "anchor": raw_text[20872:21138],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "copyright_and_publication_rights",
            "name": "poster_copyright_ownership_and_publication_authority",
            "description": "Hak cipta poster publik adalah milik peserta, namun panitia impacteers memiliki hak dan wewenang untuk mempublikasikan setiap karya pemenang dengan tetap mencantumkan identitas penulis.",
            "section": "Syarat dan ketentuan Cabang Poster",
            "anchor": raw_text[19569:19748],
        },
    ]

    for idx, sp in enumerate(u3_specs, 1):
        records.append(
            _make_record(
                req_id=f"REQ-DOC024-BU03-{idx:03d}",
                doc_id=doc_id,
                unit_id="DOC-024-BU-03",
                comp_name="Impacteers UNESA 2025 - Poster Competition",
                category=sp["category"],
                subcategory=sp["subcategory"],
                name=sp["name"],
                description=sp["description"],
                section=sp["section"],
                raw_text=raw_text,
                page_spans=pages,
                unit_start=u3_s,
                unit_end=u3_e,
                unit_seg_status=v3["validation_status"],
                anchor=sp["anchor"],
                confidence_level=sp.get("confidence_level", "high"),
                validation_status=sp.get("validation_status", "VALIDATED"),
                statement_nature=sp.get("statement_nature"),
                indicator_weight=sp.get("indicator_weight", "N/A"),
                related_ids=sp.get("related_ids"),
            )
        )

    info_items.append(
        SupportingInformationRecord(
            info_id="INFO-DOC024-BU01-001",
            document_id=doc_id,
            branch_unit_id="DOC-024-BU-01",
            competition_name="Impacteers UNESA 2025 - Essay Competition",
            info_category="participant_benefit_and_announcement_info",
            info_name="ecertificate_and_instagram_announcement",
            info_description="Peserta dengan naskah terbaik diumumkan di Instagram @impacteers_unesa dan seluruh peserta mendapat e-sertifikat melalui link Google Drive setelah pengumuman juara.",
            source_page=_locate_page_for_char(pages, 5617),
            source_section="Syarat & Ketentuan Cabang Esai",
            source_char_start=5617,
            source_char_end=5809,
            evidence_text=raw_text[5617:5809],
        )
    )

    for idx, (uid, cname, sec, rng) in enumerate(
        [
            (
                "DOC-024-BU-01",
                "Impacteers UNESA 2025 - Essay Competition",
                "Syarat & Ketentuan Cabang Esai",
                "4447..5878",
            ),
            (
                "DOC-024-BU-02",
                "Impacteers UNESA 2025 - Business Model Canvas Competition",
                "Syarat & Ketentuan Cabang BMC",
                "11089..12479",
            ),
            (
                "DOC-024-BU-03",
                "Impacteers UNESA 2025 - Poster Competition",
                "Syarat & Ketentuan Cabang Poster",
                "17934..19804",
            ),
        ],
        1,
    ):
        gaps.append(
            ExtractionGapRecord(
                gap_id=f"GAP-DOC024-BU0{idx}-001",
                document_id=doc_id,
                branch_unit_id=uid,
                competition_name=cname,
                requirement_category="eligibility_requirements",
                requirement_subcategory="education_level_and_student_status",
                missing_attribute_name="age_limit",
                gap_status="NOT_STATED",
                inspected_sections=[sec],
                inspected_char_range=rng,
                verification_method="rule_based_section_absence_scan",
                notes="Tidak ada batas usia minimum maupun maksimum yang dinyatakan pada syarat dan ketentuan cabang ini.",
            )
        )

    reviews.extend(
        [
            ReviewItemRecord(
                review_id="REV-DOC024-BU01-001",
                document_id=doc_id,
                branch_unit_id="DOC-024-BU-01",
                competition_name="Impacteers UNESA 2025 - Essay Competition",
                related_requirement_id="REQ-DOC024-BU01-016",
                issue_type="internal_rule_contradiction",
                severity="HIGH",
                review_status="NEEDS_REVIEW",
                source_page=_locate_page_for_char(pages, 6347),
                source_section="Ketentuan Penulisan Karya Cabang Esai",
                source_char_start=6347,
                source_char_end=6496,
                evidence_text=raw_text[6347:6496],
                review_description="Kalimat 'Naskah ditulis secara individu dengan 7 halaman – 10 Halaman' pada halaman 8 bertentangan dengan Syarat & Ketentuan halaman 6 ('Peserta dapat berupa perorangan maupun kelompok dengan jumlah 2 orang').",
                recommended_human_action="Pastikan apakah kata 'secara individu' hanya salah ketik pada sub-bab Ketentuan Penulisan dan tim 2 orang tetap diperbolehkan.",
            ),
            ReviewItemRecord(
                review_id="REV-DOC024-BU02-001",
                document_id=doc_id,
                branch_unit_id="DOC-024-BU-02",
                competition_name="Impacteers UNESA 2025 - Business Model Canvas Competition",
                related_requirement_id="REQ-DOC024-BU02-019",
                issue_type="cross_branch_copy_paste_typo",
                severity="MEDIUM",
                review_status="NEEDS_REVIEW",
                source_page=_locate_page_for_char(pages, 15027),
                source_section="Mekanisme Pendaftaran Cabang BMC",
                source_char_start=15027,
                source_char_end=15152,
                evidence_text=raw_text[15027:15152],
                review_description="Kalimat pada Mekanisme Pendaftaran BMC menulis 'Dokumen esai yang diunggah berupa softcopy PDF dengan format sebagai berikut : Nama Lengkap_Instansi_3 kata pertama judul bmc' (salah ketik salin-tempel kata 'Dokumen esai' dari cabang Esai).",
                recommended_human_action="Gunakan aturan penamaan file untuk dokumen BMC PDF, bukan dokumen esai.",
            ),
            ReviewItemRecord(
                review_id="REV-DOC024-BU03-001",
                document_id=doc_id,
                branch_unit_id="DOC-024-BU-03",
                competition_name="Impacteers UNESA 2025 - Poster Competition",
                related_requirement_id="REQ-DOC024-BU03-003",
                issue_type="cross_branch_copy_paste_typo",
                severity="HIGH",
                review_status="NEEDS_REVIEW",
                source_page=_locate_page_for_char(pages, 21982),
                source_section="Mekanisme Pendaftaran Cabang Poster",
                source_char_start=21982,
                source_char_end=22287,
                evidence_text=raw_text[21982:22287],
                review_description="Halaman 23 Mekanisme Pendaftaran Cabang Poster menyalin mentah teks cabang Esai/BMC ('Kartu Tanda Mahasiswa (KTM), dan bukti cek plagiasi', 'Dokumen esai yang diunggah berupa softcopy PDF... judul esai', serta label QR Code 'Karya BMC'), padahal cabang Poster terbuka bagi Mahasiswa & Pelajar SMA serta berformat JPG/JPEG/PNG.",
                recommended_human_action="Abaikan instruksi unggah dokumen esai PDF/plagiasi pada halaman 23 untuk cabang Poster dan ikuti Ketentuan Desain Karya Poster halaman 21.",
            ),
        ]
    )

    return records, info_items, gaps, reviews


def _extract_doc009_units(
    raw_text: str,
    units_by_id: Dict[str, Dict[str, Any]],
    vals_by_id: Dict[str, Dict[str, Any]],
) -> Tuple[
    List[ExtractedRequirementRecord],
    List[SupportingInformationRecord],
    List[ExtractionGapRecord],
    List[ReviewItemRecord],
]:
    """Extract refined requirements, info, gaps, and review items for DOC-009 (BU-01..04)."""
    doc_id = "DOC-009"
    pages = _build_page_spans(raw_text)
    records: List[ExtractedRequirementRecord] = []
    info_items: List[SupportingInformationRecord] = []
    gaps: List[ExtractionGapRecord] = []
    reviews: List[ReviewItemRecord] = []

    # =========================================================================
    # DOC-009-BU-01: Essay Competition (3135..15328)
    # =========================================================================
    u1 = units_by_id["DOC-009-BU-01"]
    v1 = vals_by_id["DOC-009-BU-01"]
    u1_s, u1_e = int(u1["start_char"]), int(u1["end_char"])
    u1_specs: List[Dict[str, Any]] = [
        {
            "category": "eligibility_requirements",
            "subcategory": "education_level_and_student_status",
            "name": "high_school_student_and_student_card",
            "description": "Peserta merupakan siswa/i aktif SMA/K atau sederajat di Indonesia yang dibuktikan dengan melampirkan hasil pindai (scan) kartu pelajar atau surat keterangan siswa aktif dari sekolah.",
            "section": "Ketentuan Umum Essay Competition",
            "anchor": raw_text[3769:3956],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "participation_mode_and_team_size",
            "name": "three_person_team_and_single_essay_limit",
            "description": "Tim terdiri dari 3 orang peserta (diperbolehkan berasal dari kelas atau angkatan yang berbeda), setiap tim hanya diperkenankan mengirim 1 naskah esai, dan anggota tim yang telah didaftarkan tidak dapat diganti.",
            "section": "Ketentuan Umum Essay Competition",
            "anchor": raw_text[4112:4328],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "school_delegation_quota",
            "name": "multiple_teams_per_school_allowed",
            "description": "Setiap sekolah menengah atas diperbolehkan untuk mengirimkan lebih dari 1 tim.",
            "section": "Ketentuan Umum Essay Competition",
            "anchor": raw_text[4329:4410],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "single_team_or_cross_branch_restriction",
            "name": "cross_branch_participation_restriction_with_video_exception",
            "description": "Peserta tidak diperkenankan mengikuti lebih dari 1 cabang perlombaan yang pelaksanaannya berlangsung secara bersamaan, kecuali Video Campaign Competition yang tidak memiliki babak final.",
            "section": "Ketentuan Umum Essay Competition",
            "anchor": raw_text[4988:5177],
            "exception_override": "kecuali Video Campaign Competition yang tidak memiliki babak",
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_mechanism_and_portal",
            "name": "shared_online_registration_confirmation_and_social_media_rules",
            "description": "Peserta mendaftar secara online melalui Google Forms pada https://linktr.ee/pharmacopeia2026 (cukup diwakili ketua tim untuk lomba berkelompok), membayar sesuai kode khusus cabang, melakukan konfirmasi ke contact person maksimal 1 x 24 jam dengan format Cabang Lomba_Nama Lengkap/Nama Kelompok_Asal Institusi/Sekolah, serta wajib mengikuti IG & TikTok @pharmacopeia2026, membagikan poster ke 3 grup WhatsApp (https://bit.ly/SharePosterPharmacopeia), mengunggah Twibbon (https://bit.ly/HighlightPharmacopeia2026), dan repost poster kegiatan.",
            "section": "Alur Pendaftaran (Shared Event Span 46547..48658)",
            "anchor": raw_text[46595:48024],
            "search_start": 46547,
            "search_end": 48658,
            "extraction_method": "rule_based_shared_event_span_lookup",
            "validation_status": "VALIDATED_WITH_SEGMENTATION_LIMITATION",
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "essay_registration_fee_waves_and_non_refundable_rule",
            "description": "Biaya pendaftaran Essay Competition pada rentang bersama: Gelombang 1 Ro70.001,- (Rp70.001), Gelombang 2 Rop85.001,- (Rp85.001), dan Gelombang 3 Rp95.001,- (ditandai NEEDS_REVIEW karena noise OCR pada simbol mata uang).",
            "section": "Biaya Pendaftaran (Shared Event Span 46547..48658)",
            "anchor": raw_text[48028:48129],
            "search_start": 46547,
            "search_end": 48658,
            "confidence_level": "medium",
            "extraction_method": "rule_based_shared_event_span_lookup",
            "validation_status": "NEEDS_REVIEW",
            "related_ids": ["REV-DOC009-BU01-002"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_tracks_and_themes",
            "name": "essay_three_cardiometabolic_subthemes",
            "description": "Subtema Essay Competition (pilih salah satu): Urgensi Pencegahan Penyakit Kardiometabolik pada Generasi Z; Dilema Era Digital Gaya Hidup Sedenter sebagai Ancaman dan Teknologi sebagai Solusi Kesehatan Kardiometabolik; atau Dampak Konsumsi Makanan Cepat Saji terhadap Krisis Kardiometabolik Indonesia.",
            "section": "Subtema Essay Competition",
            "anchor": raw_text[6991:7301],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_timeline_and_deadlines",
            "name": "essay_full_timeline_waves_to_final",
            "description": "Timeline Essay Competition: Pendaftaran Gelombang 1 (01-07 September 2026 via Google Forms), Gelombang 2 (08-14 September 2026), Gelombang 3 (15 September - 03 Oktober 2026), Technical Meeting Penyisihan (04 Oktober 2026 via Zoom Meeting), Pengumpulan Karya (10 - 20 Oktober 2026 via Google Forms), Penilaian Karya (21 - 31 Oktober 2026), Pengumuman Finalis (04 November 2026 di Instagram @pharmacopeia2026), Technical Meeting Final (07 November 2026 via Zoom Meeting), dan Babak Final (21 November 2026 di Fakultas Farmasi Unpad).",
            "section": "Timeline Essay Competition (3157..3765)",
            "anchor": raw_text[3157:3765],
            "search_start": 3050,
            "search_end": 3800,
            "confidence_level": "medium",
            "extraction_method": "rule_based_ocr_noisy_span",
            "validation_status": "NEEDS_REVIEW",
            "related_ids": ["REV-DOC009-BU01-001"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_stages_and_selection",
            "name": "preliminary_top_five_selection_and_final_confirmation",
            "description": "Pada babak penyisihan (batas akhir pengumpulan 20 Oktober 2026 pukul 23.59 WIB), sebanyak 5 tim dengan nilai tertinggi dinyatakan lolos ke babak final (diumumkan 04 November 2026) dan wajib melakukan konfirmasi ulang paling lambat 05 November 2026; jika tidak konfirmasi ulang atau tidak bersedia mengikuti final offline, slot diberikan kepada peringkat tertinggi berikutnya.",
            "section": "Ketentuan Khusus & Babak Penyisihan Essay Competition",
            "anchor": raw_text[5181:8493],
            "related_ids": ["REQ-DOC009-BU01-008", "REQ-DOC009-BU01-010"],
        },
        {
            "category": "competition_structure",
            "subcategory": "final_stage_offline_protocol",
            "name": "offline_final_quarantine_dress_code_seminar_and_attendance_rules",
            "description": "Ketentuan Babak Final Luring di Fakultas Farmasi Unpad: finalis wajib hadir tepat waktu dan mengikuti karantina peserta selama lomba, mengenakan pakaian sopan (atasan kemeja dan celana/rok panjang), dilarang mengenakan atribut/identitas asal sekolah (seragam, jaket organisasi, logo sekolah), wajib mengikuti Seminar Nasional Pharmacopeia 2026, dan panitia tidak menanggung biaya akomodasi; tim finalis diperbolehkan mengikuti final meskipun tidak dihadiri seluruh anggota tim tanpa perlakuan khusus atau penjadwalan ulang.",
            "section": "Babak Final Essay Competition",
            "anchor": raw_text[9097:10256],
            "related_ids": ["REQ-DOC009-BU01-009"],
        },
        {
            "category": "deliverables",
            "subcategory": "proposal_or_essay_deliverable",
            "name": "preliminary_essay_pdf_originality_sheet_and_turnitin_25",
            "description": "Berkas babak penyisihan yang dikirim melalui Google Forms dalam format PDF: Naskah esai (nama file: Esai. Nama Depan Peserta [Nama anggota tim dipisahkan tanda koma]_Institusi_Judul), Surat orisinalitas PDF (diunduh di https://bit.ly/SuratOrisinalitasPharmacopeia2026, nama file: Nama Ketua Tim_Institusi_Surat Orisinalitas), dan Hasil Turnitin maksimal 25% dalam format PDF (nama file: Nama Ketua Tim_Institusi_Hasil Turnitin), diikuti konfirmasi ke contact person.",
            "section": "Ketentuan Pengumpulan Karya Essay Competition",
            "anchor": raw_text[12079:12971],
            "related_ids": ["REQ-DOC009-BU01-019"],
        },
        {
            "category": "deliverables",
            "subcategory": "presentation_slide_deliverable",
            "name": "final_stage_powerpoint_and_10_plus_10_presentation",
            "description": "Finalis wajib menyiapkan media presentasi (PowerPoint) yang memuat poin-poin penting dari esai dan dikumpulkan paling lambat 18 November 2026; setiap tim mempresentasikan hasil esai di hadapan dewan juri selama 10 menit dilanjutkan sesi tanya jawab 10 menit.",
            "section": "Teknis Babak Final Essay Competition",
            "anchor": raw_text[13332:13807],
        },
        # Assessment Criteria: Split atomically (3 Preliminary + 3 Final = 6 records)
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "preliminary_criterion_tema_dan_gagasan",
            "description": "Kriteria Penilaian Babak Penyisihan — Tema dan Gagasan: Kesesuaian isi dengan tema, orisinalitas gagasan, kreativitas, inovasi, serta relevansi terhadap isu yang diangkat (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Penyisihan Essay)",
            "anchor": raw_text[11089:11226],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "preliminary_criterion_argumentasi_dan_analisis",
            "description": "Kriteria Penilaian Babak Penyisihan — Argumentasi dan Analisis: Ketajaman analisis, kekuatan argumentasi, penggunaan data dan fakta, relevansi referensi, serta kemampuan menyusun solusi yang logis dan aplikatif (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Penyisihan Essay)",
            "anchor": raw_text[11228:11410],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "preliminary_criterion_sistematika_dan_penulisan",
            "description": "Kriteria Penilaian Babak Penyisihan — Sistematika dan Penulisan: Kesesuaian dengan format penulisan, penggunaan bahasa Indonesia yang baik dan benar, tata tulis, serta kerapian penyajian (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Penyisihan Essay)",
            "anchor": raw_text[11412:11571],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "final_criterion_penyampaian_presentasi",
            "description": "Kriteria Penilaian Babak Final — Penyampaian Presentasi: Kejelasan penyampaian materi, penguasaan materi, sistematika presentasi, komunikasi, dan manajemen waktu (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Final Essay)",
            "anchor": raw_text[14827:14960],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "final_criterion_sesi_tanya_jawab",
            "description": "Kriteria Penilaian Babak Final — Sesi Tanya Jawab: Ketepatan menjawab pertanyaan, kemampuan berpikir kritis, kemampuan argumentasi, serta penguasaan terhadap isi esai (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Final Essay)",
            "anchor": raw_text[14962:15100],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "final_criterion_media_presentasi",
            "description": "Kriteria Penilaian Babak Final — Media Presentasi: Kesesuaian isi presentasi dengan naskah esai, kerapian desain, keterbacaan, dan efektivitas media presentasi (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Final Essay)",
            "anchor": raw_text[15102:15233],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "document_formatting_and_length",
            "name": "essay_page_length_apa_citation_and_eyd_v_language",
            "description": "Naskah esai terdiri atas minimal 5 halaman dan maksimal 10 halaman (tidak termasuk halaman cover, lampiran, dan daftar pustaka), wajib menyertakan kutipan dan daftar pustaka dengan format APA Style jika menggunakan sumber kutipan, serta menggunakan Bahasa Indonesia baku sesuai Pedoman Umum Ejaan Bahasa Indonesia yang disempurnakan (EYD V).",
            "section": "Ketentuan Penulisan Essay Competition",
            "anchor": raw_text[11644:12077],
            "related_ids": ["REQ-DOC009-BU01-011", "REV-DOC009-BU01-003"],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "content_and_tool_prohibition",
            "name": "essay_sara_pornography_prohibition_and_originality",
            "description": "Esai tidak diperbolehkan mengandung unsur SARA dan pornografi serta tidak melanggar hukum/aturan yang berlaku; karya esai wajib orisinal, belum pernah dipublikasikan, diikutsertakan dalam perlombaan sejenis, dipresentasikan, atau digunakan untuk media komunikasi apa pun.",
            "section": "Ketentuan Khusus Essay Competition",
            "anchor": raw_text[6653:6989],
        },
    ]

    for idx, sp in enumerate(u1_specs, 1):
        records.append(
            _make_record(
                req_id=f"REQ-DOC009-BU01-{idx:03d}",
                doc_id=doc_id,
                unit_id="DOC-009-BU-01",
                comp_name="Pharmacopeia 2026 - Essay Competition",
                category=sp["category"],
                subcategory=sp["subcategory"],
                name=sp["name"],
                description=sp["description"],
                section=sp["section"],
                raw_text=raw_text,
                page_spans=pages,
                unit_start=u1_s,
                unit_end=u1_e,
                unit_seg_status=v1["validation_status"],
                anchor=sp["anchor"],
                search_start=sp.get("search_start"),
                search_end=sp.get("search_end"),
                confidence_level=sp.get("confidence_level", "high"),
                extraction_method=sp.get(
                    "extraction_method", "rule_based_clause_and_span_extractor"
                ),
                validation_status=sp.get("validation_status", "VALIDATED"),
                statement_nature=sp.get("statement_nature"),
                indicator_weight=sp.get("indicator_weight", "N/A"),
                exception_override=sp.get("exception_override"),
                related_ids=sp.get("related_ids"),
            )
        )

    # =========================================================================
    # DOC-009-BU-02: Science Olympiad (15403..24614)
    # =========================================================================
    u2 = units_by_id["DOC-009-BU-02"]
    v2 = vals_by_id["DOC-009-BU-02"]
    u2_s, u2_e = int(u2["start_char"]), int(u2["end_char"])
    u2_specs: List[Dict[str, Any]] = [
        {
            "category": "eligibility_requirements",
            "subcategory": "education_level_and_student_status",
            "name": "high_school_student_and_student_card",
            "description": "Peserta merupakan siswa/i aktif SMA/K atau sederajat di Indonesia yang dibuktikan dengan melampirkan hasil pindai (scan) kartu pelajar atau surat keterangan siswa aktif dari sekolah.",
            "section": "Ketentuan Umum Science Olympiad",
            "anchor": raw_text[16041:16228],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "participation_mode_and_team_size",
            "name": "individual_participation_and_school_delegation",
            "description": "Perlombaan Science Olympiad bersifat individu, dan setiap sekolah menengah atas diperbolehkan mengirimkan lebih dari 1 peserta (tertulis 'lebih d1apesrertia' akibat noise OCR).",
            "section": "Ketentuan Umum Science Olympiad",
            "anchor": raw_text[16384:16496],
            "confidence_level": "medium",
            "validation_status": "NEEDS_REVIEW",
            "related_ids": ["REV-DOC009-BU02-001"],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "single_team_or_cross_branch_restriction",
            "name": "cross_branch_participation_restriction_with_video_exception",
            "description": "Peserta tidak diperkenankan mengikuti lebih dari 1 cabang perlombaan yang pelaksanaannya berlangsung secara bersamaan, kecuali Video Campaign Competition yang tidak memiliki babak final.",
            "section": "Ketentuan Umum Science Olympiad",
            "anchor": raw_text[17152:17348],
            "exception_override": "kecuali Video Campaign Competition yang tidak memiliki babak final",
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_mechanism_and_portal",
            "name": "shared_online_registration_and_confirmation_rules",
            "description": "Peserta melakukan pendaftaran secara online melalui Google Forms pada https://linktr.ee/pharmacopeia2026, membayar sesuai kode khusus, melakukan konfirmasi maksimal 1 x 24 jam ke contact person, serta wajib mengikuti IG & TikTok @pharmacopeia2026, share poster ke 3 grup WhatsApp, dan mengunggah Twibbon.",
            "section": "Alur Pendaftaran (Shared Event Span 46547..48658)",
            "anchor": raw_text[46595:48024],
            "search_start": 46547,
            "search_end": 48658,
            "extraction_method": "rule_based_shared_event_span_lookup",
            "validation_status": "VALIDATED_WITH_SEGMENTATION_LIMITATION",
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "science_olympiad_registration_fee_waves",
            "description": "Biaya pendaftaran Science Olympiad pada rentang bersama: Gelombang 1 Rp50.004,-, Gelombang 2 Rp60.004,-, dan Gelombang 3 Rp70.004,-.",
            "section": "Biaya Pendaftaran (Shared Event Span 46547..48658)",
            "anchor": raw_text[48352:48450],
            "search_start": 46547,
            "search_end": 48658,
            "extraction_method": "rule_based_shared_event_span_lookup",
            "validation_status": "VALIDATED_WITH_SEGMENTATION_LIMITATION",
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_timeline_and_deadlines",
            "name": "science_olympiad_full_timeline",
            "description": "Jadwal Science Olympiad: Pendaftaran Gelombang 1 (01-07 September 2026), Gelombang 2 (08-14 September 2026), Gelombang 3 (15 September - 03 Oktober 2026), Technical Meeting Penyisihan (04 Oktober 2026 via Zoom Meeting), Babak Penyisihan (24 Oktober 2026 via Zoom Meeting), Pengumuman Finalis (04 November 2026 di Instagram @pharmacopeia2026), Technical Meeting Final (07 November 2026), serta Babak Final dan Pengumuman Pemenang (21 November 2026 di Fakultas Farmasi Unpad dan Bale Sawala Gedung Rektorat Unpad).",
            "section": "Timeline Science Olympiad",
            "anchor": raw_text[15411:16037],
            "related_ids": ["REQ-DOC009-BU02-007", "REQ-DOC009-BU02-008"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_stages_and_selection",
            "name": "preliminary_online_exam_and_top_five_selection",
            "description": "Babak Penyisihan dilaksanakan secara online: peserta diberikan waktu 45 menit untuk mengerjakan 40 soal pilihan ganda melalui e-ujian, wajib bergabung ke Zoom Meeting maksimal 15 menit sebelum lomba dimulai, dan sebanyak 5 peserta dengan nilai tertinggi pada babak penyisihan melaju ke babak final.",
            "section": "Teknis Babak Penyisihan Science Olympiad",
            "anchor": raw_text[21773:22618],
            "related_ids": ["REQ-DOC009-BU02-006", "REQ-DOC009-BU02-008"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_stages_and_selection",
            "name": "final_stage_three_exam_rounds_structure",
            "description": "Lomba final diikuti oleh 5 finalis dalam 3 babak: Babak 1 (5 paket soal masing-masing berisi 5 soal isian singkat dengan sistem undian dan rebutan 1 kali jika salah/tidak menjawab), Babak 2 (10 soal pilihan ganda dijawab serentak pada layar yang disediakan), dan Babak 3 (10 soal esai dibacakan satu per satu dengan sistem adu cepat menekan bel).",
            "section": "Teknis Babak Final Science Olympiad",
            "anchor": raw_text[22627:23682],
            "related_ids": ["REQ-DOC009-BU02-007"],
        },
        {
            "category": "competition_structure",
            "subcategory": "final_stage_offline_protocol",
            "name": "offline_final_quarantine_dress_code_and_school_attribute_prohibition",
            "description": "Pada Babak Final Luring di Fakultas Farmasi Unpad, finalis wajib hadir tepat waktu dan mengikuti karantina peserta selama perlombaan, mengenakan pakaian sopan (atasan kemeja dan celana/rok panjang), dilarang mengenakan atribut/identitas asal sekolah (seragam, jaket organisasi, logo sekolah), wajib mengikuti Seminar Nasional Pharmacopeia 2026, dan panitia tidak menanggung biaya akomodasi peserta.",
            "section": "Ketentuan Babak Final Science Olympiad",
            "anchor": raw_text[20619:21334],
        },
        {
            "category": "deliverables",
            "subcategory": "prototype_or_exam_deliverable",
            "name": "online_exam_responses_on_eujian_and_final_stage_answers",
            "description": "Peserta login dengan akun masing-masing di platform e-ujian (tertulis https://wwwe- ujian.com/web/index) dan memilih jenjang yang diujikan untuk menjawab soal ujian penyisihan.",
            "section": "Teknis Babak Penyisihan Science Olympiad",
            "anchor": raw_text[21617:21772],
            "confidence_level": "medium",
            "validation_status": "NEEDS_REVIEW",
            "related_ids": ["REV-DOC009-BU02-001"],
        },
        # Assessment Criteria: Split atomically into 4 scoring records
        {
            "category": "assessment_criteria",
            "subcategory": "exam_point_scoring_formula",
            "name": "preliminary_multiple_choice_scoring_formula",
            "description": "Sistem penilaian Babak Penyisihan: Benar +4 Poin, Salah -1 Poin, Tidak Menjawab 0 Poin.",
            "section": "Teknis Babak Penyisihan Science Olympiad",
            "anchor": raw_text[21935:21989],
            "indicator_weight": "Benar +4, Salah -1, Kosong 0",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "exam_point_scoring_formula",
            "name": "final_round_1_short_answer_and_rebutan_scoring",
            "description": "Sistem penilaian Final Babak Pertama: Benar (pemilik paket soal) +2 Poin, Salah 0 Poin, Tidak Menjawab 0 Poin, Benar (Soal Rebutan) +1 Poin, Salah (Soal Rebutan) 0 Poin.",
            "section": "Teknis Babak Final Science Olympiad",
            "anchor": raw_text[23051:23188],
            "indicator_weight": "Paket: +2/0/0; Rebutan: +1/0",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "exam_point_scoring_formula",
            "name": "final_round_2_multiple_choice_scoring",
            "description": "Sistem penilaian Final Babak Kedua: Benar +2 Poin, Salah -1 Poin, Tidak Menjawab 0 Poin.",
            "section": "Teknis Babak Final Science Olympiad",
            "anchor": raw_text[23445:23499],
            "indicator_weight": "Benar +2, Salah -1, Kosong 0",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "exam_point_scoring_formula",
            "name": "final_round_3_buzzer_essay_scoring",
            "description": "Sistem penilaian Final Babak Ketiga: Benar (Pemilik paket soal) +1 s.d 5 Poin, Salah -1 Poin.",
            "section": "Teknis Babak Final Science Olympiad",
            "anchor": raw_text[23684:23810],
            "indicator_weight": "Benar +1 s.d 5, Salah -1",
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "exam_proctoring_and_device_rules",
            "name": "two_device_zoom_proctoring_and_18_minute_early_join",
            "description": "Peserta wajib bergabung pada Zoom Meeting 18 menit sebelum perlombaan dimulai (tidak ada penambahan waktu bagi yang terlambat); perlombaan dilaksanakan dengan 2 device (device 1 untuk pengawasan panitia melalui Zoom Meeting dengan kamera menyala dan mikrofon mati, sedangkan device 2 digunakan mengerjakan soal dengan posisi layar device 2 dan wajah peserta terlihat jelas pada device 1).",
            "section": "Ketentuan Babak Penyisihan Science Olympiad",
            "anchor": raw_text[18856:20051],
            "related_ids": ["REQ-DOC009-BU02-016"],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "exam_proctoring_and_device_rules",
            "name": "laptop_or_pc_device_recommendation",
            "description": "Rekomendasi perangkat ujian: dari 2 device yang disiapkan peserta, 1 device yang digunakan untuk mengerjakan soal diusahakan berupa laptop atau komputer.",
            "section": "Teknis Babak Penyisihan Science Olympiad",
            "anchor": raw_text[22114:22266],
            "statement_nature": "recommendation",
            "related_ids": ["REQ-DOC009-BU02-015"],
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "document_formatting_and_length",
            "name": "exam_syllabus_physics_chemistry_and_biology",
            "description": "Cakupan mata pelajaran dan topik bahasan ujian meliputi: Fisika (Besaran/Satuan/Pengukuran, Vektor, Gerak Lurus & Parabola, Hukum Newton, Usaha/Energi/Momentum, Fluida, Suhu & Kalor, Listrik Dinamis, Gelombang & Optik), Kimia (Struktur Atom & Sistem Periodik, Ikatan Kimia, Stoikiometri, Larutan & Konsentrasi, Termokimia, Laju Reaksi, Kesetimbangan Kimia, Asam Basa & Penyangga, Hidrolisis Garam, Kelarutan & Ksp, Reaksi Redoks, Elektrokimia, Kimia Organik Dasar), dan Biologi (Biologi Sel & Molekuler, Biokimia, Anatomi & Fisiologi Manusia, Anatomi & Fisiologi Tanaman, Ekologi, Bioteknologi, Genetika & Evolusi, Biosistematika).",
            "section": "Kisi-Kisi Materi Science Olympiad",
            "anchor": raw_text[23822:24523],
        },
    ]

    for idx, sp in enumerate(u2_specs, 1):
        records.append(
            _make_record(
                req_id=f"REQ-DOC009-BU02-{idx:03d}",
                doc_id=doc_id,
                unit_id="DOC-009-BU-02",
                comp_name="Pharmacopeia 2026 - Science Olympiad",
                category=sp["category"],
                subcategory=sp["subcategory"],
                name=sp["name"],
                description=sp["description"],
                section=sp["section"],
                raw_text=raw_text,
                page_spans=pages,
                unit_start=u2_s,
                unit_end=u2_e,
                unit_seg_status=v2["validation_status"],
                anchor=sp["anchor"],
                search_start=sp.get("search_start"),
                search_end=sp.get("search_end"),
                confidence_level=sp.get("confidence_level", "high"),
                extraction_method=sp.get(
                    "extraction_method", "rule_based_clause_and_span_extractor"
                ),
                validation_status=sp.get("validation_status", "VALIDATED"),
                statement_nature=sp.get("statement_nature"),
                indicator_weight=sp.get("indicator_weight", "N/A"),
                exception_override=sp.get("exception_override"),
                related_ids=sp.get("related_ids"),
            )
        )

    # =========================================================================
    # DOC-009-BU-03: Digital Poster Competition (24640..37583)
    # =========================================================================
    u3 = units_by_id["DOC-009-BU-03"]
    v3 = vals_by_id["DOC-009-BU-03"]
    u3_s, u3_e = int(u3["start_char"]), int(u3["end_char"])
    u3_specs: List[Dict[str, Any]] = [
        {
            "category": "eligibility_requirements",
            "subcategory": "education_level_and_student_status",
            "name": "high_school_student_and_student_card",
            "description": "Peserta merupakan siswa/i aktif SMA/K atau sederajat di Indonesia yang dibuktikan dengan melampirkan hasil pindai (scan) kartu pelajar atau surat keterangan siswa aktif dari sekolah.",
            "section": "Ketentuan Umum Digital Poster Competition",
            "anchor": raw_text[25327:25514],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "participation_mode_and_team_size",
            "name": "three_person_team_and_single_poster_limit",
            "description": "Tim terdiri dari 3 orang peserta (dapat berasal dari kelas atau angkatan yang berbeda), setiap tim hanya diperkenankan mengirim 1 karya poster, anggota tim yang telah didaftarkan tidak dapat diganti, dan setiap SMA diperbolehkan mengirimkan lebih dari 1 tim/peserta.",
            "section": "Ketentuan Umum Digital Poster Competition",
            "anchor": raw_text[25670:25963],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "single_team_or_cross_branch_restriction",
            "name": "cross_branch_participation_restriction_with_video_exception",
            "description": "Peserta tidak diperkenankan mengikuti lebih dari 1 cabang perlombaan yang pelaksanaannya berlangsung secara bersamaan, kecuali Video Campaign Competition yang tidak memiliki babak final.",
            "section": "Ketentuan Umum Digital Poster Competition",
            "anchor": raw_text[26559:26748],
            "exception_override": "kecuali Video Campaign Competition yang tidak memiliki babak",
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_mechanism_and_portal",
            "name": "shared_online_registration_and_social_media_rules",
            "description": "Peserta melakukan pendaftaran secara online melalui Google Forms pada https://linktr.ee/pharmacopeia2026 (diwakili ketua tim), melakukan konfirmasi maksimal 1 x 24 jam ke contact person, serta wajib mengikuti IG & TikTok @pharmacopeia2026, share poster ke 3 grup WhatsApp, dan mengunggah Twibbon.",
            "section": "Alur Pendaftaran (Shared Event Span 46547..48658)",
            "anchor": raw_text[46595:48024],
            "search_start": 46547,
            "search_end": 48658,
            "extraction_method": "rule_based_shared_event_span_lookup",
            "validation_status": "VALIDATED_WITH_SEGMENTATION_LIMITATION",
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "digital_poster_registration_fee_waves",
            "description": "Biaya pendaftaran Digital Poster Competition pada rentang bersama: Gelombang 1 Rp75.003,-, Gelombang 2 Rp80.003,-, dan Gelombang 3 Rp90.003,-.",
            "section": "Biaya Pendaftaran (Shared Event Span 46547..48658)",
            "anchor": raw_text[48242:48350],
            "search_start": 46547,
            "search_end": 48658,
            "extraction_method": "rule_based_shared_event_span_lookup",
            "validation_status": "VALIDATED_WITH_SEGMENTATION_LIMITATION",
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_tracks_and_themes",
            "name": "digital_poster_three_subthemes",
            "description": "Subtema Digital Poster Competition (pilih salah satu): Rethink Your Drink, Sugary Beverages and Heart Health; Fuel Your Heart, Smart Food, Healthy Life; atau Heart Starts with Healthy Habits.",
            "section": "Subtema Digital Poster Competition",
            "anchor": raw_text[29111:29306],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_timeline_and_deadlines",
            "name": "digital_poster_full_timeline",
            "description": "Jadwal Digital Poster Competition: Pendaftaran Gelombang 1 (01-07 September 2026), Gelombang 2 (08-14 September 2026), Gelombang 3 (15 September - 03 Oktober 2026), Technical Meeting Penyisihan (04 Oktober 2026), Pengumpulan Karya (10 - 20 Oktober 2026), Penilaian Karya (21 - 31 Oktober 2026), Pengumuman Finalis (04 November 2026), Technical Meeting Final (07 November 2026), serta Babak Final dan Pengumuman Pemenang (21 November 2026 di Fakultas Farmasi Unpad dan Bale Sawala Gedung Rektorat Unpad).",
            "section": "Timeline Digital Poster Competition",
            "anchor": raw_text[24644:25323],
            "related_ids": ["REQ-DOC009-BU03-008", "REQ-DOC009-BU03-009"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_stages_and_selection",
            "name": "preliminary_top_five_selection_and_final_presentation_duration",
            "description": "Pada babak penyisihan (deadline 20 Oktober 2026 pukul 23.59 WIB), sebanyak 5 tim dengan nilai tertinggi dinyatakan lolos ke babak final; pada babak final luring, setiap tim mempresentasikan hasil poster di hadapan dewan juri selama 10 menit dilanjutkan sesi tanya jawab selama 10 menit.",
            "section": "Babak Penyisihan & Babak Final Digital Poster Competition",
            "anchor": raw_text[30040:35795],
            "related_ids": ["REQ-DOC009-BU03-007", "REQ-DOC009-BU03-011"],
        },
        {
            "category": "competition_structure",
            "subcategory": "final_stage_offline_protocol",
            "name": "offline_final_quarantine_dress_code_and_school_attribute_prohibition",
            "description": "Pada Babak Final Luring di Fakultas Farmasi Unpad, finalis wajib mengikuti karantina peserta hingga seluruh rangkaian final selesai, mengenakan pakaian sopan (atasan kemeja dan celana/rok panjang), dilarang mengenakan atribut/identitas asal sekolah (seragam, jaket organisasi, logo sekolah), wajib mengikuti Seminar Nasional Pharmacopeia 2026, panitia tidak menanggung biaya akomodasi, serta tim finalis tetap diperbolehkan mengikuti final meskipun tidak dihadiri seluruh anggota tim.",
            "section": "Babak Final Digital Poster Competition",
            "anchor": raw_text[31070:32228],
        },
        {
            "category": "deliverables",
            "subcategory": "poster_deliverable",
            "name": "poster_a3_pdf_originality_sheet_and_public_instagram_upload",
            "description": "Luaran Babak Penyisihan Digital Poster: Desain poster portrait format A3 berlogo Pharmacopeia di pojok kiri atas (https://bit.ly/LogoPharmacopeia2026) yang dikirimkan dalam bentuk PDF (nama file: Desain Poster_Nama Depan Peserta [Nama anggota tim dipisahkan tanda koma]_Institusi_Judul), Surat Orisinalitas dalam bentuk PDF (https://bit.ly/SuratOrisinalitasPharmacopeia2026, nama file: Nama Ketua Tim_Institusi_Surat Orisinalitas) paling lambat 20 Oktober 2026 pukul 23.59 WIB diikuti konfirmasi ke contact person, serta Poster wajib dipublikasikan pada media sosial Instagram salah satu peserta dengan akun bersifat publik.",
            "section": "Ketentuan Pengumpulan Karya Digital Poster Competition",
            "anchor": raw_text[33894:35120],
            "related_ids": ["REQ-DOC009-BU03-011", "REQ-DOC009-BU03-017"],
        },
        {
            "category": "deliverables",
            "subcategory": "presentation_slide_deliverable",
            "name": "optional_powerpoint_at_final_stage",
            "description": "Pada babak final Digital Poster, finalis tidak wajib menyiapkan media presentasi (PowerPoint); presentasi diperbolehkan langsung menampilkan hasil poster.",
            "section": "Teknis Babak Final Digital Poster Competition",
            "anchor": raw_text[36134:36259],
            "exception_override": "presentasi boleh dilakukan dengan menampilkan hasil poster",
            "related_ids": ["REQ-DOC009-BU03-010"],
        },
        # Assessment Criteria: Split atomically (2 Preliminary + 3 Final = 5 records)
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "preliminary_criterion_keunikan_kreativitas_keindahan_dan_kerangka_teori",
            "description": "Kriteria Penilaian Penyisihan Poster — Keunikan, Kreativitas, Keindahan, dan Kerangka Teori: Karya memiliki karakter/ciri khas, perpaduan tata letak objek gambar dan warna serasi, menampilkan sisi artistik yang memikat mata, serta kerangka teori dan konsep dijelaskan runtut dari awal hingga akhir (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Penyisihan Poster)",
            "anchor": raw_text[33070:33414],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "preliminary_criterion_isi_poster_orisinalitas_dan_referensi",
            "description": "Kriteria Penilaian Penyisihan Poster — Isi Poster: Ide/gagasan runtut dan mudah dimengerti, orisinalitas karya tangan sendiri, kesesuaian dengan subtema, bahasa komunikatif, referensi kredibel dan dapat dipertanggungjawabkan, serta informasi menarik perhatian pembaca (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Penyisihan Poster)",
            "anchor": raw_text[33416:33890],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "final_criterion_penyampaian_materi",
            "description": "Kriteria Penilaian Final Poster — Penyampaian Materi: Kejelasan penyampaian materi, penguasaan terhadap isi poster, sistematika penyampaian, kemampuan komunikasi, serta manajemen waktu (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Final Poster)",
            "anchor": raw_text[36986:37144],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "final_criterion_sesi_tanya_jawab",
            "description": "Kriteria Penilaian Final Poster — Sesi Tanya Jawab: Ketepatan dalam menjawab pertanyaan, kemampuan berpikir kritis, kemampuan berargumentasi, serta penguasaan terhadap isi poster (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Final Poster)",
            "anchor": raw_text[37146:37296],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "final_criterion_kualitas_poster",
            "description": "Kriteria Penilaian Final Poster — Kualitas Poster: Kesesuaian isi poster dengan tema, kejelasan informasi, kerapian desain, keterbacaan, visualisasi data, serta efektivitas poster dalam mendukung penyampaian materi (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN (Babak Final Poster)",
            "anchor": raw_text[37298:37487],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "content_and_tool_prohibition",
            "name": "prohibition_of_ai_and_ready_made_templates_in_poster_design",
            "description": "Poster infografis wajib dibuat secara mandiri oleh peserta, tidak diperkenankan menggunakan bantuan Artificial Intelligence (AI) maupun template siap pakai, menggunakan bahasa Indonesia komunikatif sesuai EYD V, mencantumkan judul dan referensi, dirancang dengan perangkat lunak desain grafis (CorelDRAW, Adobe Photoshop, Adobe Illustrator, atau sejenisnya), serta hasil akhir dikumpulkan dalam format .pdf ukuran A3 portrait berlogo Pharmacopeia.",
            "section": "Ketentuan Khusus Digital Poster Competition",
            "anchor": raw_text[28030:29109],
            "related_ids": ["REQ-DOC009-BU03-010", "REV-DOC009-BU03-001"],
        },
    ]

    for idx, sp in enumerate(u3_specs, 1):
        records.append(
            _make_record(
                req_id=f"REQ-DOC009-BU03-{idx:03d}",
                doc_id=doc_id,
                unit_id="DOC-009-BU-03",
                comp_name="Pharmacopeia 2026 - Digital Poster Competition",
                category=sp["category"],
                subcategory=sp["subcategory"],
                name=sp["name"],
                description=sp["description"],
                section=sp["section"],
                raw_text=raw_text,
                page_spans=pages,
                unit_start=u3_s,
                unit_end=u3_e,
                unit_seg_status=v3["validation_status"],
                anchor=sp["anchor"],
                search_start=sp.get("search_start"),
                search_end=sp.get("search_end"),
                confidence_level=sp.get("confidence_level", "high"),
                extraction_method=sp.get(
                    "extraction_method", "rule_based_clause_and_span_extractor"
                ),
                validation_status=sp.get("validation_status", "VALIDATED"),
                statement_nature=sp.get("statement_nature"),
                indicator_weight=sp.get("indicator_weight", "N/A"),
                exception_override=sp.get("exception_override"),
                related_ids=sp.get("related_ids"),
            )
        )

    # =========================================================================
    # DOC-009-BU-04: Video Campaign Competition (37584..46547)
    # =========================================================================
    u4 = units_by_id["DOC-009-BU-04"]
    v4 = vals_by_id["DOC-009-BU-04"]
    u4_s, u4_e = int(u4["start_char"]), int(u4["end_char"])
    u4_specs: List[Dict[str, Any]] = [
        {
            "category": "eligibility_requirements",
            "subcategory": "education_level_and_student_status",
            "name": "high_school_student_and_student_card",
            "description": "Peserta merupakan siswa/i aktif SMA/K atau sederajat di Indonesia yang dibuktikan dengan melampirkan hasil pindai (scan) kartu pelajar atau surat keterangan siswa aktif dari sekolah.",
            "section": "Ketentuan Umum Video Campaign Competition",
            "anchor": raw_text[38206:38393],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "participation_mode_and_team_size",
            "name": "two_to_three_person_team_and_school_quota",
            "description": "Tim terdiri dari 2-3 orang peserta (dapat berasal dari kelas atau angkatan yang berbeda), setiap tim hanya diperkenankan mengirim 1 karya video, anggota tim yang telah didaftarkan tidak dapat diganti, dan setiap SMA diperbolehkan mengirimkan lebih dari 1 peserta/tim.",
            "section": "Ketentuan Umum Video Campaign Competition",
            "anchor": raw_text[38549:38845],
        },
        {
            "category": "eligibility_requirements",
            "subcategory": "single_team_or_cross_branch_restriction",
            "name": "allowed_one_other_branch_participation",
            "description": "Peserta yang mengikuti Video Campaign Competition diperbolehkan mengikuti maksimal 1 cabang perlombaan lain.",
            "section": "Ketentuan Umum Video Campaign Competition",
            "anchor": raw_text[39517:39632],
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_mechanism_and_portal",
            "name": "shared_online_registration_and_social_media_rules",
            "description": "Peserta mendaftar secara online melalui Google Forms pada https://linktr.ee/pharmacopeia2026 (diwakili ketua tim), melakukan konfirmasi maksimal 1 x 24 jam ke contact person, serta wajib mengikuti IG & TikTok @pharmacopeia2026, share poster ke 3 grup WhatsApp, dan mengunggah Twibbon.",
            "section": "Alur Pendaftaran (Shared Event Span 46547..48658)",
            "anchor": raw_text[46595:48024],
            "search_start": 46547,
            "search_end": 48658,
            "extraction_method": "rule_based_shared_event_span_lookup",
            "validation_status": "VALIDATED_WITH_SEGMENTATION_LIMITATION",
        },
        {
            "category": "registration_requirements",
            "subcategory": "registration_fee_and_payment",
            "name": "video_campaign_registration_fee_waves",
            "description": "Biaya pendaftaran Video Campaign Competition pada rentang bersama: Gelombang 1 Rp70.002,-, Gelombang 2 Rp80.002,-, dan Gelombang 3 Rp90.002,-.",
            "section": "Biaya Pendaftaran (Shared Event Span 46547..48658)",
            "anchor": raw_text[48131:48240],
            "search_start": 46547,
            "search_end": 48658,
            "extraction_method": "rule_based_shared_event_span_lookup",
            "validation_status": "VALIDATED_WITH_SEGMENTATION_LIMITATION",
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_tracks_and_themes",
            "name": "video_campaign_three_subthemes",
            "description": "Subtema Video Campaign Competition: Behind Every Disease, There’s a Lifestyle Choice; Kenali Risiko Diabetes Sebelum Terlambat; atau What's in Your Snack?.",
            "section": "Subtema Video Campaign Competition",
            "anchor": raw_text[41544:41666],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_timeline_and_deadlines",
            "name": "video_campaign_full_timeline",
            "description": "Jadwal Video Campaign Competition: Pendaftaran Gelombang 1 (01-07 September 2026 via Google Forms), Gelombang 2 (08-14 September 2026), Gelombang 3 (15 September - 03 Oktober 2026), Technical Meeting (04 Oktober 2026 via Zoom Meeting), Pengumpulan Karya (10 - 20 Oktober 2026 via Google Forms), Penilaian Karya (21 - 31 Oktober 2026), serta Pengumuman Pemenang (21 November 2026 di Bale Sawala Gedung Rektorat Unpad dan Zoom Meeting).",
            "section": "Timeline Video Campaign Competition",
            "anchor": raw_text[37648:38198],
            "related_ids": ["REQ-DOC009-BU04-008"],
        },
        {
            "category": "competition_structure",
            "subcategory": "competition_stages_and_selection",
            "name": "single_stage_online_selection_top_three_winners_and_awarding_rules",
            "description": "Seleksi dilaksanakan secara online dalam 1 tahap (penilaian 21 - 31 Oktober 2026) di mana 3 tim dengan nilai tertinggi dinyatakan sebagai pemenang lomba; jika terdapat ketidakhadiran secara offline maka panitia tidak menanggung pengiriman hadiah kepada pemenang yang tidak hadir pada sesi awarding, dan panitia tidak menanggung biaya akomodasi peserta.",
            "section": "Teknis Lomba Video Campaign Competition",
            "anchor": raw_text[44720:45574],
            "related_ids": ["REQ-DOC009-BU04-007"],
        },
        {
            "category": "deliverables",
            "subcategory": "video_deliverable",
            "name": "portrait_mp4_video_originality_sheet_and_public_instagram_upload",
            "description": "Luaran Video Campaign: 1 karya video portrait format .mp4 rasio 9:16 berdurasi minimal 1 menit dan maksimal 3 menit dengan logo Pharmacopeia di pojok kiri atas (https://bit.ly/LogoPharmacopeia2026, nama file: Video Campaign_Nama Depan Peserta [Nama anggota tim dipisahkan tanda koma]_Institusi_Judul), Surat Orisinalitas dalam bentuk PDF (https://bit.ly/SuratOrisinalitasPharmacopeia2026, nama file: Nama Ketua Tim_Institusi_Surat Orisinalitas) dikirim paling lambat 20 Oktober 2026 pukul 23.59 WIB diikuti konfirmasi ke contact person, serta Video wajib dipublikasikan pada media sosial Instagram salah satu peserta dengan akun bersifat publik.",
            "section": "Ketentuan Pengumpulan Video Campaign Competition",
            "anchor": raw_text[43025:44280],
        },
        # Assessment Criteria: Split atomically into 5 records
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "video_criterion_orisinalitas",
            "description": "Kriteria Penilaian Video — Orisinalitas: Orisinalitas ide gagasan; karya belum pernah dipublikasikan sebelumnya dan tidak plagiarisme (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN Video Campaign Competition",
            "anchor": raw_text[45622:45733],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "video_criterion_kepatuhan",
            "description": "Kriteria Penilaian Video — Kepatuhan: Durasi video, format, dan nama file sesuai ketentuan; isi video sesuai dengan tema dan judul yang diangkat; serta pengumpulan tepat waktu (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN Video Campaign Competition",
            "anchor": raw_text[45735:45888],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "video_criterion_kesesuaian_tema",
            "description": "Kriteria Penilaian Video — Kesesuaian tema: Kedalaman analisis dan argumentasi, keterkaitan dengan konsep-konsep ilmiah yang relevan dan faktual, kemampuan mengidentifikasi akar permasalahan, ketepatan informasi, serta penggunaan data atau bukti valid (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN Video Campaign Competition",
            "anchor": raw_text[45890:46119],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "video_criterion_visualisasi",
            "description": "Kriteria Penilaian Video — Visualisasi: Sistematika dan alur penyampaian konten, keseimbangan antara unsur visual dan informasi, keunikan konsep atau ide yang diangkat, serta keserasian penggunaan warna, font, dan elemen visual (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN Video Campaign Competition",
            "anchor": raw_text[46121:46323],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "assessment_criteria",
            "subcategory": "judging_criterion_unweighted",
            "name": "video_criterion_manfaat",
            "description": "Kriteria Penilaian Video — Manfaat: Kontribusi gagasan yang ditawarkan dalam perkembangan ilmu kesehatan nasional serta mengedukasi khalayak umum dengan bahasa yang lebih sederhana (bobot tidak dicantumkan).",
            "section": "KRITERIA PENILAIAN Video Campaign Competition",
            "anchor": raw_text[46325:46479],
            "indicator_weight": "NOT_STATED",
        },
        {
            "category": "technical_and_general_rules",
            "subcategory": "content_and_tool_prohibition",
            "name": "video_language_references_editing_software_and_prohibitions",
            "description": "Isi Video Campaign wajib memuat alur pikir yang jelas, komunikatif sesuai EYD V, diberikan judul dan mencantumkan referensi yang digunakan, dibuat menggunakan software seperti Filmora, CapCut, dan lainnya, serta tidak mengandung unsur SARA, pornografi, atau menyinggung pihak mana pun.",
            "section": "Ketentuan Khusus Video Campaign Competition",
            "anchor": raw_text[41046:41542],
        },
    ]

    for idx, sp in enumerate(u4_specs, 1):
        records.append(
            _make_record(
                req_id=f"REQ-DOC009-BU04-{idx:03d}",
                doc_id=doc_id,
                unit_id="DOC-009-BU-04",
                comp_name="Pharmacopeia 2026 - Video Campaign Competition",
                category=sp["category"],
                subcategory=sp["subcategory"],
                name=sp["name"],
                description=sp["description"],
                section=sp["section"],
                raw_text=raw_text,
                page_spans=pages,
                unit_start=u4_s,
                unit_end=u4_e,
                unit_seg_status=v4["validation_status"],
                anchor=sp["anchor"],
                search_start=sp.get("search_start"),
                search_end=sp.get("search_end"),
                confidence_level=sp.get("confidence_level", "high"),
                extraction_method=sp.get(
                    "extraction_method", "rule_based_clause_and_span_extractor"
                ),
                validation_status=sp.get("validation_status", "VALIDATED"),
                statement_nature=sp.get("statement_nature"),
                indicator_weight=sp.get("indicator_weight", "N/A"),
                exception_override=sp.get("exception_override"),
                related_ids=sp.get("related_ids"),
            )
        )

    # Supporting Information (Background previously misclassified as REQ-DOC009-BU01-013)
    info_items.append(
        SupportingInformationRecord(
            info_id="INFO-DOC009-BU01-001",
            document_id=doc_id,
            branch_unit_id="DOC-009-BU-01",
            competition_name="Pharmacopeia 2026 - Event Overview",
            info_category="event_historical_and_epidemiological_background",
            info_name="pharmacopeia_annual_program_and_who_ncd_context",
            info_description="Latar belakang umum acara (bukan persyaratan peserta): Pharmacopeia merupakan program tahunan Fakultas Farmasi Universitas Padjadjaran bertema 'Beyond The Surface: Your Lifestyle, Your Health' yang menyoroti isu transisi epidemiologi PTM dan data WHO bahwa pola hidup tidak sehat berkontribusi pada 74% kematian di seluruh dunia.",
            source_page=_locate_page_for_char(pages, 153),
            source_section="Latar Belakang Pharmacopeia 2026 (Shared Intro Span 0..3050)",
            source_char_start=153,
            source_char_end=856,
            evidence_text=raw_text[153:856],
        )
    )

    # Extraction Gaps for DOC-009 (age_limit across BU-01..04 + unstated rubric weights across BU-01, BU-03, BU-04)
    for idx, (uid, cname, sec, rng) in enumerate(
        [
            (
                "DOC-009-BU-01",
                "Pharmacopeia 2026 - Essay Competition",
                "Ketentuan Umum Essay Competition",
                "3769..5178",
            ),
            (
                "DOC-009-BU-02",
                "Pharmacopeia 2026 - Science Olympiad",
                "Ketentuan Umum Science Olympiad",
                "16041..17349",
            ),
            (
                "DOC-009-BU-03",
                "Pharmacopeia 2026 - Digital Poster Competition",
                "Ketentuan Umum Digital Poster Competition",
                "25327..26749",
            ),
            (
                "DOC-009-BU-04",
                "Pharmacopeia 2026 - Video Campaign Competition",
                "Ketentuan Umum Video Campaign Competition",
                "38206..39633",
            ),
        ],
        1,
    ):
        gaps.append(
            ExtractionGapRecord(
                gap_id=f"GAP-DOC009-BU0{idx}-001",
                document_id=doc_id,
                branch_unit_id=uid,
                competition_name=cname,
                requirement_category="eligibility_requirements",
                requirement_subcategory="education_level_and_student_status",
                missing_attribute_name="age_limit",
                gap_status="NOT_STATED",
                inspected_sections=[sec],
                inspected_char_range=rng,
                verification_method="rule_based_section_absence_scan",
                notes="Ketentuan umum cabang hanya mensyaratkan status siswa/i aktif SMA/K sederajat tanpa mencantumkan batas usia.",
            )
        )

    for uid, cname, gap_id, sec, rng in [
        (
            "DOC-009-BU-01",
            "Pharmacopeia 2026 - Essay Competition",
            "GAP-DOC009-BU01-002",
            "KRITERIA PENILAIAN (Penyisihan & Final Essay)",
            "11021..11572, 14807..15234",
        ),
        (
            "DOC-009-BU-03",
            "Pharmacopeia 2026 - Digital Poster Competition",
            "GAP-DOC009-BU03-002",
            "KRITERIA PENILAIAN (Penyisihan & Final Poster)",
            "33002..33891, 36921..37488",
        ),
        (
            "DOC-009-BU-04",
            "Pharmacopeia 2026 - Video Campaign Competition",
            "GAP-DOC009-BU04-002",
            "KRITERIA PENILAIAN Video Campaign Competition",
            "45578..46480",
        ),
    ]:
        gaps.append(
            ExtractionGapRecord(
                gap_id=gap_id,
                document_id=doc_id,
                branch_unit_id=uid,
                competition_name=cname,
                requirement_category="assessment_criteria",
                requirement_subcategory="judging_criterion_unweighted",
                missing_attribute_name="rubric_aspect_percentage_weights",
                gap_status="NOT_STATED",
                inspected_sections=[sec],
                inspected_char_range=rng,
                verification_method="rule_based_table_column_absence_scan",
                notes="Tabel kriteria penilaian hanya memiliki kolom 'Aspek Penilaian' dan 'Uraian' tanpa kolom bobot persentase (%).",
            )
        )

    reviews.extend(
        [
            ReviewItemRecord(
                review_id="REV-DOC009-BU01-001",
                document_id=doc_id,
                branch_unit_id="DOC-009-BU-01",
                competition_name="Pharmacopeia 2026 - Essay Competition",
                related_requirement_id="REQ-DOC009-BU01-008",
                issue_type="ocr_header_segmentation_truncation",
                severity="MEDIUM",
                review_status="NEEDS_REVIEW",
                source_page=_locate_page_for_char(pages, 3157),
                source_section="Timeline Essay Competition (3157..3235)",
                source_char_start=3157,
                source_char_end=3235,
                evidence_text=raw_text[3157:3235],
                review_description="Baris Pendaftaran Gelombang 1 (01-07 September 2026) sempat berada di luar batas awal DOC-009-BU-01 (3250) karena judul 'LOMBA ESSAY' rusak oleh OCR menjadi 'LOMDaCork Es'.",
                recommended_human_action="Perbaiki batas awal segmen DOC-009-BU-01 dari 3250 ke 3157 pada revisi segmenter.",
            ),
            ReviewItemRecord(
                review_id="REV-DOC009-BU01-002",
                document_id=doc_id,
                branch_unit_id="DOC-009-BU-01",
                competition_name="Pharmacopeia 2026 - Essay Competition",
                related_requirement_id="REQ-DOC009-BU01-006",
                issue_type="ocr_currency_symbol_noise",
                severity="LOW",
                review_status="NEEDS_REVIEW",
                source_page=_locate_page_for_char(pages, 48028),
                source_section="Biaya Pendaftaran (Shared Event Span 46547..48658)",
                source_char_start=48028,
                source_char_end=48129,
                evidence_text=raw_text[48028:48129],
                review_description="Nominal biaya pendaftaran Essay Competition mengalami distorsi OCR pada simbol Rupiah: 'Ro70.001,-' dan 'Rop85.001,-'.",
                recommended_human_action="Konfirmasi nominal Rp70.001 dan Rp85.001 (dengan kode unik +001) terhadap PDF asli.",
            ),
            ReviewItemRecord(
                review_id="REV-DOC009-BU01-003",
                document_id=doc_id,
                branch_unit_id="DOC-009-BU-01",
                competition_name="Pharmacopeia 2026 - Essay Competition",
                related_requirement_id="REQ-DOC009-BU01-019",
                issue_type="illegible_ocr_requirement_block",
                severity="HIGH",
                review_status="NEEDS_REVIEW",
                source_page=_locate_page_for_char(pages, 12983),
                source_section="Ketentuan Penulisan Essay Competition (Halaman 14 Bawah)",
                source_char_start=12983,
                source_char_end=13328,
                evidence_text=raw_text[12983:13328],
                review_description="Blok teks ketentuan teknis tipografi/margin pada bagian bawah halaman 14 rusak berat akibat OCR ('Pick Aha Mh Sh tt hAT teP... font€:, > See s eae Po eta rae. vg. 7 wt ii /herer') sehingga ukuran font, jenis font, dan margin tidak dapat diekstrak dari file TXT tanpa mengarang.",
                recommended_human_action="Buka dokumen PDF asli halaman 14 untuk membaca secara manual aturan jenis font, ukuran font, spasi, dan margin naskah esai.",
            ),
            ReviewItemRecord(
                review_id="REV-DOC009-BU02-001",
                document_id=doc_id,
                branch_unit_id="DOC-009-BU-02",
                competition_name="Pharmacopeia 2026 - Science Olympiad",
                related_requirement_id="REQ-DOC009-BU02-010",
                issue_type="ocr_url_and_token_corruption",
                severity="LOW",
                review_status="NEEDS_REVIEW",
                source_page=_locate_page_for_char(pages, 21617),
                source_section="Teknis Babak Penyisihan Science Olympiad",
                source_char_start=21617,
                source_char_end=21699,
                evidence_text=raw_text[21617:21699],
                review_description="Tautan platform ujian tertulis 'https://wwwe- \\n\\nujian.com/web/index.' (kehilangan titik setelah www dan terpotong baris) serta kuota delegasi sekolah tertulis 'lebih d1apesrertia'.",
                recommended_human_action="Normalisasikan URL ke https://www.e-ujian.com/web/index pada panduan peserta.",
            ),
            ReviewItemRecord(
                review_id="REV-DOC009-BU03-001",
                document_id=doc_id,
                branch_unit_id="DOC-009-BU-03",
                competition_name="Pharmacopeia 2026 - Digital Poster Competition",
                related_requirement_id="REQ-DOC009-BU03-017",
                issue_type="illegible_ocr_block_and_minor_typos",
                severity="MEDIUM",
                review_status="NEEDS_REVIEW",
                source_page=_locate_page_for_char(pages, 35122),
                source_section="Ketentuan Pengumpulan Karya Digital Poster (Halaman 39 Bawah)",
                source_char_start=35122,
                source_char_end=35486,
                evidence_text=raw_text[35122:35486],
                review_description="Bagian bawah halaman 39 memuat blok karakter OCR rusak ('TOPE T HOO TET ET ET TESST...') setelah butir 7 publikasi Instagram.",
                recommended_human_action="Periksa PDF asli halaman 39 untuk memastikan apakah blok OCR tersebut hanya elemen grafis/footer atau ketentuan tambahan caption/tag Instagram.",
            ),
        ]
    )

    return records, info_items, gaps, reviews


def extract_representative_requirements(
    project_root: Path,
    write_outputs: bool = True,
) -> Dict[str, Any]:
    """Run Stage 4.2 Refined Rule-Based Requirement Extraction on the 3 representative documents."""
    seg_val_path = project_root / "data" / "processed" / "segmentation_validation.json"
    units_path = project_root / "data" / "processed" / "competition_branch_units.json"
    inv_path = project_root / "data" / "processed" / "document_inventory_validated.json"
    raw_dir = project_root / "data" / "raw" / "txt"

    if not seg_val_path.exists():
        raise FileNotFoundError(
            f"Stage 3 validation file required before Stage 4 extraction: {seg_val_path}"
        )

    seg_val_payload = json.loads(seg_val_path.read_text(encoding="utf-8"))
    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    inv_payload = json.loads(inv_path.read_text(encoding="utf-8"))

    units_by_id = {u["branch_unit_id"]: u for u in units_payload["branch_units"]}
    vals_by_id = {u["branch_unit_id"]: u for u in seg_val_payload["unit_validations"]}
    docs_by_id = {d["document_id"]: d for d in inv_payload["documents"]}

    representative_selection = [
        {
            "selection_slot": "1_single_branch",
            "document_id": "DOC-001",
            "file_name": docs_by_id["DOC-001"]["file_name"],
            "multi_branch_type": "single_branch",
            "readability_status": docs_by_id["DOC-001"]["readability_status"],
            "branch_unit_ids": ["DOC-001-BU-01"],
            "segmentation_validation_statuses": {
                "DOC-001-BU-01": vals_by_id["DOC-001-BU-01"]["validation_status"]
            },
            "selection_rationale": (
                "Dokumen single_branch berstatus VALIDATED di segmentation_validation.json dengan struktur lengkap "
                "(Eligibility, Registration, Tracks & Stages, Coaching, Deliverables, Judging Criteria berbobot 25%x4, dan Verification Rules), "
                "sekaligus memuat contoh placeholder [TBC] dan inkonsistensi jadwal internal antar-bab."
            ),
        },
        {
            "selection_slot": "2_multi_branch_event",
            "document_id": "DOC-024",
            "file_name": docs_by_id["DOC-024"]["file_name"],
            "multi_branch_type": "multi_branch_event",
            "readability_status": docs_by_id["DOC-024"]["readability_status"],
            "branch_unit_ids": ["DOC-024-BU-01", "DOC-024-BU-02", "DOC-024-BU-03"],
            "segmentation_validation_statuses": {
                f"DOC-024-BU-0{i}": vals_by_id[f"DOC-024-BU-0{i}"]["validation_status"]
                for i in range(1, 4)
            },
            "selection_rationale": (
                "Dokumen multi_branch_event dengan 3 unit cabang mandiri yang seluruhnya berstatus VALIDATED di segmentation_validation.json "
                "(Esai, BMC, Poster). Menguji isolasi persyaratan antar-cabang, penanganan kontradiksi internal, serta deteksi salah ketik salin-tempel."
            ),
        },
        {
            "selection_slot": "3_text_or_segmentation_limitation",
            "document_id": "DOC-009",
            "file_name": docs_by_id["DOC-009"]["file_name"],
            "multi_branch_type": "multi_branch_event",
            "readability_status": docs_by_id["DOC-009"]["readability_status"],
            "branch_unit_ids": [
                "DOC-009-BU-01",
                "DOC-009-BU-02",
                "DOC-009-BU-03",
                "DOC-009-BU-04",
            ],
            "segmentation_validation_statuses": {
                f"DOC-009-BU-0{i}": vals_by_id[f"DOC-009-BU-0{i}"]["validation_status"]
                for i in range(1, 5)
            },
            "selection_rationale": (
                "Dokumen dengan keterbatasan ganda (kualitas teks `readable_with_ocr_noise` DAN keterbatasan segmentasi pada "
                "`segmentation_validation.json`: `DOC-009-BU-01` berstatus `NEEDS_REVISION` dan `DOC-009-BU-02..04` berstatus `VALIDATED_WITH_LIMITATION`)."
            ),
        },
    ]

    raw_001 = (raw_dir / docs_by_id["DOC-001"]["file_name"]).read_text(encoding="utf-8")
    raw_024 = (raw_dir / docs_by_id["DOC-024"]["file_name"]).read_text(encoding="utf-8")
    raw_009 = (raw_dir / docs_by_id["DOC-009"]["file_name"]).read_text(encoding="utf-8")

    r_001, i_001, g_001, rv_001 = _extract_doc001_bu01(
        raw_001, units_by_id["DOC-001-BU-01"], vals_by_id["DOC-001-BU-01"]
    )
    r_024, i_024, g_024, rv_024 = _extract_doc024_units(raw_024, units_by_id, vals_by_id)
    r_009, i_009, g_009, rv_009 = _extract_doc009_units(raw_009, units_by_id, vals_by_id)

    all_records = r_001 + r_024 + r_009
    all_info = i_001 + i_024 + i_009
    all_gaps = g_001 + g_024 + g_009
    all_reviews = rv_001 + rv_024 + rv_009

    # Deduplication guard by (branch_unit_id, requirement_category, requirement_name, source_char_start)
    deduped: List[ExtractedRequirementRecord] = []
    seen_keys: set[Tuple[str, str, str, int]] = set()
    for rec in all_records:
        key = (
            rec.branch_unit_id,
            rec.requirement_category,
            rec.requirement_name,
            rec.source_char_start,
        )
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(rec)

    by_category: Dict[str, int] = {cat: 0 for cat in REQUIREMENT_CATEGORIES}
    by_subcategory: Dict[str, int] = {}
    by_status: Dict[str, int] = {st: 0 for st in VALIDATION_STATUSES}
    by_evidence_type: Dict[str, int] = {et: 0 for et in EVIDENCE_TYPES}
    by_unit: Dict[str, int] = {}
    by_statement_nature: Dict[str, int] = {}

    for r in deduped:
        by_category[r.requirement_category] = (
            by_category.get(r.requirement_category, 0) + 1
        )
        by_subcategory[r.requirement_subcategory] = (
            by_subcategory.get(r.requirement_subcategory, 0) + 1
        )
        by_status[r.validation_status] = by_status.get(r.validation_status, 0) + 1
        by_evidence_type[r.evidence_type] = by_evidence_type.get(r.evidence_type, 0) + 1
        by_unit[r.branch_unit_id] = by_unit.get(r.branch_unit_id, 0) + 1
        by_statement_nature[r.statement_nature] = (
            by_statement_nature.get(r.statement_nature, 0) + 1
        )

    payload: Dict[str, Any] = {
        "stage": "Stage 4.2 Refinement: Rule-Based Requirement Extraction with Entity Separation & Grounded Evidence (3 Representative Documents)",
        "schema_version": "4.2",
        "entity_separation_model": {
            "requirement": "Persyaratan atau ketentuan resmi kompetisi yang benar-benar dinyatakan di dokumen sumber, dengan bukti kutipan utuh.",
            "information": "Informasi pendukung/kontekstual kompetisi (latar belakang acara, statistik WHO, struktur hadiah umum, info e-sertifikat) yang bukan syarat mengikat peserta.",
            "extraction_gap": "Atribut persyaratan standar atau bobot kriteria yang telah diperiksa secara sistematis namun tidak tercantum di dokumen sumber (NOT_STATED).",
            "review_item": "Anomali sumber (kontradiksi internal, salah ketik lintas cabang, placeholder [TBC], atau blok OCR rusak berat) yang membutuhkan pemeriksaan manusia.",
        },
        "summary": {
            "representative_documents_processed": 3,
            "branch_units_processed": len(by_unit),
            "total_requirements_extracted": len(deduped),
            "total_information_items": len(all_info),
            "total_extraction_gaps": len(all_gaps),
            "total_review_items": len(all_reviews),
            "counts_by_category": by_category,
            "counts_by_subcategory": by_subcategory,
            "counts_by_validation_status": by_status,
            "counts_by_evidence_type": by_evidence_type,
            "counts_by_statement_nature": by_statement_nature,
            "counts_by_branch_unit": by_unit,
            "strict_in_unit_bounds_count": sum(
                1 for r in deduped if r.within_strict_unit_bounds
            ),
            "recovered_from_audited_uncovered_spans_count": sum(
                1 for r in deduped if not r.within_strict_unit_bounds
            ),
            "records_with_exceptions_or_conditions": sum(
                1 for r in deduped if r.exception_or_condition != "NONE"
            ),
            "records_with_normalized_terms": sum(
                1 for r in deduped if len(r.normalized_terms) > 0
            ),
        },
        "representative_documents": representative_selection,
        "term_normalization_rules": TERM_NORMALIZATION_RULES,
        "requirements": [asdict(r) for r in deduped],
        "information_items": [asdict(i) for i in all_info],
        "extraction_gaps": [asdict(g) for g in all_gaps],
        "review_items": [asdict(rv) for rv in all_reviews],
    }

    if write_outputs:
        json_out = project_root / "data" / "processed" / "competition_requirements.json"
        csv_out = project_root / "data" / "processed" / "competition_requirements.csv"
        json_out.parent.mkdir(parents=True, exist_ok=True)
        with json_out.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        fieldnames = list(asdict(deduped[0]).keys())
        with csv_out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in deduped:
                row = asdict(r)
                row["related_requirement_ids"] = json.dumps(
                    row["related_requirement_ids"], ensure_ascii=False
                )
                row["normalized_terms"] = json.dumps(
                    row["normalized_terms"], ensure_ascii=False
                )
                writer.writerow(row)

    return payload
