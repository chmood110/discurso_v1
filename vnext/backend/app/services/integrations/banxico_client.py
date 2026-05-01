from __future__ import annotations

import os
from typing import Any

import httpx


class BanxicoClient:
    """
    Cliente para consultar series del Sistema de Información Económica de Banxico.
    """

    BASE_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"

    def __init__(self, token: str | None = None, timeout: float = 20.0) -> None:
        self._token = token or os.getenv("BANXICO_TOKEN", "")
        self.timeout = timeout

        if not self._token:
            raise ValueError("BANXICO_TOKEN no está configurado")

    @property
    def token(self) -> str:
        return self._token

    async def get_latest_observation(self, serie_id: str) -> dict[str, Any]:
        """
        Obtiene el dato oportuno o más reciente de una serie Banxico.
        """
        url = f"{self.BASE_URL}/{serie_id}/datos/oportuno"

        headers = {
            "Bmx-Token": self._token,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"Banxico respondió con error HTTP {exc.response.status_code}: "
                    f"{exc.response.text[:500]}"
                ) from exc
            except httpx.RequestError as exc:
                raise RuntimeError(
                    f"No se pudo conectar con Banxico: {exc}"
                ) from exc

    async def get_series_range(
        self,
        serie_id: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """
        Obtiene datos de una serie Banxico en un rango de fechas.

        Formato esperado:
            YYYY-MM-DD
        """
        url = f"{self.BASE_URL}/{serie_id}/datos/{start_date}/{end_date}"

        headers = {
            "Bmx-Token": self._token,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"Banxico respondió con error HTTP {exc.response.status_code}: "
                    f"{exc.response.text[:500]}"
                ) from exc
            except httpx.RequestError as exc:
                raise RuntimeError(
                    f"No se pudo conectar con Banxico: {exc}"
                ) from exc

    def normalize_latest_observation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Normaliza la respuesta de Banxico para obtener un dato limpio.

        Entrada esperada:
            {
                "bmx": {
                    "series": [
                        {
                            "idSerie": "...",
                            "titulo": "...",
                            "datos": [
                                {"fecha": "...", "dato": "..."}
                            ]
                        }
                    ]
                }
            }

        Salida:
            {
                "series_id": "...",
                "title": "...",
                "value": 6.77,
                "date": "29/04/2026",
                "source": "Banxico SIE"
            }
        """
        try:
            series = payload.get("bmx", {}).get("series", [])
            if not series:
                raise ValueError("La respuesta no contiene series")

            serie = series[0]
            datos = serie.get("datos", [])
            if not datos:
                raise ValueError("La serie no contiene datos")

            latest = datos[0]
            raw_value = str(latest.get("dato", "")).replace(",", "").strip()

            if not raw_value:
                raise ValueError("El dato viene vacío")

            return {
                "series_id": serie.get("idSerie"),
                "title": serie.get("titulo"),
                "value": float(raw_value),
                "date": latest.get("fecha"),
                "source": "Banxico SIE",
            }

        except Exception as exc:
            raise ValueError(
                f"No se pudo normalizar la respuesta de Banxico: {exc}"
            ) from exc