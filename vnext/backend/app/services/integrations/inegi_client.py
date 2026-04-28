"""
Cliente INEGI — BIE (Banco de Información Económica) + DENUE.

Diseño tolerante a fallos:
- Intenta la API real con las credenciales configuradas
- En caso de error (conexión, auth, timeout), devuelve None
- El caller (EvidenceAssembler) usa el dato de referencia estático como fallback
- NUNCA inventa datos: si no hay dato disponible, informa explícitamente

APIs documentadas:
  BIE:   https://www.inegi.org.mx/servicios/api_biinegi.html
  DENUE: https://www.inegi.org.mx/servicios/api_denue.html
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BIE_BASE = "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml"
_DENUE_BASE = "https://www.inegi.org.mx/app/api/denue/v1/consulta"
_TIMEOUT = 12.0

# Claves de indicadores BIE relevantes
# Fuente: https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml
_INDICADORES = {
    "poblacion_total": "1002000001",   # Población total
    "pea": "1005000002",               # Población Económicamente Activa
    "desocupacion": "444612",           # Tasa de desocupación
    "inflacion_gral": "910406",         # INPC general
}

# Clave geográfica para Tlaxcala en BIE
_TLAXCALA_GEO = "0700"


class InegiClient:
    """
    Cliente para INEGI BIE y DENUE.
    Requiere INEGI_API_TOKEN en variables de entorno para llamadas reales.
    Tolerante a fallos — devuelve None si la API no responde o no tiene dato.
    """

    def __init__(self):
        self._token = getattr(settings, "INEGI_API_TOKEN", "")
        self._timeout = httpx.Timeout(_TIMEOUT)

    def _is_configured(self) -> bool:
        return bool(self._token)

    async def fetch_population(self, municipality_cvegeo: Optional[str] = None) -> Optional[float]:
        """
        Obtiene población total de Tlaxcala o municipio específico.
        municipality_cvegeo: clave geoestadística INEGI del municipio (5 dígitos)
        """
        if not self._is_configured():
            logger.debug("INEGI_API_TOKEN no configurado; usando datos de referencia.")
            return None

        geo = municipality_cvegeo or _TLAXCALA_GEO
        url = (
            f"{_BIE_BASE}/INDICATOR/{_INDICADORES['poblacion_total']}"
            f"/es/{geo}/false/BIE/2.0/{self._token}"
        )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    # Extraer el valor más reciente de la serie
                    series = data.get("Series", [])
                    if series:
                        obs = series[0].get("OBSERVATIONS", [])
                        if obs:
                            return float(obs[-1].get("OBS_VALUE", 0))
        except Exception as exc:
            logger.warning("INEGI BIE error al obtener población: %s", exc)
        return None

    async def fetch_unemployment_rate(self) -> Optional[float]:
        """Tasa de desocupación estatal (ENOE). Sin desagregación municipal en BIE."""
        if not self._is_configured():
            return None
        url = (
            f"{_BIE_BASE}/INDICATOR/{_INDICADORES['desocupacion']}"
            f"/es/{_TLAXCALA_GEO}/false/BIE/2.0/{self._token}"
        )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    series = data.get("Series", [])
                    if series:
                        obs = series[0].get("OBSERVATIONS", [])
                        if obs:
                            return float(obs[-1].get("OBS_VALUE", 0))
        except Exception as exc:
            logger.warning("INEGI BIE error al obtener desocupación: %s", exc)
        return None

    async def fetch_denue_counts(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        activity_code: str = "0",
    ) -> Optional[dict]:
        """
        Cuenta unidades económicas en radio desde coordenadas.
        activity_code: código SCIAN (0 = todos, 62 = salud, 61 = educación, 46 = comercio)
        Retorna dict con total y desglose, o None si falla.
        """
        if not self._is_configured():
            return None
        url = (
            f"{_DENUE_BASE}/BuscarAreaActEstr/{lat}/{lon}/{radius_meters}"
            f"/{activity_code}/0/0/0/0/100/{self._token}"
        )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    units = resp.json()
                    if isinstance(units, list):
                        return {"total": len(units), "units": units[:20]}
        except Exception as exc:
            logger.warning("INEGI DENUE error: %s", exc)
        return None


inegi_client = InegiClient()
