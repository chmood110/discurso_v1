"""
DiagnosisGenerator — Genera diagnósticos estructurados basados en evidencia real.

Produce:
  - Perfil sociodemográfico
  - Motor económico
  - Brechas de infraestructura
  - Necesidades críticas con correlaciones multi-fuente
  - Oportunidades de política pública

REGLA: Todos los datos en el diagnóstico deben tener fuente verificable.
Si no hay dato, se declara explícitamente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.services.integrations.data_models import EvidencePack


@dataclass
class CriticalNeed:
    title: str
    description: str
    severity: str               # "alta" | "media" | "baja"
    data_evidence: list[str]    # Datos que sustentan esta necesidad (con fuente)
    cross_sources: list[str]    # Fuentes cruzadas
    policy_lever: str           # Tipo de intervención sugerida
    affected_population_pct: Optional[float] = None


@dataclass
class DiagnosisReport:
    municipality_name: str
    state: str = "Tlaxcala"

    # Sección 1: Perfil sociodemográfico
    demographic_profile: dict = field(default_factory=dict)

    # Sección 2: Motor económico
    economic_engine: dict = field(default_factory=dict)

    # Sección 3: Infraestructura
    infrastructure_gaps: dict = field(default_factory=dict)

    # Sección 4: Necesidades críticas
    critical_needs: list[CriticalNeed] = field(default_factory=list)

    # Sección 5: Oportunidades
    opportunities: list[str] = field(default_factory=list)

    # Resumen ejecutivo
    executive_summary: str = ""

    # Metadatos
    data_sources: list[str] = field(default_factory=list)
    data_quality: str = "reference"
    geographic_fallbacks: list[str] = field(default_factory=list)


class DiagnosisGenerator:
    """Genera un DiagnosisReport completo a partir de un EvidencePack."""

    def generate(self, pack: EvidencePack) -> DiagnosisReport:
        report = DiagnosisReport(
            municipality_name=pack.municipality_name,
            data_sources=pack.sources_used,
            data_quality=pack.data_quality,
            geographic_fallbacks=pack.geographic_fallbacks,
        )

        report.demographic_profile = self._build_demographic_profile(pack)
        report.economic_engine = self._build_economic_engine(pack)
        report.infrastructure_gaps = self._build_infrastructure_gaps(pack)
        report.critical_needs = self._identify_critical_needs(pack)
        report.opportunities = self._identify_opportunities(pack)
        report.executive_summary = self._build_executive_summary(pack, report)

        return report

    # ── Sección 1: Perfil sociodemográfico ──────────────────────────────────

    def _build_demographic_profile(self, pack: EvidencePack) -> dict:
        s = pack.social
        pop = s.population_total
        youth = s.pct_youth_15_29
        elderly = s.pct_elderly_60plus
        indigenous = s.pct_indigenous
        poverty = s.poverty_rate_pct
        extreme = s.extreme_poverty_rate_pct

        # Clasificación de municipio por pobreza
        poverty_level = "bajo"
        if poverty.value and poverty.value >= 50:
            poverty_level = "muy alto"
        elif poverty.value and poverty.value >= 35:
            poverty_level = "alto"
        elif poverty.value and poverty.value >= 20:
            poverty_level = "moderado"

        return {
            "population": {
                "total": pop.display(),
                "source": pop.source,
                "period": pop.period,
            },
            "density": {
                "value": pack.social.population_density_km2.display(),
                "source": pack.social.population_density_km2.source,
            },
            "age_structure": {
                "youth_15_29": youth.display(),
                "adults_30_59": pack.social.pct_adults_30_59.display(),
                "elderly_60plus": elderly.display(),
                "interpretation": self._interpret_age_structure(youth.value, elderly.value),
            },
            "social_composition": {
                "indigenous_pct": indigenous.display(),
                "female_pct": pack.social.pct_female.display(),
                "households": pack.social.households_total.display(),
            },
            "poverty_profile": {
                "poverty_rate": poverty.display(),
                "extreme_poverty_rate": extreme.display(),
                "social_vulnerability": pack.social.social_vulnerability_pct.display(),
                "welfare_income_gap": pack.social.income_below_welfare_pct.display(),
                "level_classification": poverty_level,
                "source": poverty.source,
            },
            "social_deprivations": {
                "education_lag": pack.social.education_lag_pct.display(),
                "health_access_lack": pack.social.health_access_lack_pct.display(),
                "social_security_lack": pack.social.social_security_lack_pct.display(),
                "housing_quality_lack": pack.social.housing_quality_lack_pct.display(),
                "basic_services_lack": pack.social.basic_services_lack_pct.display(),
                "food_insecurity": pack.social.food_insecurity_pct.display(),
                "worst_deprivation": self._worst_deprivation(pack),
            },
        }

    def _interpret_age_structure(
        self, youth_pct: Optional[float], elderly_pct: Optional[float]
    ) -> str:
        if youth_pct is None:
            return "Estructura etaria no disponible."
        if youth_pct >= 25:
            base = "Población predominantemente joven con alta presión sobre empleo y educación."
        elif youth_pct >= 20:
            base = "Estructura etaria equilibrada con bono demográfico activo."
        else:
            base = "Tendencia al envejecimiento poblacional."
        if elderly_pct and elderly_pct >= 15:
            base += " Alta proporción de adultos mayores demanda servicios de salud y pensiones."
        return base

    def _worst_deprivation(self, pack: EvidencePack) -> str:
        s = pack.social
        deprivations = {
            "Carencia por seguridad social": s.social_security_lack_pct.value,
            "Rezago educativo": s.education_lag_pct.value,
            "Carencia por acceso a salud": s.health_access_lack_pct.value,
            "Carencia por servicios básicos en vivienda": s.basic_services_lack_pct.value,
            "Inseguridad alimentaria": s.food_insecurity_pct.value,
        }
        valid = {k: v for k, v in deprivations.items() if v is not None}
        if not valid:
            return "Sin datos suficientes."
        return max(valid, key=lambda k: valid[k])

    # ── Sección 2: Motor económico ────────────────────────────────────────────

    def _build_economic_engine(self, pack: EvidencePack) -> dict:
        e = pack.economic
        informal = e.informal_employment_pct
        income = e.avg_income_mxn
        remesas = e.remittances_mdp_annual

        economic_vulnerability = "baja"
        if informal.value and informal.value >= 60:
            economic_vulnerability = "muy alta"
        elif informal.value and informal.value >= 45:
            economic_vulnerability = "alta"
        elif informal.value and informal.value >= 30:
            economic_vulnerability = "moderada"

        return {
            "employment": {
                "unemployment_rate": e.unemployment_rate_pct.display(),
                "informal_employment": informal.display(),
                "labor_participation": e.labor_participation_pct.display(),
                "avg_monthly_income": income.display(),
                "economic_vulnerability": economic_vulnerability,
                "source": e.unemployment_rate_pct.source,
                "note": e.unemployment_rate_pct.limitation_note,
            },
            "business_fabric": {
                "total_units": e.economic_units_total.display(),
                "density_per_1000": e.economic_units_per_1000.display(),
                "health_units": e.health_units.display(),
                "education_units": e.education_units.display(),
                "commercial_units": e.commercial_units.display(),
                "main_sectors": e.main_sectors,
                "source": e.economic_units_total.source,
            },
            "remittances": {
                "annual_mdp": remesas.display(),
                "pct_state_gdp": e.remittances_pct_gdp_state.display(),
                "significance": self._interpret_remittances(pack),
                "source": remesas.source,
                "note": remesas.limitation_note,
            },
            "macro_context": {
                "inflation": e.inflation_rate_pct.display(),
                "exchange_rate": e.exchange_rate_usd_mxn.display(),
                "banxico_rate": e.banxico_reference_rate_pct.display(),
                "source": "Banxico SIE",
                "interpretation": self._interpret_macro(pack),
            },
        }

    def _interpret_remittances(self, pack: EvidencePack) -> str:
        """Contextualiza el peso de remesas para este municipio."""
        name = pack.municipality_name
        is_high_migration = any(
            sec.lower() in " ".join(pack.economic.main_sectors).lower()
            for sec in ["migración", "migracion"]
        )
        base = (
            f"Las remesas a Tlaxcala suman {pack.economic.remittances_mdp_annual.display()} anuales, "
            "representando un ingreso complementario relevante para muchos hogares."
        )
        if is_high_migration:
            base += f" {name} es municipio de alta emigración, lo que hace de las remesas "
            base += "un pilar significativo del ingreso familiar local."
        return base

    def _interpret_macro(self, pack: EvidencePack) -> str:
        rate = pack.economic.banxico_reference_rate_pct.value
        inflation = pack.economic.inflation_rate_pct.value
        if rate and rate >= 10:
            return (
                f"Con tasa Banxico de {rate:.2f}%, el crédito es caro. "
                "Esto frena la inversión MIPYME y encarece la deuda pública. "
                "Para municipios con alta pobreza, esto reduce el acceso a financiamiento productivo."
            )
        return "Contexto macroeconómico de referencia disponible via Banxico."

    # ── Sección 3: Infraestructura ────────────────────────────────────────────

    def _build_infrastructure_gaps(self, pack: EvidencePack) -> dict:
        i = pack.infrastructure
        gaps = []
        strengths = []

        water = i.drinking_water_access_pct.value
        internet = i.internet_access_pct.value
        drainage = i.drainage_access_pct.value
        roads = i.pct_localities_paved_road.value
        hospital_time = i.minutes_to_nearest_hospital.value

        if water and water < 85:
            gaps.append(f"Acceso a agua potable ({water:.0f}%) por debajo del umbral recomendado (85%).")
        elif water:
            strengths.append(f"Cobertura de agua potable ({water:.0f}%) satisfactoria.")

        if internet and internet < 60:
            gaps.append(f"Brecha digital significativa: sólo {internet:.0f}% de hogares con internet.")
        elif internet:
            strengths.append(f"Conectividad digital ({internet:.0f}%) relativamente avanzada.")

        if drainage and drainage < 80:
            gaps.append(f"Cobertura de drenaje ({drainage:.0f}%) insuficiente; riesgo sanitario.")

        if roads and roads < 60:
            gaps.append(
                f"Sólo {roads:.0f}% de localidades con camino pavimentado. "
                "Aislamiento que encarece producción y dificulta acceso a servicios."
            )

        if hospital_time and hospital_time > 30:
            gaps.append(
                f"Tiempo al hospital más cercano estimado en {hospital_time:.0f} minutos. "
                "Déficit de atención médica de urgencias."
            )

        schooling = i.avg_schooling_years.value
        if schooling and schooling < 9:
            gaps.append(
                f"Promedio de escolaridad de {schooling:.1f} años, "
                "inferior a la media nacional (9.7 años, Censo INEGI 2020)."
            )

        return {
            "gaps": gaps,
            "strengths": strengths,
            "services_coverage": {
                "drinking_water": i.drinking_water_access_pct.display(),
                "electricity": i.electricity_access_pct.display(),
                "drainage": i.drainage_access_pct.display(),
                "internet": i.internet_access_pct.display(),
                "paved_floor": i.paved_floor_pct.display(),
                "paved_roads_localities": i.pct_localities_paved_road.display(),
            },
            "accessibility": {
                "hospital_minutes": i.minutes_to_nearest_hospital.display(),
                "capital_minutes": i.minutes_to_state_capital.display(),
            },
            "education": {
                "literacy": i.literacy_rate_pct.display(),
                "avg_schooling_years": i.avg_schooling_years.display(),
                "no_schooling": i.no_schooling_pct.display(),
            },
            "source": "INEGI Censo 2020",
        }

    # ── Sección 4: Necesidades críticas ──────────────────────────────────────

    def _identify_critical_needs(self, pack: EvidencePack) -> list[CriticalNeed]:
        needs: list[CriticalNeed] = []
        s = pack.social
        e = pack.economic
        i = pack.infrastructure

        # Necesidad 1: Pobreza y bienestar económico
        poverty_val = s.poverty_rate_pct.value
        if poverty_val and poverty_val >= 20:
            severity = "alta" if poverty_val >= 40 else "media"
            needs.append(CriticalNeed(
                title="Reducción de pobreza multidimensional",
                description=(
                    f"El {poverty_val:.1f}% de la población vive en pobreza (CONEVAL 2020), "
                    f"con {s.extreme_poverty_rate_pct.value:.1f}% en pobreza extrema. "
                    f"El {s.income_below_welfare_pct.value:.1f}% no cubre la línea de bienestar económico."
                ) if s.extreme_poverty_rate_pct.value and s.income_below_welfare_pct.value else
                f"El {poverty_val:.1f}% de la población vive en pobreza (CONEVAL 2020).",
                severity=severity,
                data_evidence=[
                    f"Tasa de pobreza: {s.poverty_rate_pct.display()} ({s.poverty_rate_pct.source})",
                    f"Pobreza extrema: {s.extreme_poverty_rate_pct.display()} ({s.extreme_poverty_rate_pct.source})",
                    f"Ingreso inferior a línea de bienestar: {s.income_below_welfare_pct.display()}",
                    f"Ingreso promedio mensual: {e.avg_income_mxn.display()} ({e.avg_income_mxn.source})",
                ],
                cross_sources=["CONEVAL 2020", "INEGI ENIGH 2022"],
                policy_lever="Programas de transferencias condicionadas, fomento al empleo formal, acceso a seguridad social.",
                affected_population_pct=poverty_val,
            ))

        # Necesidad 2: Seguridad social y empleo informal
        informal_val = e.informal_employment_pct.value
        ss_lack = s.social_security_lack_pct.value
        if (informal_val and informal_val >= 35) or (ss_lack and ss_lack >= 40):
            needs.append(CriticalNeed(
                title="Formalización del empleo y acceso a seguridad social",
                description=(
                    f"El {informal_val:.0f}% del empleo es informal "
                    f"y el {ss_lack:.0f}% de la población carece de seguridad social (CONEVAL). "
                    "Esto deja a las familias sin protección ante enfermedad, desempleo o vejez."
                ) if informal_val and ss_lack else
                "Alta informalidad laboral limita la protección social.",
                severity="alta",
                data_evidence=[
                    f"Empleo informal: {e.informal_employment_pct.display()} ({e.informal_employment_pct.source})",
                    f"Carencia por seguridad social: {s.social_security_lack_pct.display()} ({s.social_security_lack_pct.source})",
                    f"Ingreso promedio mensual: {e.avg_income_mxn.display()}",
                ],
                cross_sources=["CONEVAL 2020", "INEGI ENOE 2023", "INEGI DENUE 2023"],
                policy_lever="Incentivos a la formalización, programas IMSS-Bienestar, apoyo a MIPYMES.",
                affected_population_pct=ss_lack,
            ))

        # Necesidad 3: Salud y acceso a servicios médicos
        health_lack = s.health_access_lack_pct.value
        hospital_time = i.minutes_to_nearest_hospital.value
        if (health_lack and health_lack >= 20) or (hospital_time and hospital_time > 30):
            needs.append(CriticalNeed(
                title="Acceso a servicios de salud",
                description=(
                    f"El {health_lack:.0f}% de la población carece de acceso efectivo a servicios de salud "
                    f"y el hospital más cercano está a ~{hospital_time:.0f} minutos (estimación DENUE/ruteo). "
                    f"El municipio cuenta con {e.health_units.display()} establecimientos de salud."
                ) if health_lack and hospital_time else
                "Brecha en acceso a servicios de salud.",
                severity="alta" if health_lack and health_lack >= 30 else "media",
                data_evidence=[
                    f"Carencia por acceso a salud: {s.health_access_lack_pct.display()} ({s.health_access_lack_pct.source})",
                    f"Establecimientos de salud (DENUE SCIAN 62): {e.health_units.display()}",
                    f"Tiempo estimado al hospital: {i.minutes_to_nearest_hospital.display()}",
                ],
                cross_sources=["CONEVAL 2020", "INEGI DENUE 2023", "INEGI ruteo"],
                policy_lever="Unidades médicas móviles, telemedicina, fortalecimiento de clínicas del IMSS-Bienestar.",
                affected_population_pct=health_lack,
            ))

        # Necesidad 4: Agua e infraestructura básica
        water = i.drinking_water_access_pct.value
        services_lack = s.basic_services_lack_pct.value
        if (water and water < 85) or (services_lack and services_lack >= 20):
            needs.append(CriticalNeed(
                title="Agua potable e infraestructura básica",
                description=(
                    f"El {100 - water:.0f}% de los hogares no tiene acceso confiable a agua potable "
                    f"y el {services_lack:.0f}% carece de servicios básicos adecuados en vivienda (CONEVAL)."
                ) if water and services_lack else
                "Déficit en infraestructura básica de la vivienda.",
                severity="alta" if (water and water < 75) else "media",
                data_evidence=[
                    f"Acceso a agua potable: {i.drinking_water_access_pct.display()} ({i.drinking_water_access_pct.source})",
                    f"Carencia por servicios básicos vivienda: {s.basic_services_lack_pct.display()}",
                    f"Acceso a drenaje: {i.drainage_access_pct.display()}",
                ],
                cross_sources=["INEGI Censo 2020", "CONEVAL 2020"],
                policy_lever="Inversión en red hídrica, programa de drenaje sanitario, FISM.",
                affected_population_pct=services_lack,
            ))

        # Necesidad 5: Rezago educativo
        edu_lag = s.education_lag_pct.value
        schooling = i.avg_schooling_years.value
        if (edu_lag and edu_lag >= 20) or (schooling and schooling < 8.5):
            needs.append(CriticalNeed(
                title="Rezago educativo y capital humano",
                description=(
                    f"El {edu_lag:.0f}% de la población presenta rezago educativo (CONEVAL), "
                    f"con promedio de {schooling:.1f} años de escolaridad, "
                    "limitando la productividad y la inserción laboral formal."
                ) if edu_lag and schooling else
                "Rezago educativo significativo.",
                severity="alta" if (edu_lag and edu_lag >= 30) else "media",
                data_evidence=[
                    f"Rezago educativo: {s.education_lag_pct.display()} ({s.education_lag_pct.source})",
                    f"Años promedio de escolaridad: {i.avg_schooling_years.display()} ({i.avg_schooling_years.source})",
                    f"Sin escolaridad: {i.no_schooling_pct.display()}",
                    f"Planteles educativos (DENUE SCIAN 61): {e.education_units.display()}",
                ],
                cross_sources=["CONEVAL 2020", "INEGI Censo 2020", "INEGI DENUE 2023"],
                policy_lever="Programas de alfabetización para adultos, becas Bienestar, CONAFE.",
                affected_population_pct=edu_lag,
            ))

        # Ordenar por severidad
        severity_order = {"alta": 0, "media": 1, "baja": 2}
        needs.sort(key=lambda n: severity_order.get(n.severity, 3))

        return needs[:5]  # Máximo 5 necesidades críticas

    # ── Sección 5: Oportunidades ──────────────────────────────────────────────

    def _identify_opportunities(self, pack: EvidencePack) -> list[str]:
        opps = []
        e = pack.economic
        s = pack.social
        i = pack.infrastructure

        # Vocación productiva
        if e.main_sectors:
            opps.append(
                f"Vocación productiva identificada en: {', '.join(e.main_sectors[:3])}. "
                "Potencial de política de clúster sectorial y fomento a la cadena de valor local."
            )

        # Densidad empresarial
        density = e.economic_units_per_1000.value
        if density and density >= 50:
            opps.append(
                f"Densidad empresarial de {density:.0f} unidades/1,000 hab. (DENUE 2023) "
                "indica tejido productivo local activo susceptible de formalización y escalamiento."
            )

        # Remesas como palanca
        remesas = e.remittances_mdp_annual.value
        if remesas and remesas > 0:
            opps.append(
                f"Flujo de remesas de {e.remittances_mdp_annual.display()} hacia Tlaxcala (Banxico 2023). "
                "Programas de captación productiva de remesas (3x1) pueden multiplicar inversión local."
            )

        # Bono demográfico
        youth = s.pct_youth_15_29.value
        if youth and youth >= 22:
            opps.append(
                f"Bono demográfico activo: {youth:.0f}% de la población entre 15–29 años (Censo 2020). "
                "Inversión en formación técnica y empleo juvenil genera retorno social alto."
            )

        # Internet y transformación digital
        internet = i.internet_access_pct.value
        if internet and internet >= 55:
            opps.append(
                f"Cobertura de internet de {internet:.0f}% (Censo 2020) habilita estrategias "
                "de gobierno digital, telemedicina, educación en línea y comercio electrónico local."
            )
        elif internet and internet < 40:
            opps.append(
                "La brecha digital es simultáneamente un reto y una oportunidad: "
                "inversión en conectividad tiene alto impacto en educación, empleo y acceso a servicios."
            )

        return opps[:5]

    # ── Resumen ejecutivo ─────────────────────────────────────────────────────

    def _build_executive_summary(
        self, pack: EvidencePack, report: DiagnosisReport
    ) -> str:
        name = pack.municipality_name
        pop = pack.social.population_total
        poverty = pack.social.poverty_rate_pct
        critical_count = len(report.critical_needs)
        top_need = report.critical_needs[0].title if report.critical_needs else "N/A"
        top_sector = pack.economic.main_sectors[0] if pack.economic.main_sectors else "diversificado"

        lines = [
            f"{name} (Tlaxcala) cuenta con {pop.display()} ({pop.period}). ",
        ]

        if poverty.value:
            lines.append(
                f"El {poverty.value:.1f}% de su población vive en pobreza multidimensional "
                f"(CONEVAL 2020), con {pack.social.social_security_lack_pct.value or 'N/D'}% "
                f"sin seguridad social. "
            )

        lines.append(
            f"Su principal actividad económica es {top_sector}, "
            f"con {pack.economic.economic_units_total.display()} unidades económicas activas (DENUE 2023). "
        )

        if pack.economic.informal_employment_pct.value:
            lines.append(
                f"El empleo informal alcanza {pack.economic.informal_employment_pct.display()}, "
                "limitando la cobertura de seguridad social. "
            )

        lines.append(
            f"Se identificaron {critical_count} necesidades críticas, "
            f"siendo la más urgente: '{top_need}'. "
        )

        return "".join(lines).strip()


diagnosis_generator = DiagnosisGenerator()
