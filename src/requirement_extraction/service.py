"""Requirement and competition management service."""

import logging
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data_collection.schemas import (
    CompetitionCreate,
    CompetitionUpdate,
    EvidenceCreate,
    RequirementCreate,
    RequirementUpdate,
    SourceDocumentCreate,
    SourceStatus,
)
from src.database.models import (
    Competition,
    Evidence,
    Requirement,
    SourceDocument,
)
from src.document_processing.pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


class RequirementService:
    """Service handling Competition, SourceDocument, Requirement, and Evidence operations."""

    # -------------------------------------------------------------------------
    # Competition Operations
    # -------------------------------------------------------------------------
    @staticmethod
    def create_competition(data: CompetitionCreate, session: Session) -> Competition:
        """Create and persist a new competition record."""
        competition = Competition(
            name=data.name,
            category=data.category,
            organizer=data.organizer,
            year=data.year,
            description=data.description,
            official_url=data.official_url,
        )
        session.add(competition)
        session.flush()
        logger.info("Created competition: %s (ID: %s)", competition.name, competition.id)
        return competition

    @staticmethod
    def get_competition(competition_id: str, session: Session) -> Optional[Competition]:
        """Retrieve a competition by ID."""
        return session.get(Competition, competition_id)

    @staticmethod
    def list_competitions(
        session: Session,
        category: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[Competition]:
        """List competitions with optional category and year filters."""
        stmt = select(Competition)
        if category:
            stmt = stmt.where(Competition.category == category)
        if year:
            stmt = stmt.where(Competition.year == year)
        stmt = stmt.order_by(Competition.year.desc(), Competition.name)
        return list(session.scalars(stmt).all())

    @staticmethod
    def update_competition(
        competition_id: str, data: CompetitionUpdate, session: Session
    ) -> Competition:
        """Update an existing competition's attributes."""
        competition = session.get(Competition, competition_id)
        if not competition:
            raise ValueError(f"Competition not found with ID: {competition_id}")

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(competition, key, value)

        session.flush()
        logger.info("Updated competition ID %s", competition_id)
        return competition

    @staticmethod
    def delete_competition(competition_id: str, session: Session) -> bool:
        """Delete a competition and all cascaded child records."""
        competition = session.get(Competition, competition_id)
        if not competition:
            return False
        session.delete(competition)
        session.flush()
        logger.info("Deleted competition ID %s", competition_id)
        return True

    # -------------------------------------------------------------------------
    # Source Document Operations
    # -------------------------------------------------------------------------
    @staticmethod
    def register_source_document(
        data: SourceDocumentCreate, session: Session, auto_compute_hash: bool = True
    ) -> SourceDocument:
        """Register a source document linked to a competition."""
        competition = session.get(Competition, data.competition_id)
        if not competition:
            raise ValueError(f"Cannot register document. Competition not found: {data.competition_id}")

        file_hash = data.file_hash
        file_path_obj = Path(data.file_path)
        if auto_compute_hash and not file_hash and file_path_obj.exists() and file_path_obj.is_file():
            file_hash = PDFExtractor.calculate_sha256(file_path_obj)

        doc = SourceDocument(
            competition_id=data.competition_id,
            title=data.title,
            document_type=data.document_type.value,
            file_path=str(data.file_path),
            file_hash=file_hash,
            version=data.version,
            publication_date=data.publication_date,
        )
        session.add(doc)
        session.flush()
        logger.info("Registered source document: %s (ID: %s)", doc.title, doc.id)
        return doc

    @staticmethod
    def get_source_document(doc_id: str, session: Session) -> Optional[SourceDocument]:
        """Retrieve a source document by ID."""
        return session.get(SourceDocument, doc_id)

    @staticmethod
    def list_source_documents(competition_id: str, session: Session) -> List[SourceDocument]:
        """List all source documents for a specific competition."""
        stmt = select(SourceDocument).where(SourceDocument.competition_id == competition_id)
        return list(session.scalars(stmt).all())

    @staticmethod
    def delete_source_document(doc_id: str, session: Session) -> bool:
        """Delete a source document and dependent evidences."""
        doc = session.get(SourceDocument, doc_id)
        if not doc:
            return False
        session.delete(doc)
        session.flush()
        return True

    # -------------------------------------------------------------------------
    # Requirement Operations
    # -------------------------------------------------------------------------
    @staticmethod
    def create_requirement(data: RequirementCreate, session: Session) -> Requirement:
        """Create a requirement record with explicit provenance tracking."""
        competition = session.get(Competition, data.competition_id)
        if not competition:
            raise ValueError(f"Competition not found with ID: {data.competition_id}")

        req = Requirement(
            competition_id=data.competition_id,
            description=data.description,
            requirement_type=data.requirement_type.value,
            classification=data.classification.value,
            source_status=data.source_status.value,
        )
        session.add(req)
        session.flush()
        logger.info("Created requirement: %s (Status: %s)", req.id, req.source_status)
        return req

    @staticmethod
    def get_requirement(requirement_id: str, session: Session) -> Optional[Requirement]:
        """Retrieve requirement by ID."""
        return session.get(Requirement, requirement_id)

    @staticmethod
    def list_requirements(
        competition_id: str,
        session: Session,
        source_status: Optional[SourceStatus] = None,
    ) -> List[Requirement]:
        """List requirements for a competition with optional status filtering."""
        stmt = select(Requirement).where(Requirement.competition_id == competition_id)
        if source_status:
            stmt = stmt.where(Requirement.source_status == source_status.value)
        stmt = stmt.order_by(Requirement.created_at)
        return list(session.scalars(stmt).all())

    @staticmethod
    def update_requirement(
        requirement_id: str, data: RequirementUpdate, session: Session
    ) -> Requirement:
        """Update requirement attributes."""
        req = session.get(Requirement, requirement_id)
        if not req:
            raise ValueError(f"Requirement not found with ID: {requirement_id}")

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(req, key, value)

        session.flush()
        return req

    @staticmethod
    def delete_requirement(requirement_id: str, session: Session) -> bool:
        """Delete requirement and cascaded relationships."""
        req = session.get(Requirement, requirement_id)
        if not req:
            return False
        session.delete(req)
        session.flush()
        return True

    # -------------------------------------------------------------------------
    # Evidence Operations
    # -------------------------------------------------------------------------
    @staticmethod
    def add_evidence(data: EvidenceCreate, session: Session) -> Evidence:
        """Attach verified textual excerpt to a requirement and/or indicator."""
        doc = session.get(SourceDocument, data.source_document_id)
        if not doc:
            raise ValueError(f"Source document not found: {data.source_document_id}")

        if not data.requirement_id and not data.indicator_id:
            raise ValueError("Evidence must link to either a requirement or an indicator.")

        if data.requirement_id:
            req = session.get(Requirement, data.requirement_id)
            if not req:
                raise ValueError(f"Requirement not found: {data.requirement_id}")

        evidence = Evidence(
            source_document_id=data.source_document_id,
            requirement_id=data.requirement_id,
            indicator_id=data.indicator_id,
            page_number=data.page_number,
            section=data.section,
            excerpt=data.excerpt,
            evidence_type=data.evidence_type.value,
            confidence_level=data.confidence_level.value,
        )
        session.add(evidence)
        session.flush()

        if data.requirement_id:
            req = session.get(Requirement, data.requirement_id)
            if req:
                session.refresh(req, ["evidences"])

        logger.info(
            "Attached evidence %s to Doc %s (Page %s)",
            evidence.id,
            data.source_document_id,
            data.page_number,
        )
        return evidence

    @staticmethod
    def list_evidence_for_requirement(requirement_id: str, session: Session) -> List[Evidence]:
        """List all evidence excerpts attached to a requirement."""
        stmt = select(Evidence).where(Evidence.requirement_id == requirement_id)
        return list(session.scalars(stmt).all())
