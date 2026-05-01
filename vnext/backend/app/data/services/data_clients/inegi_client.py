from __future__ import annotations

import os
from typing import Any

import httpx


class InegiClient:
    """
    Cliente mínimo para APIs de INEGI.

    Este cliente no decide qué hacer con los datos.
    Solo consulta APIs oficiales y devuelve JSON normalizado de respuesta.
    """

    BASE_INDICADORES = "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR"
    BASE_DENUE = "https://www.inegi.org.mx/app/api/denue/v1/consulta"

    def __init__(self, token: str | None = None, timeout: float = 20.0) -> None:
        self.token = token or os.getenv("INEGI_API_TOKEN", "")
        self.timeout = timeout

        if not self.token:
            raise ValueError("INEGI_API_TOKEN no está configurado")

    async def get_indicator(
        self,
        indicator_id: str,
        *,
        geography: str,
        language: str = "es",
        recent: bool = True,
    ) -> dict[str, Any]:
        """
        Consulta un indicador del Banco de Indicadores de INEGI.

        geography:
            Para entidad/municipio depende del indicador y del constructor de consultas.
            La recomendación es guardar estos códigos en un diccionario propio.
        """
        recent_flag = "true" if recent else "false"

        url = (
            f"{self.BASE_INDICADORES}/{indicator_id}/{language}/{geography}/"
            f"{recent_flag}/BIE/2.0/{self.token}"
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def search_denue_by_area(
        self,
        *,
        term: str,
        lat: float,
        lon: float,
        radius_m: int = 5000,
    ) -> dict[str, Any]:
        """
        Consulta establecimientos DENUE alrededor de una coordenada.

        Útil para salud, escuelas, negocios, servicios, etc.
        """
        url = f"{self.BASE_DENUE}/Buscar/{term}/{lat},{lon}/{radius_m}/{self.token}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()