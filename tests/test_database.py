"""Unit tests for database models, constraints, and relational integrity."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import (
    Competency,
    Competition,
    Evidence,
    Indicator,
    Requirement,
    RequirementCompetency,
    RequirementIndicator,
    SourceDocument,
)


def test_competition_creation_and_retrieval(db_session: Session):
    """Ensure competition record is persisted with UUID and default timestamps."""
    comp = Competition(
        name="GEMASTIK XVII",
        category="Software Engineering",
        organizer="Kemendikbudristek",
        year=2024,
        description="Pagelaran Mahasiswa Nasional Bidang TIK",
    )
    db_session.add(comp)
    db_session.commit()

    fetched = db_session.get(Competition, comp.id)
    assert fetched is not None
    assert fetched.name == "GEMASTIK XVII"
    assert fetched.year == 2024
    assert fetched.created_at is not None
    assert len(fetched.id) == 36  # UUID length


def test_sqlite_foreign_key_enforcement(db_session: Session):
    """Verify that SQLite rejects foreign keys pointing to non-existent parent records."""
    invalid_doc = SourceDocument(
        competition_id="non-existent-uuid-12345",
        title="Ghost Document",
        document_type="guidebook",
        file_path="/tmp/ghost.pdf",
    )
    db_session.add(invalid_doc)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascading_delete_behavior(db_session: Session):
    """Verify deleting a competition cascades to all child documents and requirements."""
    comp = Competition(
        name="Hackathon 2024",
        category="Hackathon",
        organizer="Tech Corp",
        year=2024,
    )
    db_session.add(comp)
    db_session.flush()

    doc = SourceDocument(
        competition_id=comp.id,
        title="Hackathon Rules",
        document_type="guidebook",
        file_path="/tmp/rules.pdf",
    )
    req = Requirement(
        competition_id=comp.id,
        description="Setiap tim wajib beranggotakan 3 orang",
        requirement_type="administrative",
        classification="mandatory_eligibility",
        source_status="explicit",
    )
    db_session.add_all([doc, req])
    db_session.flush()

    evidence = Evidence(
        source_document_id=doc.id,
        requirement_id=req.id,
        page_number=1,
        excerpt="Setiap tim terdiri dari 3 orang",
        evidence_type="direct_quote",
        confidence_level="high",
    )
    db_session.add(evidence)
    db_session.commit()

    doc_id = doc.id
    req_id = req.id
    evidence_id = evidence.id

    # Delete parent competition
    db_session.delete(comp)
    db_session.commit()

    # Child records must be deleted automatically
    assert db_session.get(SourceDocument, doc_id) is None
    assert db_session.get(Requirement, req_id) is None
    assert db_session.get(Evidence, evidence_id) is None


def test_evidence_check_constraint(db_session: Session):
    """Evidence must link to at least a requirement or an indicator."""
    comp = Competition(name="Comp A", category="Cat A", organizer="Org A", year=2024)
    db_session.add(comp)
    db_session.flush()

    doc = SourceDocument(
        competition_id=comp.id,
        title="Guidebook",
        document_type="guidebook",
        file_path="/tmp/guide.pdf",
    )
    db_session.add(doc)
    db_session.flush()

    # Evidence with neither requirement nor indicator must violate CheckConstraint
    orphan_evidence = Evidence(
        source_document_id=doc.id,
        requirement_id=None,
        indicator_id=None,
        excerpt="Some random text",
        evidence_type="direct_quote",
        confidence_level="high",
    )
    db_session.add(orphan_evidence)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_constraints(db_session: Session):
    """Ensure unique constraints for indicator codes and mapping links are enforced."""
    ind1 = Indicator(
        code="IND_INNOVATION",
        name="Innovation",
        definition="Originality of idea",
        category="Ideation",
        indicator_type="rubric_scale",
    )
    db_session.add(ind1)
    db_session.commit()

    # Duplicate code must fail
    ind2 = Indicator(
        code="IND_INNOVATION",
        name="Duplicate Innovation",
        definition="Different text",
        category="Ideation",
        indicator_type="rubric_scale",
    )
    db_session.add(ind2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

