"""SQLAlchemy relational models for AI Competition Mentor."""

from typing import List, Optional
from datetime import date, datetime
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, generate_uuid, utc_now


class Competition(Base):
    """Competition entity representing an official competitive event."""
    __tablename__ = "competitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    organizer: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    official_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relational associations
    documents: Mapped[List["SourceDocument"]] = relationship(
        "SourceDocument", back_populates="competition", cascade="all, delete-orphan"
    )
    requirements: Mapped[List["Requirement"]] = relationship(
        "Requirement", back_populates="competition", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Competition(id={self.id}, name='{self.name}', year={self.year})>"


class SourceDocument(Base):
    """Primary source material (PDFs, guidebooks, rubrics) for competition data."""
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    competition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    publication_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relational associations
    competition: Mapped["Competition"] = relationship("Competition", back_populates="documents")
    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="source_document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SourceDocument(id={self.id}, title='{self.title}', type='{self.document_type}')>"


class Requirement(Base):
    """Normative specification or evaluation requirement of a competition."""
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    competition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    source_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unverified", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relational associations
    competition: Mapped["Competition"] = relationship("Competition", back_populates="requirements")
    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="requirement", cascade="all, delete-orphan"
    )
    requirement_indicators: Mapped[List["RequirementIndicator"]] = relationship(
        "RequirementIndicator", back_populates="requirement", cascade="all, delete-orphan"
    )
    requirement_competencies: Mapped[List["RequirementCompetency"]] = relationship(
        "RequirementCompetency", back_populates="requirement", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Requirement(id={self.id}, type='{self.requirement_type}', status='{self.source_status}')>"


class Indicator(Base):
    """Evaluation rubric criteria or assessment indicator."""
    __tablename__ = "indicators"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    indicator_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relational associations
    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="indicator", cascade="all, delete-orphan"
    )
    requirement_indicators: Mapped[List["RequirementIndicator"]] = relationship(
        "RequirementIndicator", back_populates="indicator", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Indicator(id={self.id}, code='{self.code}', name='{self.name}')>"


class RequirementIndicator(Base):
    """Association linking competition requirements with specific evaluation indicators."""
    __tablename__ = "requirement_indicators"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    indicator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False, default="primary_criterion")
    mapping_status: Mapped[str] = mapped_column(String(20), nullable=False, default="explicit")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        UniqueConstraint("requirement_id", "indicator_id", name="uq_requirement_indicator"),
    )

    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="requirement_indicators")
    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="requirement_indicators")

    def __repr__(self) -> str:
        return f"<RequirementIndicator(req={self.requirement_id}, ind={self.indicator_id}, weight={self.weight})>"


class Evidence(Base):
    """Verifiable textual excerpt proving requirements, indicators, or provenance."""
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=True, index=True
    )
    indicator_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("indicators.id", ondelete="CASCADE"), nullable=True, index=True
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "requirement_id IS NOT NULL OR indicator_id IS NOT NULL",
            name="chk_evidence_target_not_null",
        ),
    )

    # Relational associations
    source_document: Mapped["SourceDocument"] = relationship("SourceDocument", back_populates="evidences")
    requirement: Mapped[Optional["Requirement"]] = relationship("Requirement", back_populates="evidences")
    indicator: Mapped[Optional["Indicator"]] = relationship("Indicator", back_populates="evidences")
    requirement_competencies: Mapped[List["RequirementCompetency"]] = relationship(
        "RequirementCompetency", back_populates="evidence"
    )

    def __repr__(self) -> str:
        return f"<Evidence(id={self.id}, doc={self.source_document_id}, page={self.page_number})>"


class Competency(Base):
    """Reusable skill, knowledge, or behavioral capability taxonomy."""
    __tablename__ = "competencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relational associations
    requirement_competencies: Mapped[List["RequirementCompetency"]] = relationship(
        "RequirementCompetency", back_populates="competency", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Competency(id={self.id}, code='{self.code}', name='{self.name}')>"


class RequirementCompetency(Base):
    """Mapping between a competition requirement and required competencies."""
    __tablename__ = "requirement_competencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    competency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("competencies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mapping_basis: Mapped[str] = mapped_column(String(50), nullable=False)
    mapping_status: Mapped[str] = mapped_column(String(20), nullable=False, default="inferred", index=True)
    evidence_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        UniqueConstraint("requirement_id", "competency_id", name="uq_requirement_competency"),
    )

    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="requirement_competencies")
    competency: Mapped["Competency"] = relationship("Competency", back_populates="requirement_competencies")
    evidence: Mapped[Optional["Evidence"]] = relationship("Evidence", back_populates="requirement_competencies")

    def __repr__(self) -> str:
        return f"<RequirementCompetency(req={self.requirement_id}, comp={self.competency_id}, status='{self.mapping_status}')>"

