"""Indicator mapping service for evaluation criteria and rubrics."""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data_collection.schemas import (
    IndicatorCreate,
    IndicatorUpdate,
    RequirementIndicatorCreate,
)
from src.database.models import (
    Evidence,
    Indicator,
    Requirement,
    RequirementIndicator,
)

logger = logging.getLogger(__name__)


class IndicatorService:
    """Service handling Indicator taxonomy and requirement-indicator linkage."""

    @staticmethod
    def create_indicator(data: IndicatorCreate, session: Session) -> Indicator:
        """Create a new evaluation indicator in taxonomy."""
        existing = session.scalar(select(Indicator).where(Indicator.code == data.code))
        if existing:
            raise ValueError(f"Indicator with code '{data.code}' already exists.")

        indicator = Indicator(
            code=data.code,
            name=data.name,
            definition=data.definition,
            category=data.category,
            indicator_type=data.indicator_type.value,
        )
        session.add(indicator)
        session.flush()
        logger.info("Created indicator: %s [%s]", indicator.name, indicator.code)
        return indicator

    @staticmethod
    def get_indicator(indicator_id: str, session: Session) -> Optional[Indicator]:
        """Retrieve indicator by ID."""
        return session.get(Indicator, indicator_id)

    @staticmethod
    def get_indicator_by_code(code: str, session: Session) -> Optional[Indicator]:
        """Retrieve indicator by unique taxonomy code."""
        return session.scalar(select(Indicator).where(Indicator.code == code))

    @staticmethod
    def list_indicators(
        session: Session, category: Optional[str] = None
    ) -> List[Indicator]:
        """List all indicators, optionally filtered by category."""
        stmt = select(Indicator)
        if category:
            stmt = stmt.where(Indicator.category == category)
        stmt = stmt.order_by(Indicator.category, Indicator.code)
        return list(session.scalars(stmt).all())

    @staticmethod
    def update_indicator(
        indicator_id: str, data: IndicatorUpdate, session: Session
    ) -> Indicator:
        """Update indicator definition or category."""
        indicator = session.get(Indicator, indicator_id)
        if not indicator:
            raise ValueError(f"Indicator not found with ID: {indicator_id}")

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(indicator, key, value)

        session.flush()
        return indicator

    @staticmethod
    def delete_indicator(indicator_id: str, session: Session) -> bool:
        """Delete an indicator."""
        indicator = session.get(Indicator, indicator_id)
        if not indicator:
            return False
        session.delete(indicator)
        session.flush()
        return True

    @staticmethod
    def link_requirement_indicator(
        data: RequirementIndicatorCreate, session: Session
    ) -> RequirementIndicator:
        """Link a competition requirement to an evaluation indicator."""
        req = session.get(Requirement, data.requirement_id)
        if not req:
            raise ValueError(f"Requirement not found: {data.requirement_id}")

        ind = session.get(Indicator, data.indicator_id)
        if not ind:
            raise ValueError(f"Indicator not found: {data.indicator_id}")

        # Check existing link
        existing = session.scalar(
            select(RequirementIndicator).where(
                RequirementIndicator.requirement_id == data.requirement_id,
                RequirementIndicator.indicator_id == data.indicator_id,
            )
        )
        if existing:
            raise ValueError(
                f"Requirement {data.requirement_id} is already linked to Indicator {data.indicator_id}."
            )

        link = RequirementIndicator(
            requirement_id=data.requirement_id,
            indicator_id=data.indicator_id,
            weight=data.weight,
            relation_type=data.relation_type.value,
            mapping_status=data.mapping_status.value,
        )
        session.add(link)
        session.flush()
        logger.info("Linked Requirement %s to Indicator %s", data.requirement_id, data.indicator_id)
        return link

    @staticmethod
    def unlink_requirement_indicator(
        requirement_id: str, indicator_id: str, session: Session
    ) -> bool:
        """Remove link between a requirement and an indicator."""
        link = session.scalar(
            select(RequirementIndicator).where(
                RequirementIndicator.requirement_id == requirement_id,
                RequirementIndicator.indicator_id == indicator_id,
            )
        )
        if not link:
            return False
        session.delete(link)
        session.flush()
        return True

    @staticmethod
    def list_indicators_for_requirement(
        requirement_id: str, session: Session
    ) -> List[RequirementIndicator]:
        """List indicator links for a requirement."""
        stmt = select(RequirementIndicator).where(
            RequirementIndicator.requirement_id == requirement_id
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def list_evidence_for_indicator(
        indicator_id: str, session: Session
    ) -> List[Evidence]:
        """List all evidence excerpts attached to an indicator."""
        stmt = select(Evidence).where(Evidence.indicator_id == indicator_id)
        return list(session.scalars(stmt).all())

