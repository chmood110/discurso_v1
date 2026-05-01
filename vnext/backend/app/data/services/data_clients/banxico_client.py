from __future__ import annotations

import os
from typing import Any

import httpx


class BanxicoClient:
    """
    Cliente mínimo para series del Sistema de Información Económica de Banxico.
    """

    BASE_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"

    def __init__(self, token: str | None = None, timeout: float = 20.0) -> None:
        self.token = token or os.getenv("BANXICO_TOKEN", "")
        self.timeout = timeout

        if not self.token:
            raise ValueError("BANXICO_TOKEN no está configurado")

    async def get_latest_observation(self, serie_id: str) -> dict[str, Any]:
        """
        Obtiene el dato más reciente de una serie Banxico.
        """
        url = f"{self.BASE_URL}/{serie_id}/datos/oportuno"

        headers = {
            "Bmx-Token": self.token,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_series_range(
        self,
        serie_id: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """
        Obtiene datos de una serie Banxico en rango de fechas.

        Fechas en formato:
            YYYY-MM-DD
        """
        url = f"{self.BASE_URL}/{serie_id}/datos/{start_date}/{end_date}"

        headers = {
            "Bmx-Token": self.token,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()