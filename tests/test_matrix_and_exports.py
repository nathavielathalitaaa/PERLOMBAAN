"""Tests for Competition Requirement Matrix generation, DataFrame conversion, and exports."""

import json
from pathlib import Path
import pandas as pd
import pytest
from sqlalchemy.orm import Session

from src.analysis.exporter import CompetitionExporter
from src.analysis.matrix import CompetitionMatrixBuilder
from src.competency_mapping.service import CompetencyService
from src.data_collection.schemas import (
    Classification,
    CompetencyCreate,
    CompetitionCreate,
    EvidenceCreate,
    IndicatorCreate,
    IndicatorType,
    MappingBasis,
    RelationType,
    RequirementCompetencyCreate,
    RequirementCreate,
    RequirementIndicatorCreate,
    RequirementType,
    SourceDocumentCreate,
    SourceStatus,
)
from src.indicator_mapping.service import IndicatorService
from src.requirement_extraction.service import RequirementService


def test_matrix_builder_and_export_roundtrip(
    db_session: Session, sample_pdf: Path, tmp_path: Path
):
    """Test full matrix construction, dataframe flattening, export to CSV/JSON, and roundtrip data integrity."""
    # 1. Setup Competition
    comp = RequirementService.create_competition(
        CompetitionCreate(
            name="Matrix Cup",
            category="Data Science",
            organizer="Data Society",
            year=2024,
            description="National Analytics Challenge",
        ),
        db_session,
    )

    # 2. Setup Source Document
    doc = RequirementService.register_source_document(
        SourceDocumentCreate(
            competition_id=comp.id,
            title="Panduan Matrix Cup",
            file_path=str(sample_pdf),
        ),
        db_session,
    )

    # 3. Setup Requirements
    req = RequirementService.create_requirement(
        RequirementCreate(
            competition_id=comp.id,
            description="Model harus dievaluasi menggunakan metrik F1-score",
            requirement_type=RequirementType.TECHNICAL,
            classification=Classification.EVALUATION_CRITERIA,
            source_status=SourceStatus.EXPLICIT,
        ),
        db_session,
    )

    # 4. Attach Evidence
    ev = RequirementService.add_evidence(
        EvidenceCreate(
            source_document_id=doc.id,
            requirement_id=req.id,
            page_number=2,
            section="Kriteria Penilaian",
            excerpt="Model dievaluasi dengan F1-Score minimal 0.85.",
        ),
        db_session,
    )

    # 5. Setup Indicator and Link
    ind = IndicatorService.create_indicator(
        IndicatorCreate(
            code="IND_ACCURACY",
            name="Model Performance",
            definition="Akurasi dan reliabilitas model prediktif.",
            category="Technical Evaluation",
            indicator_type=IndicatorType.QUANTITATIVE,
        ),
        db_session,
    )
    IndicatorService.link_requirement_indicator(
        RequirementIndicatorCreate(
            requirement_id=req.id,
            indicator_id=ind.id,
            weight=40.0,
            relation_type=RelationType.PRIMARY_CRITERION,
            mapping_status=SourceStatus.EXPLICIT,
        ),
        db_session,
    )

    # 6. Setup Competency and Map
    comp_skill = CompetencyService.create_competency(
        CompetencyCreate(
            code="COMP_ML_OPS",
            name="Machine Learning Operations",
            definition="Kemampuan deployment dan evaluasi model ML.",
            category="Technical",
        ),
        db_session,
    )
    CompetencyService.map_requirement_competency(
        RequirementCompetencyCreate(
            requirement_id=req.id,
            competency_id=comp_skill.id,
            mapping_basis=MappingBasis.DIRECT_TEXT,
            mapping_status=SourceStatus.EXPLICIT,
            evidence_id=ev.id,
        ),
        db_session,
    )

    # 7. Build Hierarchical Matrix
    matrix = CompetitionMatrixBuilder.build_matrix(comp.id, db_session)
    assert matrix["competition"]["name"] == "Matrix Cup"
    assert matrix["provenance_summary"]["total_requirements"] == 1
    assert matrix["provenance_summary"]["explicit_requirements"] == 1
    assert matrix["provenance_summary"]["citation_coverage_percentage"] == 100.0

    req_data = matrix["requirements"][0]
    assert len(req_data["indicators"]) == 1
    assert req_data["indicators"][0]["code"] == "IND_ACCURACY"
    assert len(req_data["competencies"]) == 1
    assert req_data["competencies"][0]["code"] == "COMP_ML_OPS"
    assert len(req_data["evidences"]) == 1

    # 8. Test Flattening to DataFrame
    df = CompetitionMatrixBuilder.to_dataframe(matrix)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "requirement_description" in df.columns
    assert "indicator_code" in df.columns
    assert "competency_code" in df.columns
    assert "source_document" in df.columns
    assert "page_number" in df.columns
    assert df.iloc[0]["indicator_code"] == "IND_ACCURACY"
    assert df.iloc[0]["competency_code"] == "COMP_ML_OPS"
    assert df.iloc[0]["page_number"] == 2

    # 9. Test Export to JSON and CSV
    json_path = tmp_path / "test_matrix.json"
    csv_path = tmp_path / "test_matrix.csv"

    CompetitionExporter.export_to_json(matrix, json_path)
    CompetitionExporter.export_to_csv(matrix, csv_path)

    assert json_path.exists()
    assert csv_path.exists()

    # 10. Verify Roundtrip Lossless Traceability
    with open(json_path, "r", encoding="utf-8") as f:
        reloaded_json = json.load(f)
    assert reloaded_json["competition"]["id"] == comp.id
    assert reloaded_json["requirements"][0]["evidences"][0]["page_number"] == 2

    reloaded_df = pd.read_csv(csv_path)
    assert len(reloaded_df) == 1
    assert reloaded_df.iloc[0]["requirement_source_status"] == "explicit"
    assert reloaded_df.iloc[0]["excerpt"] == "Model dievaluasi dengan F1-Score minimal 0.85."

