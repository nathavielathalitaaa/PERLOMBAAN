"""Integration and unit tests for application services."""

from pathlib import Path
import pytest
from sqlalchemy.orm import Session

from src.competency_mapping.service import CompetencyService
from src.data_collection.schemas import (
    Classification,
    CompetitionCreate,
    CompetitionUpdate,
    EvidenceCreate,
    EvidenceType,
    IndicatorCreate,
    IndicatorType,
    MappingBasis,
    RelationType,
    RequirementCompetencyCreate,
    RequirementCreate,
    RequirementIndicatorCreate,
    RequirementType,
    SourceDocumentCreate,
    SourceStatus,
)
from src.indicator_mapping.service import IndicatorService
from src.requirement_extraction.service import RequirementService


def test_competition_service_lifecycle(db_session: Session):
    """Test full CRUD lifecycle of Competition via RequirementService."""
    create_dto = CompetitionCreate(
        name="Lomba Inovasi Nasional",
        category="Inovasi",
        organizer="Kemendikbud",
        year=2024,
        description="Lomba karya cipta inovatif",
    )
    comp = RequirementService.create_competition(create_dto, db_session)
    assert comp.id is not None
    assert comp.name == "Lomba Inovasi Nasional"

    # Update
    update_dto = CompetitionUpdate(description="Deskripsi terbarui")
    updated = RequirementService.update_competition(comp.id, update_dto, db_session)
    assert updated.description == "Deskripsi terbarui"

    # List
    comps = RequirementService.list_competitions(db_session, category="Inovasi")
    assert len(comps) == 1

    # Delete
    deleted = RequirementService.delete_competition(comp.id, db_session)
    assert deleted is True
    assert RequirementService.get_competition(comp.id, db_session) is None


def test_source_document_and_evidence_service(db_session: Session, sample_pdf: Path):
    """Test source document registration with SHA-256 calculation and evidence attachment."""
    comp = RequirementService.create_competition(
        CompetitionCreate(
            name="GEMASTIK 2024", category="Software", organizer="Puspresnas", year=2024
        ),
        db_session,
    )

    doc_dto = SourceDocumentCreate(
        competition_id=comp.id,
        title="Buku Panduan Gemastik 2024",
        file_path=str(sample_pdf),
    )
    doc = RequirementService.register_source_document(doc_dto, db_session)
    assert doc.file_hash is not None
    assert len(doc.file_hash) == 64

    # Create explicit requirement
    req_dto = RequirementCreate(
        competition_id=comp.id,
        description="Setiap tim terdiri dari 3 orang mahasiswa",
        requirement_type=RequirementType.ADMINISTRATIVE,
        classification=Classification.MANDATORY_ELIGIBILITY,
        source_status=SourceStatus.EXPLICIT,
    )
    req = RequirementService.create_requirement(req_dto, db_session)

    # Attach evidence
    ev_dto = EvidenceCreate(
        source_document_id=doc.id,
        requirement_id=req.id,
        page_number=1,
        section="Ketentuan Peserta",
        excerpt="Setiap tim terdiri dari 3 orang mahasiswa dengan 1 dosen pembimbing.",
        evidence_type=EvidenceType.DIRECT_QUOTE,
    )
    ev = RequirementService.add_evidence(ev_dto, db_session)
    assert ev.id is not None

    evidence_list = RequirementService.list_evidence_for_requirement(req.id, db_session)
    assert len(evidence_list) == 1
    assert evidence_list[0].page_number == 1


def test_indicator_service_and_linking(db_session: Session):
    """Test indicator taxonomy creation and requirement-indicator link with weights."""
    comp = RequirementService.create_competition(
        CompetitionCreate(
            name="Comp B", category="AI", organizer="AI Org", year=2024
        ),
        db_session,
    )
    req = RequirementService.create_requirement(
        RequirementCreate(
            competition_id=comp.id,
            description="Karya harus orisinal dan memiliki dampak luas",
            requirement_type=RequirementType.TECHNICAL,
            classification=Classification.EVALUATION_CRITERIA,
            source_status=SourceStatus.EXPLICIT,
        ),
        db_session,
    )

    ind = IndicatorService.create_indicator(
        IndicatorCreate(
            code="IND_IMPACT",
            name="Impact of Solution",
            definition="Tingkat kemanfaatan dan dampak nyata solusi pada masyarakat.",
            category="Impact",
            indicator_type=IndicatorType.RUBRIC_SCALE,
        ),
        db_session,
    )

    link_dto = RequirementIndicatorCreate(
        requirement_id=req.id,
        indicator_id=ind.id,
        weight=25.0,
        relation_type=RelationType.PRIMARY_CRITERION,
        mapping_status=SourceStatus.EXPLICIT,
    )
    link = IndicatorService.link_requirement_indicator(link_dto, db_session)
    assert link.weight == 25.0

    links = IndicatorService.list_indicators_for_requirement(req.id, db_session)
    assert len(links) == 1
    assert links[0].indicator.code == "IND_IMPACT"


def test_competency_taxonomy_and_mapping(db_session: Session):
    """Test seeding competencies and mapping requirement to competency."""
    seeded_count = CompetencyService.seed_default_taxonomy(db_session)
    assert seeded_count > 0

    sw_comp = CompetencyService.get_competency_by_code("COMP_SOFTWARE_ENG", db_session)
    assert sw_comp is not None

    comp = RequirementService.create_competition(
        CompetitionCreate(name="Hack A", category="Dev", organizer="Dev Inc", year=2024),
        db_session,
    )
    req = RequirementService.create_requirement(
        RequirementCreate(
            competition_id=comp.id,
            description="Sistem wajib dibangun menggunakan microservices",
            requirement_type=RequirementType.TECHNICAL,
            classification=Classification.EVALUATION_CRITERIA,
            source_status=SourceStatus.INFERRED,
        ),
        db_session,
    )

    mapping_dto = RequirementCompetencyCreate(
        requirement_id=req.id,
        competency_id=sw_comp.id,
        mapping_basis=MappingBasis.EXPERT_JUDGMENT,
        mapping_status=SourceStatus.INFERRED,
    )
    mapping = CompetencyService.map_requirement_competency(mapping_dto, db_session)
    assert mapping.mapping_basis == "expert_judgment"
    assert mapping.mapping_status == "inferred"

    mappings = CompetencyService.list_competencies_for_requirement(req.id, db_session)
    assert len(mappings) == 1
    assert mappings[0].competency.code == "COMP_SOFTWARE_ENG"

