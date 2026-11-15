"""Competition Requirement Matrix builder and flattening engine."""

import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from src.database.models import (
    Competition,
    Evidence,
    Requirement,
)

logger = logging.getLogger(__name__)


class CompetitionMatrixBuilder:
    """Constructs the research-grade Competition Requirement Matrix with provenance tracking."""

    @classmethod
    def build_matrix(cls, competition_id: str, session: Session) -> Dict[str, Any]:
        """Build the full hierarchical matrix for a competition."""
        comp = session.get(Competition, competition_id)
        if not comp:
            raise ValueError(f"Competition not found with ID: {competition_id}")

        documents_data = [
            {
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "file_path": doc.file_path,
                "file_hash": doc.file_hash,
                "version": doc.version,
                "publication_date": str(doc.publication_date) if doc.publication_date else None,
                "collected_at": doc.collected_at.isoformat() if doc.collected_at else None,
            }
            for doc in comp.documents
        ]

        doc_title_map = {doc.id: doc.title for doc in comp.documents}

        requirements_data: List[Dict[str, Any]] = []
        explicit_count = 0
        inferred_count = 0
        unverified_count = 0
        requirements_with_evidence = 0

        for req in comp.requirements:
            # Count provenance statuses
            if req.source_status == "explicit":
                explicit_count += 1
            elif req.source_status == "inferred":
                inferred_count += 1
            else:
                unverified_count += 1

            if req.evidences:
                requirements_with_evidence += 1

            # Indicators linked to this requirement
            indicators = [
                {
                    "indicator_id": link.indicator.id,
                    "code": link.indicator.code,
                    "name": link.indicator.name,
                    "definition": link.indicator.definition,
                    "category": link.indicator.category,
                    "indicator_type": link.indicator.indicator_type,
                    "weight": link.weight,
                    "relation_type": link.relation_type,
                    "mapping_status": link.mapping_status,
                }
                for link in req.requirement_indicators
            ]

            # Competencies mapped to this requirement
            competencies = [
                {
                    "competency_id": cmap.competency.id,
                    "code": cmap.competency.code,
                    "name": cmap.competency.name,
                    "definition": cmap.competency.definition,
                    "category": cmap.competency.category,
                    "mapping_basis": cmap.mapping_basis,
                    "mapping_status": cmap.mapping_status,
                    "evidence_id": cmap.evidence_id,
                }
                for cmap in req.requirement_competencies
            ]

            # Evidence excerpts grounding this requirement
            evidences = [
                {
                    "evidence_id": ev.id,
                    "source_document_id": ev.source_document_id,
                    "source_document_title": doc_title_map.get(ev.source_document_id, "Unknown"),
                    "page_number": ev.page_number,
                    "section": ev.section,
                    "excerpt": ev.excerpt,
                    "evidence_type": ev.evidence_type,
                    "confidence_level": ev.confidence_level,
                }
                for ev in req.evidences
            ]

            requirements_data.append({
                "id": req.id,
                "description": req.description,
                "requirement_type": req.requirement_type,
                "classification": req.classification,
                "source_status": req.source_status,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "indicators": indicators,
                "competencies": competencies,
                "evidences": evidences,
            })

        total_reqs = len(comp.requirements)
        coverage_rate = (requirements_with_evidence / total_reqs * 100.0) if total_reqs > 0 else 0.0

        provenance_summary = {
            "total_requirements": total_reqs,
            "explicit_requirements": explicit_count,
            "inferred_requirements": inferred_count,
            "unverified_requirements": unverified_count,
            "requirements_with_evidence": requirements_with_evidence,
            "citation_coverage_percentage": round(coverage_rate, 2),
            "total_documents": len(comp.documents),
        }

        return {
            "competition": {
                "id": comp.id,
                "name": comp.name,
                "category": comp.category,
                "organizer": comp.organizer,
                "year": comp.year,
                "description": comp.description,
                "official_url": comp.official_url,
                "created_at": comp.created_at.isoformat() if comp.created_at else None,
                "updated_at": comp.updated_at.isoformat() if comp.updated_at else None,
            },
            "provenance_summary": provenance_summary,
            "documents": documents_data,
            "requirements": requirements_data,
        }

    @classmethod
    def to_dataframe(cls, matrix_dict: Dict[str, Any]) -> pd.DataFrame:
        """Flatten the matrix into a scientific research table (Pandas DataFrame)."""
        comp_info = matrix_dict["competition"]
        rows: List[Dict[str, Any]] = []

        for req in matrix_dict.get("requirements", []):
            base_row = {
                "competition_id": comp_info["id"],
                "competition_name": comp_info["name"],
                "competition_year": comp_info["year"],
                "competition_category": comp_info["category"],
                "requirement_id": req["id"],
                "requirement_description": req["description"],
                "requirement_type": req["requirement_type"],
                "classification": req["classification"],
                "requirement_source_status": req["source_status"],
            }

            # Evidence aggregation
            if req["evidences"]:
                primary_evidence = req["evidences"][0]
                base_row["source_document"] = primary_evidence["source_document_title"]
                base_row["page_number"] = primary_evidence["page_number"]
                base_row["section"] = primary_evidence["section"]
                base_row["excerpt"] = primary_evidence["excerpt"]
                base_row["evidence_confidence"] = primary_evidence["confidence_level"]
            else:
                base_row["source_document"] = None
                base_row["page_number"] = None
                base_row["section"] = None
                base_row["excerpt"] = None
                base_row["evidence_confidence"] = None

            # Flatten indicators and competencies
            indicators = req.get("indicators", [])
            competencies = req.get("competencies", [])

            if not indicators and not competencies:
                row = dict(base_row)
                row.update({
                    "indicator_code": None,
                    "indicator_name": None,
                    "indicator_weight": None,
                    "indicator_mapping_status": None,
                    "competency_code": None,
                    "competency_name": None,
                    "competency_category": None,
                    "competency_mapping_status": None,
                })
                rows.append(row)
            else:
                # Pairwise product or zip
                ind_list = indicators if indicators else [{}]
                comp_list = competencies if competencies else [{}]

                for ind in ind_list:
                    for cmp in comp_list:
                        row = dict(base_row)
                        row.update({
                            "indicator_code": ind.get("code"),
                            "indicator_name": ind.get("name"),
                            "indicator_weight": ind.get("weight"),
                            "indicator_mapping_status": ind.get("mapping_status"),
                            "competency_code": cmp.get("code"),
                            "competency_name": cmp.get("name"),
                            "competency_category": cmp.get("category"),
                            "competency_mapping_status": cmp.get("mapping_status"),
                        })
                        rows.append(row)

        return pd.DataFrame(rows)

