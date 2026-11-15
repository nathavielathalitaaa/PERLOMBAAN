"""Competency taxonomy and requirement-competency mapping service."""

import json
import logging
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import KNOWLEDGE_BASE_DIR
from src.data_collection.schemas import (
    CompetencyCreate,
    CompetencyUpdate,
    RequirementCompetencyCreate,
)
from src.database.models import (
    Competency,
    Evidence,
    Requirement,
    RequirementCompetency,
)

logger = logging.getLogger(__name__)


class CompetencyService:
    """Service handling Competency taxonomy and mapping to competition requirements."""

    @staticmethod
    def create_competency(data: CompetencyCreate, session: Session) -> Competency:
        """Create a new competency in the taxonomy."""
        existing = session.scalar(select(Competency).where(Competency.code == data.code))
        if existing:
            raise ValueError(f"Competency with code '{data.code}' already exists.")

        comp = Competency(
            code=data.code,
            name=data.name,
            definition=data.definition,
            category=data.category,
        )
        session.add(comp)
        session.flush()
        logger.info("Created competency: %s [%s]", comp.name, comp.code)
        return comp

    @staticmethod
    def get_competency(competency_id: str, session: Session) -> Optional[Competency]:
        """Retrieve competency by ID."""
        return session.get(Competency, competency_id)

    @staticmethod
    def get_competency_by_code(code: str, session: Session) -> Optional[Competency]:
        """Retrieve competency by unique code."""
        return session.scalar(select(Competency).where(Competency.code == code))

    @staticmethod
    def list_competencies(
        session: Session, category: Optional[str] = None
    ) -> List[Competency]:
        """List competencies, optionally filtered by category."""
        stmt = select(Competency)
        if category:
            stmt = stmt.where(Competency.category == category)
        stmt = stmt.order_by(Competency.category, Competency.code)
        return list(session.scalars(stmt).all())

    @staticmethod
    def update_competency(
        competency_id: str, data: CompetencyUpdate, session: Session
    ) -> Competency:
        """Update competency attributes."""
        comp = session.get(Competency, competency_id)
        if not comp:
            raise ValueError(f"Competency not found with ID: {competency_id}")

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(comp, key, value)

        session.flush()
        return comp

    @staticmethod
    def delete_competency(competency_id: str, session: Session) -> bool:
        """Delete competency and associated mappings."""
        comp = session.get(Competency, competency_id)
        if not comp:
            return False
        session.delete(comp)
        session.flush()
        return True

    @staticmethod
    def map_requirement_competency(
        data: RequirementCompetencyCreate, session: Session
    ) -> RequirementCompetency:
        """Map a requirement to a competency with explicit justification and provenance."""
        req = session.get(Requirement, data.requirement_id)
        if not req:
            raise ValueError(f"Requirement not found: {data.requirement_id}")

        comp = session.get(Competency, data.competency_id)
        if not comp:
            raise ValueError(f"Competency not found: {data.competency_id}")

        if data.evidence_id:
            evidence = session.get(Evidence, data.evidence_id)
            if not evidence:
                raise ValueError(f"Evidence not found with ID: {data.evidence_id}")

        # Check existing mapping
        existing = session.scalar(
            select(RequirementCompetency).where(
                RequirementCompetency.requirement_id == data.requirement_id,
                RequirementCompetency.competency_id == data.competency_id,
            )
        )
        if existing:
            raise ValueError(
                f"Requirement {data.requirement_id} is already mapped to Competency {data.competency_id}."
            )

        mapping = RequirementCompetency(
            requirement_id=data.requirement_id,
            competency_id=data.competency_id,
            mapping_basis=data.mapping_basis.value,
            mapping_status=data.mapping_status.value,
            evidence_id=data.evidence_id,
        )
        session.add(mapping)
        session.flush()
        logger.info(
            "Mapped Requirement %s to Competency %s (Status: %s)",
            data.requirement_id,
            data.competency_id,
            data.mapping_status.value,
        )
        return mapping

    @staticmethod
    def unmap_requirement_competency(
        requirement_id: str, competency_id: str, session: Session
    ) -> bool:
        """Remove mapping between requirement and competency."""
        mapping = session.scalar(
            select(RequirementCompetency).where(
                RequirementCompetency.requirement_id == requirement_id,
                RequirementCompetency.competency_id == competency_id,
            )
        )
        if not mapping:
            return False
        session.delete(mapping)
        session.flush()
        return True

    @staticmethod
    def list_competencies_for_requirement(
        requirement_id: str, session: Session
    ) -> List[RequirementCompetency]:
        """List all competencies mapped to a requirement."""
        stmt = select(RequirementCompetency).where(
            RequirementCompetency.requirement_id == requirement_id
        )
        return list(session.scalars(stmt).all())

    @classmethod
    def seed_default_taxonomy(
        cls, session: Session, json_path: Optional[str | Path] = None
    ) -> int:
        """Seed default competency taxonomy from JSON file if not already present."""
        path = (
            Path(json_path)
            if json_path
            else KNOWLEDGE_BASE_DIR / "competency_taxonomy" / "default_competencies.json"
        )
        if not path.is_file():
            logger.warning("Default competency taxonomy file not found: %s", path)
            return 0

        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        created_count = 0
        for item in raw_data:
            existing = cls.get_competency_by_code(item["code"], session)
            if not existing:
                comp = Competency(
                    code=item["code"],
                    name=item["name"],
                    definition=item["definition"],
                    category=item["category"],
                )
                session.add(comp)
                created_count += 1

        session.flush()
        logger.info("Seeded %d new competencies into taxonomy.", created_count)
        return created_count

