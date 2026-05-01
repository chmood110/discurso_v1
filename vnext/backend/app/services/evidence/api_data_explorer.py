from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.integrations.banxico_client import BanxicoClient
from app.services.integrations.inegi_client import InegiClient


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = PROJECT_ROOT / "app" / "data" / "support" / "api_exploration_catalog.json"


class ApiDataExplorer:
    """
    Explora qué información puede aportar cada API.

    No modifica base de datos.
    No genera PDF.
    Solo devuelve una matriz para decidir qué información conviene usar.
    """

    def __init__(
        self,
        inegi_client: InegiClient | None = None,
        banxico_client: BanxicoClient | None = None,
    ) -> None:
        self.inegi = inegi_client or InegiClient()
        self.banxico = banxico_client or BanxicoClient()

    def load_catalog(self) -> dict[str, Any]:
        if not CATALOG_PATH.exists():
            raise FileNotFoundError(f"No existe el catálogo: {CATALOG_PATH}")

        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    async def explore_static_catalog(self) -> list[dict[str, Any]]:
        """
        Devuelve una matriz inicial con los temas candidatos del catálogo.

        Esta primera versión no hace llamadas masivas a APIs.
        Sirve para visualizar y discutir qué vale la pena integrar.
        """
        catalog = self.load_catalog()
        rows: list[dict[str, Any]] = []

        for api_name, api_info in catalog.items():
            for topic in api_info.get("candidate_topics", []):
                rows.append(
                    {
                        "api": api_name,
                        "api_description": api_info.get("description"),
                        "api_status": api_info.get("status"),
                        "priority": api_info.get("priority"),
                        "topic": topic.get("name"),
                        "target_section": topic.get("target_section"),
                        "target_field": topic.get("target_field"),
                        "geographic_level": topic.get("geographic_level"),
                        "use_in_pdf": topic.get("use_in_pdf"),
                        "notes": topic.get("notes"),
                    }
                )

        return rows

    async def test_banxico_reference_rate(self) -> dict[str, Any]:
        """
        Prueba técnica con una serie Banxico conocida.
        No implica que deba usarse en el PDF.
        """
        payload = await self.banxico.get_latest_observation("SF43773")
        normalized = self.banxico.normalize_latest_observation(payload)

        return {
            "api": "banxico_sie",
            "topic": "Tasa de fondeo bancario",
            "series_id": normalized["series_id"],
            "title": normalized["title"],
            "value": normalized["value"],
            "date": normalized["date"],
            "source": normalized["source"],
            "geographic_level": "national",
            "use_in_pdf": False,
            "notes": "Prueba técnica de conectividad; no usar como indicador territorial principal.",
        }

    async def build_exploration_report(self) -> dict[str, Any]:
        static_rows = await self.explore_static_catalog()

        live_tests: list[dict[str, Any]] = []

        try:
            live_tests.append(await self.test_banxico_reference_rate())
        except Exception as exc:
            live_tests.append(
                {
                    "api": "banxico_sie",
                    "topic": "Tasa de fondeo bancario",
                    "error": str(exc),
                    "use_in_pdf": False,
                }
            )

        return {
            "summary": {
                "total_candidate_topics": len(static_rows),
                "live_tests": len(live_tests),
                "recommended_next_step": (
                    "Seleccionar primero indicadores municipales de INEGI "
                    "y series estatales de Banxico realmente útiles para el análisis territorial."
                ),
            },
            "candidate_topics": static_rows,
            "live_tests": live_tests,
        }