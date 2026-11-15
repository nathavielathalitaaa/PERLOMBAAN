"""Requirement extraction service and Stage 4.2/4.3 rule-based extraction package."""

from src.requirement_extraction.evaluator import (
    GroundTruthRequirement,
    build_ground_truth_dataset,
    evaluate_requirement_extraction,
)
from src.requirement_extraction.extractor import (
    ExtractedRequirementRecord,
    ExtractionGapRecord,
    ReviewItemRecord,
    SupportingInformationRecord,
    extract_representative_requirements,
)
from src.requirement_extraction.readiness import (
    READINESS_DECISION_STATUSES,
    CorpusExpansionPlanRow,
    evaluate_corpus_expansion_readiness,
)
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
from src.requirement_extraction.service import RequirementService

__all__ = [
    "CONFIDENCE_LEVELS",
    "EVIDENCE_TYPES",
    "RECORD_TYPES",
    "REQUIREMENT_CATEGORIES",
    "REQUIREMENT_SUBCATEGORIES",
    "STATEMENT_NATURES",
    "TERM_NORMALIZATION_RULES",
    "VALIDATION_STATUSES",
    "READINESS_DECISION_STATUSES",
    "apply_term_normalization",
    "classify_requirement_clause",
    "extract_exception_or_condition",
    "is_non_requirement_background",
    "verify_description_grounded_in_evidence",
    "ExtractedRequirementRecord",
    "SupportingInformationRecord",
    "ExtractionGapRecord",
    "ReviewItemRecord",
    "extract_representative_requirements",
    "GroundTruthRequirement",
    "build_ground_truth_dataset",
    "evaluate_requirement_extraction",
    "CorpusExpansionPlanRow",
    "evaluate_corpus_expansion_readiness",
    "RequirementService",
]
