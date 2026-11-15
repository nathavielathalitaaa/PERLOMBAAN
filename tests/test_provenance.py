"""Unit and integration tests for data provenance, evidence integrity, and auditing."""

from pathlib import Path
import pytest
from sqlalchemy.orm import Session

from src.data_collection.schemas import (
    Classification,
    CompetitionCreate,
    EvidenceCreate,
    EvidenceType,
    IndicatorCreate,
    IndicatorType,
    RequirementCreate,
    RequirementType,
    SourceDocumentCreate,
    SourceStatus,
)
from src.evaluation.integrity import DataIntegrityAuditor
from src.indicator_mapping.service import IndicatorService
from src.requirement_extraction.service import RequirementService


def test_provenance_separation_explicit_inferred_unverified(db_session: Session):
    """Ensure explicit, inferred, and unverified data remain strictly separated."""
    comp = RequirementService.create_competition(
        CompetitionCreate(
            name="Comp Provenance Test", category="Test", organizer="Test Org", year=2024
        ),
        db_session,
    )

    req_explicit = RequirementService.create_requirement(
        RequirementCreate(
            competition_id=comp.id,
            description="Syarat resmi dari panduan",
            requirement_type=RequirementType.ADMINISTRATIVE,
            classification=Classification.MANDATORY_ELIGIBILITY,
            source_status=SourceStatus.EXPLICIT,
        ),
        db_session,
    )

    req_inferred = RequirementService.create_requirement(
        RequirementCreate(
            competition_id=comp.id,
            description="Interpretasi peneliti terkait kebutuhan backend",
            requirement_type=RequirementType.TECHNICAL,
            classification=Classification.EVALUATION_CRITERIA,
            source_status=SourceStatus.INFERRED,
        ),
        db_session,
    )

    req_unverified = RequirementService.create_requirement(
        RequirementCreate(
            competition_id=comp.id,
            description="Informasi dari blog pihak ketiga",
            requirement_type=RequirementType.OTHER,
            classification=Classification.GENERAL_GUIDELINE,
            source_status=SourceStatus.UNVERIFIED,
        ),
        db_session,
    )

    explicit_list = RequirementService.list_requirements(
        comp.id, db_session, source_status=SourceStatus.EXPLICIT
    )
    inferred_list = RequirementService.list_requirements(
        comp.id, db_session, source_status=SourceStatus.INFERRED
    )
    unverified_list = RequirementService.list_requirements(
        comp.id, db_session, source_status=SourceStatus.UNVERIFIED
    )

    assert len(explicit_list) == 1
    assert explicit_list[0].id == req_explicit.id

    assert len(inferred_list) == 1
    assert inferred_list[0].id == req_inferred.id

    assert len(unverified_list) == 1
    assert unverified_list[0].id == req_unverified.id


def test_indicator_with_multiple_evidence_excerpts(db_session: Session, sample_pdf: Path):
    """An indicator can have multiple supporting pieces of evidence from one or more documents."""
    comp = RequirementService.create_competition(
        CompetitionCreate(name="Gemastik", category="IT", organizer="Puspresnas", year=2024),
        db_session,
    )
    doc = RequirementService.register_source_document(
        SourceDocumentCreate(
            competition_id=comp.id,
            title="Pedoman Gemastik",
            file_path=str(sample_pdf),
        ),
        db_session,
    )

    ind = IndicatorService.create_indicator(
        IndicatorCreate(
            code="IND_INNOVATION_TECH",
            name="Inovasi Teknologi",
            definition="Tingkat kebaruan dan orisinalitas solusi teknologi.",
            category="Inovasi",
            indicator_type=IndicatorType.RUBRIC_SCALE,
        ),
        db_session,
    )

    # Attach Evidence 1: rubric section
    ev1 = RequirementService.add_evidence(
        EvidenceCreate(
            source_document_id=doc.id,
            indicator_id=ind.id,
            page_number=2,
            section="Rubrik Penilaian",
            excerpt="Inovasi dan Keaslian Ide (Bobot: 30%)",
            evidence_type=EvidenceType.DIRECT_QUOTE,
        ),
        db_session,
    )

    # Attach Evidence 2: general guideline section
    ev2 = RequirementService.add_evidence(
        EvidenceCreate(
            source_document_id=doc.id,
            indicator_id=ind.id,
            page_number=1,
            section="Pendahuluan",
            excerpt="Karya cipta harus merupakan karya orisinal bukan plagiasi.",
            evidence_type=EvidenceType.DIRECT_QUOTE,
        ),
        db_session,
    )

    evidences = IndicatorService.list_evidence_for_indicator(ind.id, db_session)
    assert len(evidences) == 2
    assert {e.id for e in evidences} == {ev1.id, ev2.id}


def test_data_integrity_auditor_flags_ungrounded_explicit_data(
    db_session: Session, sample_pdf: Path
):
    """Auditor flags violations where explicit requirements lack evidence citations."""
    comp = RequirementService.create_competition(
        CompetitionCreate(name="Audit Comp", category="Test", organizer="Audit Org", year=2024),
        db_session,
    )
    doc = RequirementService.register_source_document(
        SourceDocumentCreate(
            competition_id=comp.id,
            title="Audit Doc",
            file_path=str(sample_pdf),
        ),
        db_session,
    )

    # Explicit requirement WITHOUT evidence
    req_unsupported = RequirementService.create_requirement(
        RequirementCreate(
            competition_id=comp.id,
            description="Requirement without citation",
            requirement_type=RequirementType.TECHNICAL,
            classification=Classification.EVALUATION_CRITERIA,
            source_status=SourceStatus.EXPLICIT,
        ),
        db_session,
    )

    audit_report = DataIntegrityAuditor.audit_competition(comp.id, db_session)
    assert audit_report["is_fully_grounded"] is False
    assert audit_report["unsupported_explicit_requirements"] == 1
    assert any("Violation of Research Integrity" in issue for issue in audit_report["critical_issues"])

    # Now add evidence to ground it
    RequirementService.add_evidence(
        EvidenceCreate(
            source_document_id=doc.id,
            requirement_id=req_unsupported.id,
            page_number=1,
            section="Sec 1",
            excerpt="Verified quote from doc",
            evidence_type=EvidenceType.DIRECT_QUOTE,
        ),
        db_session,
    )

    updated_report = DataIntegrityAuditor.audit_competition(comp.id, db_session)
    assert updated_report["is_fully_grounded"] is True
    assert updated_report["unsupported_explicit_requirements"] == 0

