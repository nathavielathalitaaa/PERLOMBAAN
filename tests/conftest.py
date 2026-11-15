"""Pytest fixtures for AI Competition Mentor."""

import tempfile
from pathlib import Path
from typing import Generator

import pymupdf  # PyMuPDF
import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.connection import get_engine, get_session_factory, init_db


@pytest.fixture(scope="function")
def test_engine() -> Engine:
    """Create an isolated in-memory SQLite engine with foreign keys enabled."""
    engine = get_engine("sqlite:///:memory:")
    init_db(engine)
    return engine


@pytest.fixture(scope="function")
def session_factory(test_engine: Engine) -> sessionmaker[Session]:
    """Provide a session factory for test engine."""
    return get_session_factory(test_engine)


@pytest.fixture(scope="function")
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Provide an isolated database session with automatic rollback."""
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def sample_pdf(tmp_path: Path) -> Path:
    """Generate a valid multi-page PDF document for testing text and evidence extraction."""
    pdf_path = tmp_path / "gemastik_pedoman_2024.pdf"
    doc = pymupdf.open()

    # Page 1: General Info & Eligibility
    page1 = doc.new_page()
    page1.insert_text(
        (50, 72),
        "PANDUAN GEMASTIK XVII 2024\n"
        "Divisi: Pengembangan Perangkat Lunak\n"
        "Ketentuan Peserta: Mahasiswa aktif S1/D4/D3 di perguruan tinggi Indonesia.\n"
        "Setiap tim terdiri dari 3 orang mahasiswa dengan 1 dosen pembimbing.",
        fontsize=11,
    )

    # Page 2: Evaluation Rubric
    page2 = doc.new_page()
    page2.insert_text(
        (50, 72),
        "KRITERIA PENILAIAN PROPOSAL & PRODUK\n"
        "1. Inovasi dan Keaslian Ide (Bobot: 30%)\n"
        "2. Kualitas Arsitektur dan Rekayasa Perangkat Lunak (Bobot: 35%)\n"
        "3. Kemanfaatan dan Dampak Solusi (Bobot: 20%)\n"
        "4. Kualitas Presentasi dan Video Demo (Bobot: 15%)",
        fontsize=11,
    )

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path
