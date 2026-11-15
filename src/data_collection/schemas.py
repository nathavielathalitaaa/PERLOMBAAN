"""Data validation schemas and taxonomy enums for AI Competition Mentor."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceStatus(str, Enum):
    """Data provenance classification indicating origin of information."""
    EXPLICIT = "explicit"        # Langsung tertulis dalam dokumen resmi
    INFERRED = "inferred"        # Hasil interpretasi atau pemetaan logis
    UNVERIFIED = "unverified"    # Belum memiliki bukti memadai atau staging


class DocumentType(str, Enum):
    """Classification of competition source documents."""
    GUIDEBOOK = "guidebook"
    SCORING_RUBRIC = "scoring_rubric"
    FAQ = "faq"
    OFFICIAL_ANNOUNCEMENT = "official_announcement"
    OTHER = "other"


class RequirementType(str, Enum):
    """Categorization of competition requirements."""
    ADMINISTRATIVE = "administrative"
    TECHNICAL = "technical"
    OUTPUT = "output"
    PRESENTATION = "presentation"
    TIMELINE = "timeline"
    OTHER = "other"


class Classification(str, Enum):
    """Legal/normative classification of competition requirement."""
    MANDATORY_ELIGIBILITY = "mandatory_eligibility"
    EVALUATION_CRITERIA = "evaluation_criteria"
    DISQUALIFICATION_RULE = "disqualification_rule"
    GENERAL_GUIDELINE = "general_guideline"


class IndicatorType(str, Enum):
    """Metric type used by an evaluation indicator."""
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    BINARY = "binary"
    RUBRIC_SCALE = "rubric_scale"


class EvidenceType(str, Enum):
    """Form of evidentiary excerpt captured from source document."""
    DIRECT_QUOTE = "direct_quote"
    TABLE = "table"
    FIGURE = "figure"
    SUMMARY = "summary"


class ConfidenceLevel(str, Enum):
    """Epistemic confidence level of recorded evidence."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MappingBasis(str, Enum):
    """Justification basis for competency or indicator mapping."""
    DIRECT_TEXT = "direct_text"
    INFERRED_FROM_INDICATOR = "inferred_from_indicator"
    EXPERT_JUDGMENT = "expert_judgment"


class RelationType(str, Enum):
    """Relationship character between a requirement and an indicator."""
    PRIMARY_CRITERION = "primary_criterion"
    SUB_CRITERION = "sub_criterion"
    SUPPORTING = "supporting"


# -----------------------------------------------------------------------------
# Pydantic Schemas for Validation and DTOs
# -----------------------------------------------------------------------------

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Competition Schemas
class CompetitionBase(BaseSchema):
    name: str = Field(..., min_length=2, max_length=255, description="Official competition name")
    category: str = Field(..., min_length=2, max_length=100, description="E.g., Business Plan, Hackathon, Data Science")
    organizer: str = Field(..., min_length=2, max_length=255, description="Organizing institution/entity")
    year: int = Field(..., ge=2000, le=2100, description="Competition edition year")
    description: Optional[str] = Field(None, description="Detailed overview of competition scope")
    official_url: Optional[str] = Field(None, max_length=500, description="Official portal/landing page URL")


class CompetitionCreate(CompetitionBase):
    pass


class CompetitionUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    organizer: Optional[str] = Field(None, min_length=2, max_length=255)
    year: Optional[int] = Field(None, ge=2000, le=2100)
    description: Optional[str] = None
    official_url: Optional[str] = None


class CompetitionRead(CompetitionBase):
    id: str
    created_at: datetime
    updated_at: datetime


# SourceDocument Schemas
class SourceDocumentBase(BaseSchema):
    competition_id: str
    title: str = Field(..., min_length=2, max_length=255)
    document_type: DocumentType = DocumentType.GUIDEBOOK
    file_path: str = Field(..., min_length=1, max_length=500)
    file_hash: Optional[str] = Field(None, max_length=64, description="SHA-256 checksum")
    version: Optional[str] = Field(None, max_length=50)
    publication_date: Optional[date] = None


class SourceDocumentCreate(SourceDocumentBase):
    pass


class SourceDocumentRead(SourceDocumentBase):
    id: str
    collected_at: datetime


# Requirement Schemas
class RequirementBase(BaseSchema):
    competition_id: str
    description: str = Field(..., min_length=3, description="Exact requirement clause or specification")
    requirement_type: RequirementType = RequirementType.TECHNICAL
    classification: Classification = Classification.EVALUATION_CRITERIA
    source_status: SourceStatus = SourceStatus.UNVERIFIED


class RequirementCreate(RequirementBase):
    pass


class RequirementUpdate(BaseSchema):
    description: Optional[str] = Field(None, min_length=3)
    requirement_type: Optional[RequirementType] = None
    classification: Optional[Classification] = None
    source_status: Optional[SourceStatus] = None


class RequirementRead(RequirementBase):
    id: str
    created_at: datetime
    updated_at: datetime


# Indicator Schemas
class IndicatorBase(BaseSchema):
    code: str = Field(..., min_length=2, max_length=50, description="Unique code e.g. IND_FEASIBILITY")
    name: str = Field(..., min_length=2, max_length=255)
    definition: str = Field(..., min_length=5)
    category: str = Field(..., min_length=2, max_length=100)
    indicator_type: IndicatorType = IndicatorType.RUBRIC_SCALE


class IndicatorCreate(IndicatorBase):
    pass


class IndicatorUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    definition: Optional[str] = Field(None, min_length=5)
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    indicator_type: Optional[IndicatorType] = None


class IndicatorRead(IndicatorBase):
    id: str
    created_at: datetime
    updated_at: datetime


# RequirementIndicator Schemas
class RequirementIndicatorBase(BaseSchema):
    requirement_id: str
    indicator_id: str
    weight: Optional[float] = Field(None, ge=0.0, le=100.0, description="Percentage or normalized weight if explicit")
    relation_type: RelationType = RelationType.PRIMARY_CRITERION
    mapping_status: SourceStatus = SourceStatus.EXPLICIT


class RequirementIndicatorCreate(RequirementIndicatorBase):
    pass


class RequirementIndicatorRead(RequirementIndicatorBase):
    id: str
    created_at: datetime


# Evidence Schemas
class EvidenceBase(BaseSchema):
    source_document_id: str
    requirement_id: Optional[str] = None
    indicator_id: Optional[str] = None
    page_number: Optional[int] = Field(None, ge=1)
    section: Optional[str] = Field(None, max_length=255)
    excerpt: str = Field(..., min_length=2, description="Verbatim text from source document")
    evidence_type: EvidenceType = EvidenceType.DIRECT_QUOTE
    confidence_level: ConfidenceLevel = ConfidenceLevel.HIGH

    @field_validator("requirement_id")
    @classmethod
    def validate_target(cls, v, info):
        # We also check in model validator that either requirement_id or indicator_id is present
        return v


class EvidenceCreate(EvidenceBase):
    def model_post_init(self, __context):
        if not self.requirement_id and not self.indicator_id:
            raise ValueError("Evidence must be associated with at least a requirement_id or an indicator_id.")


class EvidenceRead(EvidenceBase):
    id: str
    created_at: datetime


# Competency Schemas
class CompetencyBase(BaseSchema):
    code: str = Field(..., min_length=2, max_length=50, description="Taxonomy code e.g. COMP_DATA_ANALYSIS")
    name: str = Field(..., min_length=2, max_length=255)
    definition: str = Field(..., min_length=5)
    category: str = Field(..., min_length=2, max_length=100, description="E.g., Technical, Domain, Collaboration")


class CompetencyCreate(CompetencyBase):
    pass


class CompetencyUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    definition: Optional[str] = Field(None, min_length=5)
    category: Optional[str] = Field(None, min_length=2, max_length=100)


class CompetencyRead(CompetencyBase):
    id: str
    created_at: datetime
    updated_at: datetime


# RequirementCompetency Schemas
class RequirementCompetencyBase(BaseSchema):
    requirement_id: str
    competency_id: str
    mapping_basis: MappingBasis = MappingBasis.EXPERT_JUDGMENT
    mapping_status: SourceStatus = SourceStatus.INFERRED
    evidence_id: Optional[str] = None


class RequirementCompetencyCreate(RequirementCompetencyBase):
    pass


class RequirementCompetencyRead(RequirementCompetencyBase):
    id: str
    created_at: datetime

