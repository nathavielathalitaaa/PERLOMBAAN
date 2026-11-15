"""Research data integrity, evidence verification, and provenance auditing."""

import logging
from pathlib import Path
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from src.database.models import (
    Competition,
    Evidence,
    Requirement,
    SourceDocument,
)
from src.document_processing.pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


class DataIntegrityAuditor:
    """Audits scientific data provenance, citation completeness, and document integrity."""

    @classmethod
    def audit_competition(cls, competition_id: str, session: Session) -> Dict[str, Any]:
        """Perform a rigorous provenance and referential audit on a competition."""
        session.expire_all()
        comp = session.get(Competition, competition_id)
        if not comp:
            raise ValueError(f"Competition not found with ID: {competition_id}")

        issues: List[str] = []
        warnings: List[str] = []

        # 1. Document Integrity Check
        docs = comp.documents
        if not docs:
            issues.append(f"Competition '{comp.name}' has no registered source documents.")

        for doc in docs:
            doc_path = Path(doc.file_path)
            if not doc_path.exists():
                issues.append(f"Document file missing on disk: {doc.file_path} (Doc ID: {doc.id})")
            elif doc.file_hash:
                current_hash = PDFExtractor.calculate_sha256(doc_path)
                if current_hash != doc.file_hash:
                    issues.append(
                        f"Document SHA-256 mismatch for '{doc.title}'. "
                        f"Expected {doc.file_hash}, calculated {current_hash}."
                    )

        # 2. Requirement Provenance & Evidence Grounding Check
        reqs = comp.requirements
        unsupported_explicit_count = 0
        unverified_count = 0
        inferred_count = 0

        for req in reqs:
            evidence_count = len(req.evidences)
            
            if req.source_status == "explicit" and evidence_count == 0:
                unsupported_explicit_count += 1
                issues.append(
                    f"Violation of Research Integrity: Requirement '{req.id}' is marked as EXPLICIT "
                    f"but contains 0 attached evidence citations."
                )
            elif req.source_status == "unverified":
                unverified_count += 1
                warnings.append(
                    f"Requirement '{req.id}' is UNVERIFIED: Requires human review and citation."
                )
            elif req.source_status == "inferred":
                inferred_count += 1

            # Check competency mappings
            for cmap in req.requirement_competencies:
                if cmap.mapping_status == "explicit" and not cmap.evidence_id:
                    warnings.append(
                        f"Competency mapping (Req: {req.id}, Comp: {cmap.competency_id}) "
                        f"marked EXPLICIT without direct evidence citation."
                    )

        # 3. Overall Research Health
        is_fully_grounded = (len(issues) == 0 and unsupported_explicit_count == 0)

        report = {
            "competition_id": comp.id,
            "competition_name": comp.name,
            "is_fully_grounded": is_fully_grounded,
            "total_documents": len(docs),
            "total_requirements": len(reqs),
            "unsupported_explicit_requirements": unsupported_explicit_count,
            "unverified_requirements": unverified_count,
            "inferred_requirements": inferred_count,
            "critical_issues": issues,
            "warnings": warnings,
        }

        logger.info(
            "Integrity audit for '%s': Fully Grounded = %s (Issues: %d, Warnings: %d)",
            comp.name,
            is_fully_grounded,
            len(issues),
            len(warnings),
        )
        return report
