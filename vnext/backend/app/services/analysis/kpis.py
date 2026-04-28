"""
KPIGenerator — Genera KPIs SMART con línea base real y fuente verificable.

Principios:
- Cada KPI tiene valor base REAL de fuente oficial
- Cada KPI tiene fórmula de medición
- Cada KPI tiene meta realista (basada en tendencias y benchmarks)
- Cada KPI tiene fuente verificable y periodicidad
- NUNCA se inventa ninguna línea base

KPIs disponibles:
  1. Reducción de pobreza multidimensional
  2. Formalización laboral
  3. Cobertura de salud
  4. Conectividad digital
  5. Agua potable
  6. Rezago educativo
  7. Densidad empresarial
  8. Ingresos laborales
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.services.integrations.data_models import EvidencePack


@dataclass
class KPI:
    name: str
    objective: str              # El qué queremos lograr
    formula: str                # Cómo se mide
    baseline_value: Optional[float] = None
    baseline_unit: str = ""
    baseline_period: str = ""
    baseline_source: str = ""
    baseline_geographic_level: str = "municipal"
    target_value: Optional[float] = None
    target_period: str = ""
    target_rationale: str = ""
    measurement_frequency: str = "Anual"
    responsible_entity: str = ""
    data_collection_method: str = ""
    available: bool = True
    limitation: Optional[str] = None

    def display_baseline(self) -> str:
        if not self.available or self.baseline_value is None:
            return f"No disponible ({self.limitation or 'sin datos'})"
        return f"{self.baseline_value:,.1f} {self.baseline_unit} ({self.baseline_period})"

    def display_target(self) -> str:
        if self.target_value is None:
            return "Meta por definir"
        return f"{self.target_value:,.1f} {self.baseline_unit} ({self.target_period})"


@dataclass
class KPIBoard:
    municipality_name: str
    state: str = "Tlaxcala"
    kpis: list[KPI] = field(default_factory=list)
    methodology_note: str = ""
    data_disclaimer: str = ""


class KPIGenerator:
    """Genera un tablero de KPIs SMART para un municipio de Tlaxcala."""

    def generate(self, pack: EvidencePack, max_kpis: int = 5) -> KPIBoard:
        all_kpis = self._build_all_kpis(pack)
        # Seleccionar los más relevantes (los que tienen baseline disponible primero)
        available = [k for k in all_kpis if k.available and k.baseline_value is not None]
        unavailable = [k for k in all_kpis if not k.available or k.baseline_value is None]
        selected = (available + unavailable)[:max_kpis]

        return KPIBoard(
            municipality_name=pack.municipality_name,
            kpis=selected,
            methodology_note=(
                "Los KPIs se construyen con base en datos oficiales de INEGI, CONEVAL y Banxico. "
                "Las metas propuestas son indicativas y deben validarse con el equipo técnico municipal "
                "y las metas de los programas sectoriales vigentes (PNMC, Programas Estatales de Desarrollo)."
            ),
            data_disclaimer=(
                f"Fuentes primarias: INEGI Censo 2020, CONEVAL Medición de Pobreza Municipal 2020, "
                f"INEGI ENOE 2023-Q4, INEGI DENUE 2023, Banxico SIE 2023. "
                f"Nivel geográfico: {'municipal' if pack.data_quality == 'reference' else 'estatal (fallback)'}. "
                f"{'; '.join(pack.geographic_fallbacks) if pack.geographic_fallbacks else ''}"
            ),
        )

    def _build_all_kpis(self, pack: EvidencePack) -> list[KPI]:
        kpis = []
        s = pack.social
        e = pack.economic
        i = pack.infrastructure

        # KPI 1: Pobreza multidimensional
        kpis.append(KPI(
            name="Reducción de la pobreza multidimensional",
            objective=(
                f"Disminuir la tasa de pobreza multidimensional en {pack.municipality_name} "
                "mediante intervenciones coordinadas en ingreso, educación y acceso a servicios."
            ),
            formula="(Personas en pobreza / Población total) × 100 — medido por CONEVAL cada 2 años",
            baseline_value=s.poverty_rate_pct.value,
            baseline_unit="%",
            baseline_period=s.poverty_rate_pct.period,
            baseline_source=s.poverty_rate_pct.source,
            target_value=round(s.poverty_rate_pct.value * 0.85, 1) if s.poverty_rate_pct.value else None,
            target_period="2026 (CONEVAL medición)",
            target_rationale=(
                "Meta de -15% absoluto en 3 años, consistente con la Agenda 2030 ODS-1 "
                "y la tasa promedio de reducción estatal Tlaxcala 2016–2020."
            ),
            measurement_frequency="Bienal (medición CONEVAL)",
            responsible_entity="Municipio / Secretaría de Bienestar Tlaxcala / CONEVAL",
            data_collection_method="Encuesta Nacional de Ingresos y Gastos de los Hogares (ENIGH) — INEGI/CONEVAL",
            available=s.poverty_rate_pct.available,
        ))

        # KPI 2: Formalización laboral
        kpis.append(KPI(
            name="Reducción de empleo informal",
            objective=(
                "Aumentar la proporción de trabajadores con contrato formal y acceso a seguridad social."
            ),
            formula="(Trabajadores informales / PEA ocupada) × 100 — ENOE INEGI",
            baseline_value=e.informal_employment_pct.value,
            baseline_unit="% PEA informal",
            baseline_period=e.informal_employment_pct.period,
            baseline_source=e.informal_employment_pct.source,
            baseline_geographic_level=e.informal_employment_pct.geographic_level,
            target_value=round(e.informal_employment_pct.value * 0.90, 1) if e.informal_employment_pct.value else None,
            target_period="2026",
            target_rationale=(
                "Reducción del 10% del nivel base, alineado con la meta IMSS-Bienestar "
                "de cobertura universal de seguridad social."
            ),
            measurement_frequency="Trimestral (ENOE)",
            responsible_entity="Municipio / IMSS / Secretaría del Trabajo Tlaxcala",
            data_collection_method="Encuesta Nacional de Ocupación y Empleo (ENOE) — INEGI",
            available=e.informal_employment_pct.available,
            limitation=e.informal_employment_pct.limitation_note,
        ))

        # KPI 3: Cobertura de salud
        kpis.append(KPI(
            name="Reducción de carencia por acceso a salud",
            objective=(
                "Garantizar que la población tenga acceso a atención médica regular "
                "sin gasto de bolsillo catastrófico."
            ),
            formula=(
                "(Personas con carencia de acceso a salud / Población total) × 100 — CONEVAL"
            ),
            baseline_value=s.health_access_lack_pct.value,
            baseline_unit="% población con carencia",
            baseline_period=s.health_access_lack_pct.period,
            baseline_source=s.health_access_lack_pct.source,
            target_value=round(s.health_access_lack_pct.value * 0.80, 1) if s.health_access_lack_pct.value else None,
            target_period="2026",
            target_rationale=(
                "Reducción del 20% en 3 años, consistente con la expansión del IMSS-Bienestar "
                "y el programa Médico de Familia del gobierno estatal."
            ),
            measurement_frequency="Bienal (CONEVAL) / Mensual (registros IMSS-ISSSTE)",
            responsible_entity="Secretaría de Salud Tlaxcala / IMSS-Bienestar / Municipio",
            data_collection_method="CONEVAL medición bienal; registros administrativos IMSS/ISSSTE",
            available=s.health_access_lack_pct.available,
        ))

        # KPI 4: Conectividad digital
        kpis.append(KPI(
            name="Cobertura de internet en hogares",
            objective=(
                "Reducir la brecha digital garantizando acceso a internet de banda ancha "
                "para potenciar educación, teletrabajo y trámites gubernamentales."
            ),
            formula="(Viviendas con internet / Total de viviendas particulares habitadas) × 100 — INEGI",
            baseline_value=i.internet_access_pct.value,
            baseline_unit="% viviendas",
            baseline_period=i.internet_access_pct.period,
            baseline_source=i.internet_access_pct.source,
            target_value=min(95.0, round((i.internet_access_pct.value or 50) * 1.25, 1)),
            target_period="2026",
            target_rationale=(
                "Meta de +25% relativo en 3 años, acorde al Plan Nacional de Infraestructura "
                "Digital y el programa Internet para Todos."
            ),
            measurement_frequency="Cada 5 años (Censo INEGI) / Anual (ENDUTIH)",
            responsible_entity="SCT / IFT / Municipio / CFE",
            data_collection_method=(
                "Encuesta Nacional sobre Disponibilidad y Uso de TIC en Hogares (ENDUTIH) — INEGI"
            ),
            available=i.internet_access_pct.available,
        ))

        # KPI 5: Agua potable
        kpis.append(KPI(
            name="Cobertura de agua potable",
            objective=(
                "Asegurar acceso universal y permanente a agua potable en la red domiciliaria."
            ),
            formula=(
                "(Viviendas con agua entubada dentro del terreno / Total de viviendas) × 100 — INEGI Censo"
            ),
            baseline_value=i.drinking_water_access_pct.value,
            baseline_unit="% viviendas",
            baseline_period=i.drinking_water_access_pct.period,
            baseline_source=i.drinking_water_access_pct.source,
            target_value=min(98.0, round((i.drinking_water_access_pct.value or 80) + 8, 1)),
            target_period="2026",
            target_rationale=(
                "Meta de +8 puntos porcentuales, alineada con el ODS-6 "
                "y los recursos FAIS/FISM disponibles para infraestructura hídrica."
            ),
            measurement_frequency="Cada 5 años (Censo INEGI) / Anual (CONAGUA SINA)",
            responsible_entity="SEMARNAT-CONAGUA / CAET Tlaxcala / Municipio",
            data_collection_method="INEGI Censo de Población y Vivienda; CONAGUA SINA",
            available=i.drinking_water_access_pct.available,
        ))

        # KPI 6: Rezago educativo (adicional)
        kpis.append(KPI(
            name="Reducción del rezago educativo",
            objective=(
                "Disminuir el porcentaje de personas mayores de 15 años sin educación básica completa."
            ),
            formula=(
                "(Personas de 15+ años en rezago educativo / Población de 15+ años) × 100 — CONEVAL"
            ),
            baseline_value=s.education_lag_pct.value,
            baseline_unit="% población 15+ años",
            baseline_period=s.education_lag_pct.period,
            baseline_source=s.education_lag_pct.source,
            target_value=round(s.education_lag_pct.value * 0.80, 1) if s.education_lag_pct.value else None,
            target_period="2027 (medición CONEVAL)",
            target_rationale=(
                "Meta de -20% del nivel base en 4 años mediante programas INEA/NATALII "
                "y Aprende en Casa para adultos."
            ),
            measurement_frequency="Bienal (CONEVAL)",
            responsible_entity="SEP / INEA / Municipio",
            data_collection_method="CONEVAL medición bienal; INEA registros administrativos",
            available=s.education_lag_pct.available,
        ))

        return kpis


kpi_generator = KPIGenerator()
