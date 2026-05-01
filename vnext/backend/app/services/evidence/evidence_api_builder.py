from __future__ import annotations

import logging
from typing import Any

from app.services.evidence.denue_normalizer import normalize_denue_records
from app.services.integrations.banxico_client import BanxicoClient
from app.services.integrations.inegi_client import InegiClient

logger = logging.getLogger(__name__)


class EvidenceApiBuilder:
    """
    Construye evidencia territorial complementaria usando APIs oficiales.

    No reemplaza reference_data.
    Agrega datos complementarios para enriquecer EvidenceRecordDB.

    Importante:
        - INEGI DENUE es evidencia territorial directa.
        - Banxico es contexto macro nacional.
        - Banxico nunca debe bloquear DENUE.
    """

    def __init__(
        self,
        inegi_client: InegiClient | None = None,
        banxico_client: BanxicoClient | None = None,
    ) -> None:
        self.inegi = inegi_client or InegiClient()

        # No instanciamos Banxico obligatoriamente aquí porque puede fallar
        # si BANXICO_TOKEN no está configurado. Banxico es opcional.
        self.banxico = banxico_client

    async def build_api_snapshot(
        self,
        *,
        municipality_id: str,
        municipality_name: str,
        lat: float | None = None,
        lon: float | None = None,
        entity_code: str | None = None,
        municipality_code: str | None = None,
        denue_radius_m: int = 1000,
        denue_page_size: int = 500,
        denue_max_records: int = 5000,
    ) -> dict[str, Any]:
        social_data: dict[str, Any] = {}
        infrastructure_data: dict[str, Any] = {}
        economic_data: dict[str, Any] = {}

        sources_used: list[str] = []
        sources_failed: list[str] = []
        geographic_fallbacks: list[str] = []

        # ------------------------------------------------------------------
        # BANXICO — contexto macro opcional.
        # No debe bloquear DENUE.
        # ------------------------------------------------------------------
        try:
            banxico_client = self.banxico or BanxicoClient()

            payload = await banxico_client.get_latest_observation("SF43773")
            normalized = banxico_client.normalize_latest_observation(payload)

            economic_data["banxico_reference_rate"] = {
                "value": normalized.get("value"),
                "date": normalized.get("date"),
                "series_id": normalized.get("series_id"),
                "title": normalized.get("title"),
                "source": normalized.get("source"),
                "scope": "national",
                "origin": "api",
                "use_in_pdf": False,
            }

            sources_used.append("Banxico SIE")

        except Exception as exc:
            logger.info(
                "Banxico SIE skipped for %s: %s",
                municipality_id,
                exc,
            )
            sources_failed.append(f"Banxico SIE: {exc}")

        # ------------------------------------------------------------------
        # INEGI DENUE — evidencia territorial directa.
        # Método principal: BuscarAreaAct por entidad + municipio.
        # ------------------------------------------------------------------
        denue_records: list[dict[str, Any]] = []

        if entity_code and municipality_code:
            try:
                logger.info(
                    "DENUE BuscarAreaAct request | municipality_id=%s municipality_name=%s entity_code=%s municipality_code=%s page_size=%s max_records=%s",
                    municipality_id,
                    municipality_name,
                    entity_code,
                    municipality_code,
                    denue_page_size,
                    denue_max_records,
                )

                denue_records = await self.inegi.search_denue_by_municipality_all(
                    entity_code=entity_code,
                    municipality_code=municipality_code,
                    term="0",
                    page_size=denue_page_size,
                    max_records=denue_max_records,
                )

                logger.info(
                    "DENUE BuscarAreaAct response | municipality_id=%s records=%s",
                    municipality_id,
                    len(denue_records),
                )

                if denue_records:
                    geographic_fallbacks.append(
                        f"INEGI DENUE API consultada por municipio con BuscarAreaAct: entidad={entity_code}, municipio={municipality_code}"
                    )
                else:
                    sources_failed.append(
                        "INEGI DENUE API BuscarAreaAct: la consulta devolvió 0 registros"
                    )

            except Exception as exc:
                logger.exception(
                    "INEGI DENUE BuscarAreaAct failed for %s",
                    municipality_id,
                )
                sources_failed.append(f"INEGI DENUE API BuscarAreaAct: {exc}")

        else:
            sources_failed.append(
                "INEGI DENUE API BuscarAreaAct: no se consultó porque faltan entity_code/municipality_code"
            )

        # ------------------------------------------------------------------
        # Fallback: DENUE por coordenadas.
        # En tu entorno este endpoint puede devolver HTTP 000, por eso queda
        # solo como respaldo.
        # ------------------------------------------------------------------
        if not denue_records and lat is not None and lon is not None:
            try:
                logger.info(
                    "DENUE Buscar fallback request | municipality_id=%s municipality_name=%s lat=%s lon=%s radius_m=%s",
                    municipality_id,
                    municipality_name,
                    lat,
                    lon,
                    denue_radius_m,
                )

                denue_records = await self.inegi.search_denue_by_area(
                    term="todos",
                    lat=lat,
                    lon=lon,
                    radius_m=denue_radius_m,
                )

                logger.info(
                    "DENUE Buscar fallback response | municipality_id=%s records=%s",
                    municipality_id,
                    len(denue_records),
                )

                if denue_records:
                    geographic_fallbacks.append(
                        f"INEGI DENUE API consultada por radio de {min(int(denue_radius_m), 5000)} m alrededor de la cabecera municipal"
                    )
                else:
                    sources_failed.append(
                        "INEGI DENUE API Buscar: la consulta por coordenadas devolvió 0 registros"
                    )

            except Exception as exc:
                logger.exception(
                    "INEGI DENUE Buscar fallback failed for %s",
                    municipality_id,
                )
                sources_failed.append(f"INEGI DENUE API Buscar: {exc}")

        elif not denue_records and (lat is None or lon is None):
            sources_failed.append(
                "INEGI DENUE API Buscar: no se consultó porque faltan coordenadas lat/lon"
            )

        # ------------------------------------------------------------------
        # Normalización DENUE.
        # ------------------------------------------------------------------
        if denue_records:
            try:
                denue_normalized = normalize_denue_records(
                    denue_records,
                    municipality_name=municipality_name,
                    source="INEGI DENUE API",
                )

                denue_economic = denue_normalized.get("economic_data", {})
                denue_infrastructure = denue_normalized.get(
                    "infrastructure_data",
                    {},
                )

                logger.info(
                    "DENUE normalized | municipality_id=%s economic_keys=%s infrastructure_keys=%s",
                    municipality_id,
                    list(denue_economic.keys()),
                    list(denue_infrastructure.keys()),
                )

                economic_data.update(denue_economic)
                infrastructure_data.update(denue_infrastructure)

                sources_used.append("INEGI DENUE API")
                sources_used.append("INEGI API configurada")

            except Exception as exc:
                logger.exception(
                    "DENUE normalization failed for %s",
                    municipality_id,
                )
                sources_failed.append(f"INEGI DENUE normalización: {exc}")

        return {
            "municipality_id": municipality_id,
            "municipality_name": municipality_name,
            "snapshot_version": "api-v3-denue-areaact",
            "collection_method": "reference_plus_api",
            "overall_confidence": 0.80,
            "municipal_coverage_pct": 0.70,
            "state_coverage_pct": 0.20,
            "estimated_coverage_pct": 0.10,
            "can_cite_as_municipal": True,
            "quality_label": "Alta — datos locales con enriquecimiento API",
            "methodology_disclaimer": (
                "La evidencia combina catálogos locales versionados con datos "
                "complementarios consultados en APIs oficiales de INEGI y Banxico. "
                "Los conteos DENUE deben interpretarse como establecimientos registrados, "
                "no como capacidad efectiva de atención o cobertura de servicios."
            ),
            "social_data": social_data,
            "economic_data": economic_data,
            "infrastructure_data": infrastructure_data,
            "sources_used": self._dedupe(sources_used),
            "sources_failed": self._dedupe(sources_failed),
            "geographic_fallbacks": self._dedupe(geographic_fallbacks),
        }

    def _dedupe(self, values: list[Any]) -> list[Any]:
        result: list[Any] = []
        seen: set[str] = set()

        for value in values:
            marker = str(value).strip()

            if not marker or marker in seen:
                continue

            seen.add(marker)
            result.append(value)

        return result