"""
TerritoryContextAssembler — Builds rich textual territory context for AI prompts.

Key design:
- Produces highly specific text per municipality (not a generic template)
- Incorporates evidence_pack (from analysis module) when available
- Falls back gracefully to territorial_profiles.json profile data
- Includes data quality signals so the LLM knows confidence level
"""
from typing import Optional


class TerritoryContextAssembler:

    def to_prompt_context(self, assembled_context: dict) -> str:
        """Generates the territorial context block for LLM prompts."""
        lines: list[str] = []
        municipality = assembled_context.get("municipality") or {}
        neighborhood = assembled_context.get("neighborhood")
        profile      = assembled_context.get("profile") or {}
        narrative    = profile.get("narrative", {}) if isinstance(profile, dict) else {}

        mun_name     = municipality.get("name", "N/D")
        mun_region   = municipality.get("region", "")
        mun_cat      = municipality.get("category", "")
        mun_pop      = municipality.get("population_approx")

        lines.append("=== CONTEXTO TERRITORIAL — TLAXCALA ===")
        lines.append(
            f"Municipio: {mun_name}"
            + (f" | Región: {mun_region}" if mun_region else "")
            + (f" | Tipo: {mun_cat}" if mun_cat else "")
        )
        if mun_pop:
            lines.append(f"Población municipal: {mun_pop:,} hab. (INEGI Censo 2020)")

        if neighborhood:
            nh_name = neighborhood.get("name", "N/D")
            nh_type = neighborhood.get("type", "localidad")
            lines.append(f"Zona específica de análisis: {nh_name} ({nh_type})")

        # Priority 1: use evidence_pack (full analysis from /analysis module)
        evidence = assembled_context.get("evidence_pack")
        if evidence:
            self._append_evidence_context(lines, evidence, mun_name)
        elif profile:
            self._append_profile_context(lines, profile, narrative, mun_name)
        else:
            lines.append(
                f"\n[Nota: Sin perfil territorial detallado para {mun_name}. "
                "Se usará el contexto base del municipio para orientar la narrativa.]"
            )

        return "\n".join(lines)

    def _append_evidence_context(self, lines: list[str], evidence: dict, mun_name: str) -> None:
        """Appends rich context from a full EvidencePack/analysis result."""
        social   = evidence.get("social") or {}
        economic = evidence.get("economic") or {}
        infra    = evidence.get("infrastructure") or {}
        diagnosis = evidence.get("diagnosis") or {}
        data_quality = evidence.get("data_quality", "reference")

        # Data quality signal
        if data_quality == "estimated":
            lines.append(
                "\n[Nota de fuentes: datos municipales estimados por región/categoría. "
                "Úsalos para orientar narrativa, pero no los presentes como cifras exactas.]"
            )
        elif data_quality == "partial":
            lines.append(
                "\n[Nota de fuentes: datos parciales — algunas cifras provienen de escala estatal.]"
            )

        # Social data
        poverty = social.get("poverty_rate_pct") or {}
        if poverty.get("value"):
            lines.append(
                f"\nPobreza multidimensional: {poverty['value']:.1f}% de la población "
                f"({poverty.get('period','2020')}, {poverty.get('source','CONEVAL')})"
            )
        extreme = social.get("extreme_poverty_rate_pct") or {}
        if extreme.get("value"):
            lines.append(f"Pobreza extrema: {extreme['value']:.1f}%")

        ss = social.get("social_security_lack_pct") or {}
        health = social.get("health_access_lack_pct") or {}
        edu_lag = social.get("education_lag_pct") or {}
        food = social.get("food_insecurity_pct") or {}

        carencias = []
        if ss.get("value"):    carencias.append(f"sin seguridad social {ss['value']:.0f}%")
        if health.get("value"): carencias.append(f"sin acceso a salud {health['value']:.0f}%")
        if edu_lag.get("value"): carencias.append(f"rezago educativo {edu_lag['value']:.0f}%")
        if food.get("value"):  carencias.append(f"inseguridad alimentaria {food['value']:.0f}%")
        if carencias:
            lines.append(f"Carencias sociales principales: {'; '.join(carencias)}")

        # Economic data
        informal = economic.get("informal_employment_pct") or {}
        income   = economic.get("avg_income_mxn") or {}
        units    = economic.get("economic_units_total") or {}
        sectors  = economic.get("main_sectors") or []

        if informal.get("value"):
            lines.append(f"\nEmpleo informal: {informal['value']:.0f}% de la PEA ocupada")
        if income.get("value"):
            lines.append(f"Ingreso promedio mensual: ${income['value']:,.0f} MXN")
        if units.get("value"):
            lines.append(f"Unidades económicas activas: {int(units['value']):,} (DENUE 2023)")
        if sectors:
            lines.append(f"Sectores económicos dominantes: {', '.join(sectors[:4])}")

        # Infrastructure gaps
        water   = infra.get("drinking_water_access_pct") or {}
        internet= infra.get("internet_access_pct") or {}
        hospital= infra.get("minutes_to_nearest_hospital") or {}

        gaps = []
        if water.get("value") and water["value"] < 88:
            gaps.append(f"déficit de agua potable ({water['value']:.0f}% cobertura)")
        if internet.get("value") and internet["value"] < 55:
            gaps.append(f"brecha digital ({internet['value']:.0f}% hogares con internet)")
        if hospital.get("value") and hospital["value"] > 25:
            gaps.append(f"hospital a {int(hospital['value'])} min (atención médica limitada)")
        if gaps:
            lines.append(f"Brechas de infraestructura: {'; '.join(gaps)}")

        # Diagnosis: critical needs
        needs = diagnosis.get("critical_needs") or []
        if needs:
            lines.append(f"\nNecesidades críticas identificadas:")
            for n in needs[:4]:
                title = n.get("title","") if isinstance(n, dict) else str(n)
                sev   = n.get("severity","") if isinstance(n, dict) else ""
                desc  = n.get("description","") if isinstance(n, dict) else ""
                short = desc[:90] + "…" if len(desc) > 90 else desc
                badge = f"[{sev.upper()}]" if sev else ""
                lines.append(f"  • {title} {badge}: {short}")

        # Diagnosis: opportunities
        opps = diagnosis.get("opportunities") or []
        if opps:
            lines.append(f"\nOportunidades estratégicas:")
            for o in opps[:3]:
                txt = o[:100] + "…" if len(o) > 100 else o
                lines.append(f"  → {txt}")

    def _append_profile_context(
        self, lines: list[str], profile: dict, narrative: dict, mun_name: str
    ) -> None:
        """Appends context from territorial_profiles.json profile data."""
        pop  = profile.get("population")
        if pop:
            lines.append(f"\nPoblación en zona: {pop:,} hab.")

        eco = profile.get("economic") or {}
        if eco:
            unemp = eco.get("unemployment_rate")
            if unemp:
                lines.append(f"Desempleo estimado: {unemp}%")
            inf = eco.get("informal_employment_pct")
            if inf:
                lines.append(f"Empleo informal: {inf}%")
            acts = eco.get("main_activities") or []
            if acts:
                lines.append(f"Actividades económicas: {', '.join(acts)}")

        social = profile.get("social") or {}
        if social:
            mi  = social.get("marginalization_index")
            pov = social.get("poverty_rate")
            ext = social.get("extreme_poverty_rate")
            if mi:  lines.append(f"Marginación: {mi}")
            if pov: lines.append(f"Pobreza: {pov}%")
            if ext: lines.append(f"Pobreza extrema: {ext}%")

        services = profile.get("services") or {}
        if services:
            deficit = [k for k, v in services.items() if isinstance(v, (int, float)) and v < 80]
            if deficit:
                lines.append(f"Servicios con déficit (<80%): {', '.join(deficit)}")

        pain   = narrative.get("pain_points") or []
        opps   = narrative.get("opportunities") or []
        sens   = narrative.get("sensitive_topics") or []
        frm    = narrative.get("framing_suggestions") or []
        tone   = narrative.get("recommended_tone", "moderado")

        if pain:
            lines.append(f"\nDolores ciudadanos: {'; '.join(pain)}")
        if opps:
            lines.append(f"Oportunidades narrativas: {'; '.join(opps)}")
        if sens:
            lines.append(f"Temas sensibles: {'; '.join(sens)}")
        if frm:
            lines.append(f"Marcos sugeridos: {'; '.join(frm)}")
        lines.append(f"Tono comunicacional recomendado: {tone}")

    # ── Extractors ───────────────────────────────────────────────────────────

    def extract_pain_points(self, assembled_context: dict) -> list[str]:
        evidence = assembled_context.get("evidence_pack") or {}
        if evidence:
            diagnosis = evidence.get("diagnosis") or {}
            needs = diagnosis.get("critical_needs") or []
            if needs:
                result = []
                for n in needs:
                    if isinstance(n, dict) and n.get("title"):
                        result.append(n["title"])
                if result:
                    return result

        profile  = assembled_context.get("profile") or {}
        narrative = profile.get("narrative") or {} if isinstance(profile, dict) else {}
        return narrative.get("pain_points") or []

    def extract_opportunities(self, assembled_context: dict) -> list[str]:
        evidence = assembled_context.get("evidence_pack") or {}
        if evidence:
            diagnosis = evidence.get("diagnosis") or {}
            opps = diagnosis.get("opportunities") or []
            if opps:
                return opps

        profile  = assembled_context.get("profile") or {}
        narrative = profile.get("narrative") or {} if isinstance(profile, dict) else {}
        return narrative.get("opportunities") or []

    def extract_key_topics(self, assembled_context: dict) -> list[str]:
        pain = self.extract_pain_points(assembled_context)
        opp  = self.extract_opportunities(assembled_context)
        return list(dict.fromkeys(pain + opp))
