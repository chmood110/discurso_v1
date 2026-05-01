from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class InegiClient:
    """
    Cliente para APIs de INEGI.

    Incluye:
        - Banco de Indicadores.
        - DENUE por coordenadas: Buscar.
        - DENUE por entidad federativa: BuscarEntidad.
        - DENUE por entidad + municipio: BuscarAreaAct.

    Nota:
        En pruebas locales, el endpoint DENUE Buscar por coordenadas puede responder
        con HTTP/1.1 000. Por eso, para análisis municipal se recomienda usar
        search_denue_by_municipality(), basado en BuscarAreaAct.
    """

    BASE_INDICADORES = (
        "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR"
    )
    BASE_DENUE = "https://www.inegi.org.mx/app/api/denue/v1/consulta"

    def __init__(self, token: str | None = None, timeout: float = 45.0) -> None:
        self._token = (token or settings.INEGI_API_TOKEN or "").strip()
        self.timeout = timeout

        if not self._token:
            raise ValueError(
                "INEGI_API_TOKEN no está configurado. "
                "Verifica que exista en .env y que app.core.config.Settings lo cargue correctamente."
            )

    @property
    def token(self) -> str:
        return self._token

    # ─────────────────────────────────────────────────────────────────────
    # HTTP helpers
    # ─────────────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Connection": "close",
        }

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            timeout=self.timeout,
            connect=15.0,
            read=self.timeout,
            write=15.0,
            pool=15.0,
        )

    def _redact_token(self, url: str) -> str:
        return url.replace(self._token, "***TOKEN***")

    async def _get_json(self, url: str) -> Any:
        """
        GET JSON robusto.

        Estrategia:
            1. Intentar con httpx.
            2. Si httpx falla por protocolo/red, usar urllib como fallback.

        Nota:
            BuscarAreaAct funcionó correctamente con curl, pero se mantiene urllib
            como fallback por estabilidad frente a respuestas no estándar de INEGI.
        """
        try:
            return await self._get_json_httpx(url)
        except Exception as exc:
            logger.warning(
                "httpx failed for INEGI url=%s error=%s. Trying urllib fallback.",
                self._redact_token(url),
                exc,
            )
            return await asyncio.to_thread(self._get_json_urllib, url)

    async def _get_json_httpx(self, url: str) -> Any:
        transport = httpx.AsyncHTTPTransport(
            retries=1,
            http1=True,
            http2=False,
        )

        async with httpx.AsyncClient(
            timeout=self._timeout(),
            headers=self._headers(),
            follow_redirects=True,
            transport=transport,
            trust_env=False,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            if not response.text.strip():
                return []

            return response.json()

    def _get_json_urllib(self, url: str) -> Any:
        request = Request(
            url,
            headers=self._headers(),
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()

                if not raw:
                    return []

                text = raw.decode("utf-8", errors="replace").strip()

                if not text:
                    return []

                return json.loads(text)

        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(
                f"INEGI respondió con error HTTP {exc.code}: {body}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"No se pudo conectar con INEGI usando urllib: {exc}"
            ) from exc

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"INEGI devolvió una respuesta que no es JSON válido: {exc}"
            ) from exc

    def _as_records(self, data: Any, *, context: str) -> list[dict[str, Any]]:
        """
        Normaliza una respuesta DENUE a lista de diccionarios.

        Si INEGI devuelve un dict en lugar de una lista, se considera una respuesta
        no esperada para los métodos de búsqueda.
        """
        if isinstance(data, list):
            return [
                item
                for item in data
                if isinstance(item, dict)
            ]

        if isinstance(data, dict):
            raise RuntimeError(
                f"{context} devolvió una respuesta no esperada: {str(data)[:500]}"
            )

        return []

    # ─────────────────────────────────────────────────────────────────────
    # INEGI Indicadores
    # ─────────────────────────────────────────────────────────────────────

    async def get_indicator(
        self,
        indicator_id: str,
        *,
        geography: str,
        language: str = "es",
        recent: bool = True,
        source: str = "BIE",
    ) -> dict[str, Any]:
        """
        Consulta un indicador del Banco de Indicadores de INEGI.
        """
        recent_flag = "true" if recent else "false"

        url = (
            f"{self.BASE_INDICADORES}/{indicator_id}/{language}/{geography}/"
            f"{recent_flag}/{source}/2.0/{self._token}"
            "?type=json"
        )

        logger.info(
            "INEGI Indicadores request url=%s",
            self._redact_token(url),
        )

        data = await self._get_json(url)

        if not isinstance(data, dict):
            raise RuntimeError(
                f"INEGI Indicadores devolvió una respuesta no esperada: {str(data)[:500]}"
            )

        return data

    # ─────────────────────────────────────────────────────────────────────
    # DENUE: Buscar por coordenadas
    # ─────────────────────────────────────────────────────────────────────

    async def search_denue_by_area(
        self,
        *,
        term: str,
        lat: float,
        lon: float,
        radius_m: int = 5000,
    ) -> list[dict[str, Any]]:
        """
        Consulta establecimientos DENUE alrededor de una coordenada.

        Parámetros:
            term:
                Palabra a buscar. Para todos los establecimientos usar "todos".
            lat/lon:
                Coordenadas del centro de búsqueda.
            radius_m:
                Radio en metros. DENUE permite máximo 5,000.

        Nota:
            Este endpoint puede responder HTTP 000 en algunos entornos.
            Para análisis municipal, preferir search_denue_by_municipality().
        """
        if radius_m > 5000:
            radius_m = 5000

        if radius_m <= 0:
            radius_m = 1000

        safe_term = quote((term or "").strip() or "todos", safe="")

        url = (
            f"{self.BASE_DENUE}/Buscar/"
            f"{safe_term}/{lat},{lon}/{radius_m}/{self._token}"
        )

        logger.info(
            "INEGI DENUE Buscar request url=%s",
            self._redact_token(url),
        )

        data = await self._get_json(url)
        return self._as_records(data, context="INEGI DENUE Buscar")

    # ─────────────────────────────────────────────────────────────────────
    # DENUE: BuscarEntidad
    # ─────────────────────────────────────────────────────────────────────

    async def search_denue_by_entity(
        self,
        *,
        term: str,
        entity_code: str,
        start: int = 1,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Consulta DENUE por entidad federativa.

        Ejemplo:
            Tlaxcala = "29"

        La URL usa:
            BuscarEntidad/{term}/{entity_code}/{start}/{end}/{token}

        Donde:
            start = registro inicial
            end = registro final
        """
        safe_term = quote((term or "").strip() or "todos", safe="")
        entity = self._normalize_entity_code(entity_code)
        start, end = self._normalize_range(start=start, limit=limit)

        url = (
            f"{self.BASE_DENUE}/BuscarEntidad/"
            f"{safe_term}/{entity}/{start}/{end}/{self._token}"
        )

        logger.info(
            "INEGI DENUE BuscarEntidad request url=%s",
            self._redact_token(url),
        )

        data = await self._get_json(url)
        return self._as_records(data, context="INEGI DENUE BuscarEntidad")

    # ─────────────────────────────────────────────────────────────────────
    # DENUE: BuscarAreaAct por municipio
    # ─────────────────────────────────────────────────────────────────────

    async def search_denue_by_municipality(
        self,
        *,
        entity_code: str,
        municipality_code: str,
        term: str = "0",
        locality: str = "0",
        ageb: str = "0",
        block: str = "0",
        sector: str = "0",
        subsector: str = "0",
        branch: str = "0",
        class_code: str = "0",
        establishment_id: str = "0",
        start: int = 1,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Consulta DENUE usando BuscarAreaAct por entidad y municipio.

        Este método es el recomendado para análisis municipal porque consulta
        el municipio completo, no solo un radio de 5 km alrededor de una coordenada.

        Estructura oficial:
            BuscarAreaAct/
                {entidad}/{municipio}/{localidad}/{ageb}/{manzana}/
                {sector}/{subsector}/{rama}/{clase}/{nombre}/
                {registro_inicial}/{registro_final}/{id}/{token}

        Para no filtrar:
            localidad = 0
            ageb = 0
            manzana = 0
            sector = 0
            subsector = 0
            rama = 0
            clase = 0
            nombre = 0
            id = 0

        Ejemplo Xicohtzinco:
            entity_code = "29"
            municipality_code = "042"
        """
        entity = self._normalize_entity_code(entity_code)
        municipality = self._normalize_municipality_code(municipality_code)

        safe_locality = self._clean_code(locality, default="0")
        safe_ageb = self._clean_code(ageb, default="0")
        safe_block = self._clean_code(block, default="0")
        safe_sector = self._clean_code(sector, default="0")
        safe_subsector = self._clean_code(subsector, default="0")
        safe_branch = self._clean_code(branch, default="0")
        safe_class = self._clean_code(class_code, default="0")
        safe_term = quote((term or "0").strip() or "0", safe="")
        safe_id = self._clean_code(establishment_id, default="0")

        start, end = self._normalize_range(start=start, limit=limit)

        url = (
            f"{self.BASE_DENUE}/BuscarAreaAct/"
            f"{entity}/"
            f"{municipality}/"
            f"{safe_locality}/"
            f"{safe_ageb}/"
            f"{safe_block}/"
            f"{safe_sector}/"
            f"{safe_subsector}/"
            f"{safe_branch}/"
            f"{safe_class}/"
            f"{safe_term}/"
            f"{start}/"
            f"{end}/"
            f"{safe_id}/"
            f"{self._token}"
        )

        logger.info(
            "INEGI DENUE BuscarAreaAct request url=%s",
            self._redact_token(url),
        )

        data = await self._get_json(url)
        return self._as_records(data, context="INEGI DENUE BuscarAreaAct")

    async def search_denue_by_municipality_all(
        self,
        *,
        entity_code: str,
        municipality_code: str,
        term: str = "0",
        page_size: int = 100,
        max_records: int = 5000,
    ) -> list[dict[str, Any]]:
        """
        Descarga registros DENUE de un municipio en páginas.

        DENUE usa registro inicial y registro final, no page/page_size.
        Este helper permite obtener más de los primeros 100 registros.

        Parámetros:
            page_size:
                Número de registros por llamada.
            max_records:
                Límite defensivo para evitar llamadas excesivas.

        Detiene la descarga cuando:
            - Una página viene vacía.
            - Una página trae menos registros que page_size.
            - Se alcanza max_records.
        """
        if page_size <= 0:
            page_size = 100

        if page_size > 500:
            page_size = 500

        if max_records <= 0:
            max_records = page_size

        all_records: list[dict[str, Any]] = []
        start = 1

        while start <= max_records:
            remaining = max_records - len(all_records)

            if remaining <= 0:
                break

            current_limit = min(page_size, remaining)

            records = await self.search_denue_by_municipality(
                entity_code=entity_code,
                municipality_code=municipality_code,
                term=term,
                start=start,
                limit=current_limit,
            )

            if not records:
                break

            all_records.extend(records)

            if len(records) < current_limit:
                break

            start += current_limit

        return all_records

    # ─────────────────────────────────────────────────────────────────────
    # DENUE: Cuantificar
    # ─────────────────────────────────────────────────────────────────────

    async def quantify_denue(
        self,
        *,
        activity_code: str = "0",
        area_code: str = "0",
        stratum: str = "0",
    ) -> list[dict[str, Any]]:
        """
        Consulta conteos DENUE con el método Cuantificar.

        Estructura:
            Cuantificar/{actividad_economica}/{area_geografica}/{estrato}/{token}

        Ejemplo municipal:
            activity_code = "0"
            area_code = "29042"
            stratum = "0"
        """
        safe_activity = self._clean_code(activity_code, default="0")
        safe_area = self._clean_code(area_code, default="0")
        safe_stratum = self._clean_code(stratum, default="0")

        url = (
            f"{self.BASE_DENUE}/Cuantificar/"
            f"{safe_activity}/{safe_area}/{safe_stratum}/{self._token}"
        )

        logger.info(
            "INEGI DENUE Cuantificar request url=%s",
            self._redact_token(url),
        )

        data = await self._get_json(url)
        return self._as_records(data, context="INEGI DENUE Cuantificar")

    # ─────────────────────────────────────────────────────────────────────
    # Normalization helpers
    # ─────────────────────────────────────────────────────────────────────

    def _normalize_range(self, *, start: int, limit: int) -> tuple[int, int]:
        """
        DENUE espera registro inicial y registro final.

        Ejemplo:
            start=1, limit=100 -> 1,100
        """
        try:
            safe_start = int(start)
        except (TypeError, ValueError):
            safe_start = 1

        try:
            safe_limit = int(limit)
        except (TypeError, ValueError):
            safe_limit = 100

        if safe_start <= 0:
            safe_start = 1

        if safe_limit <= 0:
            safe_limit = 100

        end = safe_start + safe_limit - 1

        return safe_start, end

    def _normalize_entity_code(self, value: str | int) -> str:
        """
        Normaliza clave de entidad a dos dígitos.

        Ejemplo:
            29 -> "29"
            "29" -> "29"
            "029" -> "29"
        """
        raw = str(value or "").strip()

        if not raw:
            return "00"

        try:
            number = int(raw)
            return f"{number:02d}"
        except ValueError:
            return raw.zfill(2)

    def _normalize_municipality_code(self, value: str | int) -> str:
        """
        Normaliza clave municipal a tres dígitos.

        Acepta:
            "042" -> "042"
            42 -> "042"
            "29042" -> "042"
        """
        raw = str(value or "").strip()

        if not raw:
            return "0"

        if raw.isdigit() and len(raw) == 5:
            raw = raw[-3:]

        try:
            number = int(raw)
            return f"{number:03d}"
        except ValueError:
            return raw.zfill(3)

    def _clean_code(self, value: str | int | None, *, default: str = "0") -> str:
        raw = str(value or "").strip()
        return raw if raw else default