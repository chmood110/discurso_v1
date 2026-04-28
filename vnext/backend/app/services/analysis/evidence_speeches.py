"""
Generates two evidence-based speech outlines directly from the EvidencePack
(without Groq) for immediate use, plus enriched prompts for Groq generation.
"""
from __future__ import annotations

from app.services.integrations.data_models import EvidencePack
from app.services.analysis.diagnosis import DiagnosisReport


class EvidenceSpeechOutlines:
    """Two speech outlines: technical/investment and social/community."""

    def __init__(
        self,
        technical: dict,
        social: dict,
    ):
        self.technical = technical
        self.social = social


class EvidenceSpeechGenerator:
    """Builds speech outlines and Groq-ready prompts from real evidence."""

    def generate(
        self,
        pack: EvidencePack,
        report: DiagnosisReport,
        objective: str = "",
        candidate_name: str = "",
        candidate_position: str = "",
    ) -> EvidenceSpeechOutlines:
        name = pack.municipality_name
        pop = pack.social.population_total.display()
        poverty = pack.social.poverty_rate_pct.display()
        informal = pack.economic.informal_employment_pct.display()
        top_sectors = ", ".join(pack.economic.main_sectors[:3]) if pack.economic.main_sectors else "diversificados"
        top_need = report.critical_needs[0].title if report.critical_needs else "desarrollo social"
        needs_list = [n.title for n in report.critical_needs[:3]]

        technical = self._build_technical(
            name, pop, poverty, informal, top_sectors, needs_list,
            objective, candidate_name, candidate_position, pack,
        )
        social = self._build_social(
            name, pop, poverty, informal, top_need, needs_list,
            objective, candidate_name, candidate_position, pack, report,
        )
        return EvidenceSpeechOutlines(technical=technical, social=social)

    def _build_technical(
        self, name, pop, poverty, informal, top_sectors, needs_list,
        objective, candidate_name, candidate_position, pack,
    ) -> dict:
        units = pack.economic.economic_units_total.display()
        remittances = pack.economic.remittances_mdp_annual.display()
        water = pack.infrastructure.drinking_water_access_pct.display()

        opening = (
            f"{name} es un municipio de {pop} que enfrenta desafíos estructurales medibles. "
            f"Con una tasa de pobreza del {poverty} (CONEVAL 2020) y {informal} de empleo informal, "
            "la evidencia señala con claridad dónde deben concentrarse las inversiones."
        )

        body = [
            {
                "section": "Diagnóstico con datos",
                "content": (
                    f"El análisis de fuentes oficiales (INEGI, CONEVAL, Banxico) revela que {name} "
                    f"cuenta con {units} unidades económicas activas (DENUE 2023), "
                    f"cuya actividad principal es {top_sectors}. "
                    f"Las remesas hacia Tlaxcala suman {remittances} anuales (Banxico 2023), "
                    "evidenciando la migración como válvula de escape económica que debe revertirse."
                ),
            },
            {
                "section": "Necesidades con evidencia",
                "content": (
                    "Los datos identifican tres prioridades críticas: "
                    + "; ".join(needs_list)
                    + ". Cada una tiene línea base verificable y metas SMART propuestas."
                ),
            },
            {
                "section": "Propuesta de inversión",
                "content": (
                    f"Una estrategia de inversión eficiente para {name} debe: "
                    "(1) fortalecer la formalización laboral para ampliar base tributaria y cobertura social; "
                    f"(2) resolver el déficit en agua potable ({water} cobertura actual, INEGI 2020) "
                    "mediante recursos FAIS; "
                    "(3) detonar la vocación productiva existente en "
                    f"{pack.economic.main_sectors[0] if pack.economic.main_sectors else 'sectores clave'} "
                    "con incentivos a la cadena de valor."
                ),
            },
            {
                "section": "Rendición de cuentas",
                "content": (
                    "Las metas propuestas son medibles con fuentes oficiales existentes: "
                    "CONEVAL (bienal), INEGI ENOE (trimestral), DENUE (actualización anual). "
                    "Esto permite seguimiento ciudadano independiente."
                ),
            },
        ]

        closing = (
            f"La evidencia es clara: {name} tiene los desafíos identificados y las herramientas para resolverlos. "
            f"{('El candidato ' + candidate_name) if candidate_name else 'Este plan'} "
            "propone gobierno basado en datos, con metas verificables y rendición de cuentas real."
        )

        return {
            "type": "technical_investment",
            "title": f"Discurso Técnico — Inversión y Política Pública en {name}",
            "audience": "Inversionistas, tomadores de decisión, academia, medios especializados",
            "tone": "Técnico, propositivo, basado en evidencia",
            "data_sources_cited": pack.sources_used,
            "opening": opening,
            "body_sections": body,
            "closing": closing,
            "key_statistics": [
                f"Población: {pop} (INEGI Censo 2020)",
                f"Tasa de pobreza: {poverty} (CONEVAL 2020)",
                f"Empleo informal: {informal} (INEGI ENOE)",
                f"Unidades económicas: {units} (DENUE 2023)",
                f"Remesas Tlaxcala: {remittances} anuales (Banxico 2023)",
                f"Agua potable: {water} (INEGI Censo 2020)",
            ],
        }

    def _build_social(
        self, name, pop, poverty, informal, top_need, needs_list,
        objective, candidate_name, candidate_position, pack, report,
    ) -> dict:
        worst_dep = report.demographic_profile.get(
            "social_deprivations", {}
        ).get("worst_deprivation", "carencia social")
        youth = pack.social.pct_youth_15_29.display()
        health_gap = pack.social.health_access_lack_pct.display()
        food_gap = pack.social.food_insecurity_pct.display()

        opening = (
            f"Vecinas y vecinos de {name}: "
            "Antes de hablar de lo que vamos a hacer, quiero reconocer lo que ya saben. "
            f"Que en nuestra comunidad, casi {poverty} de las familias vive en pobreza. "
            "Eso no es un número: son nuestros vecinos, nuestros hijos, nuestra gente."
        )

        body = [
            {
                "section": "Reconocimiento del dolor ciudadano",
                "content": (
                    f"Los datos oficiales confirman lo que viven cada día: "
                    f"el {health_gap} de las personas no tiene acceso efectivo a servicios de salud. "
                    f"El {food_gap} enfrenta inseguridad alimentaria. "
                    f"Y el principal problema no resuelto es: {top_need}. "
                    "Eso lo dicen los números, pero también lo dicen ustedes cada que se les pregunta."
                ),
            },
            {
                "section": "Compromiso con las familias",
                "content": (
                    f"Nuestro plan para {name} tiene propuestas concretas: "
                    + "; ".join([n for n in needs_list])
                    + ". No son promesas vacías: cada una tiene meta medible con fuente oficial, "
                    "para que cualquier ciudadano pueda verificar el avance."
                ),
            },
            {
                "section": "El bono demográfico",
                "content": (
                    f"El {youth} de nuestra gente tiene entre 15 y 29 años. "
                    "Son el mayor activo que tiene este municipio. "
                    "Necesitamos que se queden aquí, que construyan sus familias aquí. "
                    "Para eso necesitamos empleo formal, educación de calidad y seguridad social real."
                ),
            },
            {
                "section": "La transparencia como base",
                "content": (
                    "Cada peso de inversión pública tendrá indicador, fecha y responsable. "
                    "El INEGI, el CONEVAL y el Banco de México publican datos que cualquier "
                    "ciudadano puede consultar. Eso es lo que hace la diferencia entre promesa y compromiso."
                ),
            },
        ]

        closing = (
            f"En {name} merecemos un gobierno que trabaje con datos reales, "
            "que reconozca los problemas sin excusas, "
            f"y que tenga el valor de medirse públicamente. "
            f"{('Eso es lo que ' + candidate_name + ' representa.') if candidate_name else 'Ese es el camino.'} "
            "Juntos podemos construirlo."
        )

        return {
            "type": "social_community",
            "title": f"Discurso Social — {name}, Tlaxcala",
            "audience": "Comunidad general, familias, adultos mayores, jóvenes",
            "tone": "Cercano, empático, esperanzador, con base en datos reales",
            "data_sources_cited": pack.sources_used,
            "opening": opening,
            "body_sections": body,
            "closing": closing,
            "emotional_hooks": [
                f"El {poverty} de familias en pobreza no es estadística, son nuestros vecinos",
                f"{youth} de jóvenes que merecen quedarse en su tierra",
                "Datos reales, no promesas vacías",
            ],
            "rational_hooks": [
                f"Pobreza: {poverty} (CONEVAL 2020) — verificable",
                f"Sin acceso a salud: {health_gap} (CONEVAL 2020)",
                f"Empleo informal: {informal} (INEGI ENOE)",
            ],
        }


evidence_speech_generator = EvidenceSpeechGenerator()
