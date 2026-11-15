"""Data exporter for competition matrices in scientific formats (CSV, JSON)."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from config.settings import EXPORTS_DIR
from src.analysis.matrix import CompetitionMatrixBuilder

logger = logging.getLogger(__name__)


class CompetitionExporter:
    """Service to export competition matrices for downstream statistical analysis and reporting."""

    @staticmethod
    def export_to_json(matrix_data: Dict[str, Any], output_path: str | Path) -> Path:
        """Export hierarchical matrix to formatted JSON preserving complete provenance."""
        target_path = Path(output_path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(matrix_data, f, indent=2, ensure_ascii=False)

        logger.info("Exported JSON matrix to: %s", target_path)
        return target_path

    @staticmethod
    def export_to_csv(matrix_data: Dict[str, Any], output_path: str | Path) -> Path:
        """Export flattened matrix to CSV for tabular and statistical workflows."""
        target_path = Path(output_path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        df = CompetitionMatrixBuilder.to_dataframe(matrix_data)
        df.to_csv(target_path, index=False, encoding="utf-8")

        logger.info("Exported CSV matrix to: %s (%d rows)", target_path, len(df))
        return target_path

    @classmethod
    def export_competition_bundle(
        cls,
        competition_id: str,
        session: Session,
        output_dir: Optional[str | Path] = None,
    ) -> Dict[str, Path]:
        """Generate both JSON and CSV exports for a given competition in the exports directory."""
        matrix = CompetitionMatrixBuilder.build_matrix(competition_id, session)
        comp_name = matrix["competition"]["name"].lower().replace(" ", "_").replace("/", "_")
        comp_year = matrix["competition"]["year"]
        
        base_dir = Path(output_dir) if output_dir else EXPORTS_DIR
        base_dir.mkdir(parents=True, exist_ok=True)

        json_file = base_dir / f"{comp_name}_{comp_year}_matrix.json"
        csv_file = base_dir / f"{comp_name}_{comp_year}_matrix.csv"

        cls.export_to_json(matrix, json_file)
        cls.export_to_csv(matrix, csv_file)

        return {
            "json_path": json_file,
            "csv_path": csv_file,
        }

