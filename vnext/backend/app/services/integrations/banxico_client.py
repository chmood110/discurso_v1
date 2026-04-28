"""
Cliente Banxico SIE (Sistema de Información Económica).

API REST: https://www.banxico.org.mx/SieAPIRest/service/v1/
Requiere BMX-TOKEN en variables de entorno.

Series relevantes:
  SF43718 — Tipo de cambio (FIX) USD/MXN
  SF61745 — Tasa de Fondeo Bancario (tasa objetivo Banxico)
  SF43773 — Tasa de interés de fondeo interbancario
  SG20 — INPC general (inflación)
  SE27820 — Remesas familiares totales (millones USD)
  SE57408 — Remesas por entidad federativa: Tlaxcala
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BANXICO_BASE = "https://www.banxico.org.mx/SieAPIRest/service/v1"
_TIMEOUT = 12.0


class BanxicoClient:
    """
    Cliente para Banxico SIE REST.
    Requiere BANXICO_TOKEN en variables de entorno.
    Tolerante a fallos.
    """

    def __init__(self):
        self._token = getattr(settings, "BANXICO_TOKEN", "")
        self._timeout = httpx.Timeout(_TIMEOUT)

    def _is_configured(self) -> bool:
        return bool(self._token)

    def _headers(self) -> dict:
        return {"Bmx-Token": self._token}

    async def _fetch_series_latest(self, series_id: str) -> Optional[float]:
        """Obtiene el dato más reciente de una serie del SIE."""
        if not self._is_configured():
            logger.debug("BANXICO_TOKEN no configurado; usando datos de referencia.")
            return None
        url = f"{_BANXICO_BASE}/series/{series_id}/datos/oportuno"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    data = resp.json()
                    series_list = data.get("bmx", {}).get("series", [])
                    if series_list:
                        datos = series_list[0].get("datos", [])
                        if datos:
                            val_str = datos[-1].get("dato", "").replace(",", "")
                            return float(val_str)
        except Exception as exc:
            logger.warning("Banxico SIE error para serie %s: %s", series_id, exc)
        return None

    async def fetch_exchange_rate(self) -> Optional[float]:
        """Tipo de cambio FIX USD/MXN (SF43718)."""
        return await self._fetch_series_latest("SF43718")

    async def fetch_reference_rate(self) -> Optional[float]:
        """Tasa objetivo Banxico (SF61745)."""
        return await self._fetch_series_latest("SF61745")

    async def fetch_inflation(self) -> Optional[float]:
        """INPC variación anual (SF46405)."""
        return await self._fetch_series_latest("SF46405")

    async def fetch_remittances_national(self) -> Optional[float]:
        """Remesas familiares totales en millones de USD (SE27820)."""
        return await self._fetch_series_latest("SE27820")

    async def fetch_remittances_tlaxcala(self) -> Optional[float]:
        """
        Remesas por entidad federativa — Tlaxcala.
        Banxico publica esta serie desde 2017 desagregada por estado.
        El valor está en millones de pesos.
        """
        return await self._fetch_series_latest("SE57408")


banxico_client = BanxicoClient()
