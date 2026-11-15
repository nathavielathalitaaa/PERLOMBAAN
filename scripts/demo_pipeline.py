"""End-to-End demonstration script for AI Competition Mentor V0.1 Foundation.

Demonstrates:
1. Database initialization.
2. Competency taxonomy seeding.
3. Competition registration.
4. Document registration & cryptographic hash calculation.
5. Explicit & Inferred requirement extraction with evidence linking.
6. Indicator rubric mapping with weights.
7. Competency requirement mapping.
8. Rigorous provenance integrity audit.
9. Matrix generation and export to CSV & JSON.
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pymupdf

from config.settings import EXPORTS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.analysis.exporter import CompetitionExporter
from src.analysis.matrix import CompetitionMatrixBuilder
from src.competency_mapping.service import CompetencyService
from src.data_collection.schemas import (
    Classification,
    CompetitionCreate,
    EvidenceCreate,
    EvidenceType,
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
from src.database.connection import get_db_session, init_db
from src.evaluation.integrity import DataIntegrityAuditor
from src.indicator_mapping.service import IndicatorService
from src.requirement_extraction.service import RequirementService


def create_sample_pdf(output_path: Path) -> Path:
    """Create a sample competition guidebook PDF."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()

    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "PANDUAN GEMASTIK XVII 2024\n"
        "Divisi: Pengembangan Perangkat Lunak (Software Development)\n\n"
        "KETENTUAN UMUM PESERTA:\n"
        "1. Peserta adalah mahasiswa aktif program Sarjana/Diploma di PTN/PTS Indonesia.\n"
        "2. Setiap tim terdiri dari maksimal 3 (tiga) orang mahasiswa dari perguruan tinggi yang sama.\n"
        "3. Setiap tim wajib didampingi oleh 1 (satu) dosen pembimbing resmi.\n\n"
        "KETENTUAN KARYA CIPTA:\n"
        "Solusi perangkat lunak yang diajukan harus orisinal, fungsional, dan dapat dioperasikan.",
        fontsize=11,
    )

    p2 = doc.new_page()
    p2.insert_text(
        (50, 72),
        "RUBRIK PENILAIAN TAHAP FINAL:\n"
        "Kriteria 1: Inovasi & Kebaruan Ide (Bobot: 30%)\n"
        "Kriteria 2: Kompleksitas Arsitektur & Rekayasa Perangkat Lunak (Bobot: 35%)\n"
        "Kriteria 3: Kemanfaatan dan Skalabilitas Solusi (Bobot: 20%)\n"
        "Kriteria 4: Presentasi & Demo Produk (Bobot: 15%)\n",
        fontsize=11,
    )

    doc.save(str(output_path))
    doc.close()
    return output_path


def main():
    print("=" * 70)
    print("AI COMPETITION MENTOR - V0.1 FOUNDATION PIPELINE RUN")
    print("=" * 70)

    # 1. Initialize SQLite Database
    init_db()
    print("[1] Database initialized successfully.")

    with get_db_session() as session:
        # 2. Seed Default Competency Taxonomy
        seeded_count = CompetencyService.seed_default_taxonomy(session)
        print(f"[2] Competency taxonomy ready ({seeded_count} new competencies seeded).")

        # 3. Create Sample Guidebook PDF
        pdf_file = RAW_DATA_DIR / "competitions" / "gemastik_2024_panduan.pdf"
        create_sample_pdf(pdf_file)
        print(f"[3] Sample guidebook generated: {pdf_file}")

        # 4. Register Competition
        comp = RequirementService.create_competition(
            CompetitionCreate(
                name="GEMASTIK XVII 2024",
                category="Software Engineering",
                organizer="Balai Pengembangan Talenta Indonesia (BPTI) - Kemendikbudristek",
                year=2024,
                description="Pagelaran Mahasiswa Nasional Bidang Teknologi Informasi dan Komunikasi ke-17.",
                official_url="https://gemastik.kemdikbud.go.id",
            ),
            session,
        )
        print(f"[4] Competition registered: {comp.name} (ID: {comp.id})")

        # 5. Register Source Document
        doc = RequirementService.register_source_document(
            SourceDocumentCreate(
                competition_id=comp.id,
                title="Buku Panduan Gemastik XVII 2024",
                file_path=str(pdf_file),
                version="1.0",
            ),
            session,
        )
        print(f"[5] Document registered: {doc.title} (SHA-256: {doc.file_hash[:16]}...)")

        # 6. Extract Requirements (Explicit vs Inferred)
        req_eligibility = RequirementService.create_requirement(
            RequirementCreate(
                competition_id=comp.id,
                description="Setiap tim terdiri dari maksimal 3 (tiga) orang mahasiswa dengan 1 dosen pembimbing.",
                requirement_type=RequirementType.ADMINISTRATIVE,
                classification=Classification.MANDATORY_ELIGIBILITY,
                source_status=SourceStatus.EXPLICIT,
            ),
            session,
        )

        req_architecture = RequirementService.create_requirement(
            RequirementCreate(
                competition_id=comp.id,
                description="Karya perangkat lunak harus memiliki arsitektur modular dan rekayasa yang teruji.",
                requirement_type=RequirementType.TECHNICAL,
                classification=Classification.EVALUATION_CRITERIA,
                source_status=SourceStatus.EXPLICIT,
            ),
            session,
        )

        req_inferred_ops = RequirementService.create_requirement(
            RequirementCreate(
                competition_id=comp.id,
                description="Disarankan mengimplementasikan pipeline CI/CD untuk menjamin reliabilitas deployment demo.",
                requirement_type=RequirementType.TECHNICAL,
                classification=Classification.GENERAL_GUIDELINE,
                source_status=SourceStatus.INFERRED,
            ),
            session,
        )

        # 7. Ground Requirements with Verifiable Evidence
        RequirementService.add_evidence(
            EvidenceCreate(
                source_document_id=doc.id,
                requirement_id=req_eligibility.id,
                page_number=1,
                section="Ketentuan Umum Peserta",
                excerpt="Setiap tim terdiri dari maksimal 3 (tiga) orang mahasiswa... Setiap tim wajib didampingi oleh 1 dosen pembimbing.",
                evidence_type=EvidenceType.DIRECT_QUOTE,
            ),
            session,
        )

        RequirementService.add_evidence(
            EvidenceCreate(
                source_document_id=doc.id,
                requirement_id=req_architecture.id,
                page_number=2,
                section="Rubrik Penilaian Tahap Final",
                excerpt="Kriteria 2: Kompleksitas Arsitektur & Rekayasa Perangkat Lunak (Bobot: 35%)",
                evidence_type=EvidenceType.DIRECT_QUOTE,
            ),
            session,
        )
        print("[6] Requirements and Evidence citations recorded.")

        # 8. Create Indicators & Link
        ind_arch = IndicatorService.create_indicator(
            IndicatorCreate(
                code="IND_ARCH_COMPLEXITY",
                name="Kualitas Arsitektur Perangkat Lunak",
                definition="Tingkat kematangan desain sistem, modularitas, dan pola arsitektur yang digunakan.",
                category="Software Engineering",
                indicator_type=IndicatorType.RUBRIC_SCALE,
            ),
            session,
        )

        IndicatorService.link_requirement_indicator(
            RequirementIndicatorCreate(
                requirement_id=req_architecture.id,
                indicator_id=ind_arch.id,
                weight=35.0,
                relation_type=RelationType.PRIMARY_CRITERION,
                mapping_status=SourceStatus.EXPLICIT,
            ),
            session,
        )
        print("[7] Evaluation indicators linked with official rubric weights.")

        # 9. Map Competencies
        comp_se = CompetencyService.get_competency_by_code("COMP_SOFTWARE_ENG", session)
        comp_collab = CompetencyService.get_competency_by_code("COMP_TEAM_COLLABORATION", session)

        CompetencyService.map_requirement_competency(
            RequirementCompetencyCreate(
                requirement_id=req_architecture.id,
                competency_id=comp_se.id,
                mapping_basis=MappingBasis.DIRECT_TEXT,
                mapping_status=SourceStatus.EXPLICIT,
            ),
            session,
        )

        CompetencyService.map_requirement_competency(
            RequirementCompetencyCreate(
                requirement_id=req_eligibility.id,
                competency_id=comp_collab.id,
                mapping_basis=MappingBasis.INFERRED_FROM_INDICATOR,
                mapping_status=SourceStatus.INFERRED,
            ),
            session,
        )
        print("[8] Competencies mapped to requirements with provenance status.")

        # 10. Rigorous Research Integrity Audit
        audit = DataIntegrityAuditor.audit_competition(comp.id, session)
        print("\n" + "-" * 50)
        print("DATA INTEGRITY AUDIT REPORT:")
        print(f"  Fully Grounded: {audit['is_fully_grounded']}")
        print(f"  Total Requirements: {audit['total_requirements']}")
        print(f"  Explicit Requirements: {audit['total_requirements'] - audit['unverified_requirements'] - audit['inferred_requirements']}")
        print(f"  Inferred Requirements: {audit['inferred_requirements']}")
        print(f"  Unsupported Explicit Items: {audit['unsupported_explicit_requirements']}")
        print(f"  Warnings: {len(audit['warnings'])}")
        print("-" * 50)

        # 11. Export Matrix Bundle
        bundle = CompetitionExporter.export_competition_bundle(comp.id, session)
        print(f"\n[9] Matrix exported to JSON: {bundle['json_path']}")
        print(f"[10] Matrix exported to CSV:  {bundle['csv_path']}")

    print("\nPipeline execution completed successfully.")


if __name__ == "__main__":
    main()
