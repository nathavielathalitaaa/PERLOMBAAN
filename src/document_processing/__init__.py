"""Document processing package."""

from src.document_processing.document_segmenter import (
    MULTI_BRANCH_STRUCTURAL_SPECS,
    CompetitionBranchUnit,
    segment_documents,
)
from src.document_processing.inventory_validator import (
    BRANCH_TO_DOMAIN,
    DOCUMENT_AUDIT_SPEC,
    DOCUMENT_TYPE_TO_MACRO_CATEGORY,
    ValidatedDocumentRecord,
    get_recommended_stage3_metadata_schema,
    validate_inventory,
)
from src.document_processing.pdf_extractor import (
    DocumentExtractionResult,
    PageExtraction,
    PDFExtractor,
)
from src.document_processing.segmentation_validator import (
    ENTITY_DISTINCTION_FRAMEWORK,
    SEMANTIC_ENTITY_TYPES,
    SPAN_CLASSIFICATIONS,
    VALID_STATUSES,
    UncoveredCharSpan,
    UnitValidationResult,
    run_segmentation_validation,
)
from src.document_processing.txt_inventory import (
    DocumentInventoryItem,
    InventorySummary,
    TxtDocumentInventorizer,
)

__all__ = [
    "MULTI_BRANCH_STRUCTURAL_SPECS",
    "CompetitionBranchUnit",
    "segment_documents",
    "BRANCH_TO_DOMAIN",
    "DOCUMENT_AUDIT_SPEC",
    "DOCUMENT_TYPE_TO_MACRO_CATEGORY",
    "ValidatedDocumentRecord",
    "get_recommended_stage3_metadata_schema",
    "validate_inventory",
    "DocumentExtractionResult",
    "PageExtraction",
    "PDFExtractor",
    "ENTITY_DISTINCTION_FRAMEWORK",
    "SEMANTIC_ENTITY_TYPES",
    "SPAN_CLASSIFICATIONS",
    "VALID_STATUSES",
    "UncoveredCharSpan",
    "UnitValidationResult",
    "run_segmentation_validation",
    "DocumentInventoryItem",
    "InventorySummary",
    "TxtDocumentInventorizer",
]
