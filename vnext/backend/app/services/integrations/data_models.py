"""
Modelos de datos normalizados para todas las fuentes externas.
Cada modelo representa la estructura canónica independiente de la API origen.
"""
from typing import Optional
from pydantic import BaseModel, Field


class DataPoint(BaseModel):
    """Un dato individual con trazabilidad completa de fuente."""
    value: Optional[float] = None
    unit: str = ""
    period: str = ""          # "2020", "2023-Q4", "2023"
    source: str = ""          # "INEGI Censo 2020", "CONEVAL 2020", "Banxico SIE"
    geographic_level: str = "" # "municipal", "estatal", "nacional"
    municipality: Optional[str] = None
    available: bool = True
    limitation_note: Optional[str] = None  # Si hay degradación geográfica o dato faltante

    def display(self) -> str:
        if not self.available:
            return f"No disponible ({self.limitation_note or 'sin datos'})"
        val = f"{self.value:,.1f}" if self.value is not None else "N/D"
        return f"{val} {self.unit}".strip()


class SocialLayer(BaseModel):
    """Capa social: demografía + pobreza CONEVAL."""
    # Demografía (INEGI Censo 2020)
    population_total: DataPoint = Field(default_factory=DataPoint)
    population_density_km2: DataPoint = Field(default_factory=DataPoint)
    pct_youth_15_29: DataPoint = Field(default_factory=DataPoint)
    pct_adults_30_59: DataPoint = Field(default_factory=DataPoint)
    pct_elderly_60plus: DataPoint = Field(default_factory=DataPoint)
    pct_indigenous: DataPoint = Field(default_factory=DataPoint)
    pct_female: DataPoint = Field(default_factory=DataPoint)
    households_total: DataPoint = Field(default_factory=DataPoint)

    # Pobreza multidimensional (CONEVAL 2020)
    poverty_rate_pct: DataPoint = Field(default_factory=DataPoint)
    extreme_poverty_rate_pct: DataPoint = Field(default_factory=DataPoint)
    social_vulnerability_pct: DataPoint = Field(default_factory=DataPoint)
    # Carencias sociales CONEVAL
    education_lag_pct: DataPoint = Field(default_factory=DataPoint)
    health_access_lack_pct: DataPoint = Field(default_factory=DataPoint)
    social_security_lack_pct: DataPoint = Field(default_factory=DataPoint)
    housing_quality_lack_pct: DataPoint = Field(default_factory=DataPoint)
    basic_services_lack_pct: DataPoint = Field(default_factory=DataPoint)
    food_insecurity_pct: DataPoint = Field(default_factory=DataPoint)
    # Ingresos
    income_below_welfare_pct: DataPoint = Field(default_factory=DataPoint)


class EconomicLayer(BaseModel):
    """Capa económica: DENUE + INEGI ENOE + Banxico."""
    # Empleo (INEGI ENOE 2023)
    unemployment_rate_pct: DataPoint = Field(default_factory=DataPoint)
    informal_employment_pct: DataPoint = Field(default_factory=DataPoint)
    avg_income_mxn: DataPoint = Field(default_factory=DataPoint)
    labor_participation_pct: DataPoint = Field(default_factory=DataPoint)

    # Unidades económicas DENUE 2023
    economic_units_total: DataPoint = Field(default_factory=DataPoint)
    economic_units_per_1000: DataPoint = Field(default_factory=DataPoint)
    main_sectors: list[str] = Field(default_factory=list)
    health_units: DataPoint = Field(default_factory=DataPoint)
    education_units: DataPoint = Field(default_factory=DataPoint)
    commercial_units: DataPoint = Field(default_factory=DataPoint)

    # Remesas Banxico 2023
    remittances_mdp_annual: DataPoint = Field(default_factory=DataPoint)
    remittances_pct_gdp_state: DataPoint = Field(default_factory=DataPoint)

    # Contexto macro Banxico
    inflation_rate_pct: DataPoint = Field(default_factory=DataPoint)
    exchange_rate_usd_mxn: DataPoint = Field(default_factory=DataPoint)
    banxico_reference_rate_pct: DataPoint = Field(default_factory=DataPoint)


class InfrastructureLayer(BaseModel):
    """Capa de infraestructura y accesibilidad."""
    # Servicios en vivienda (INEGI Censo 2020)
    drinking_water_access_pct: DataPoint = Field(default_factory=DataPoint)
    electricity_access_pct: DataPoint = Field(default_factory=DataPoint)
    drainage_access_pct: DataPoint = Field(default_factory=DataPoint)
    internet_access_pct: DataPoint = Field(default_factory=DataPoint)
    paved_floor_pct: DataPoint = Field(default_factory=DataPoint)

    # Accesibilidad geográfica (estimado/referencia)
    minutes_to_nearest_hospital: DataPoint = Field(default_factory=DataPoint)
    minutes_to_state_capital: DataPoint = Field(default_factory=DataPoint)
    pct_localities_paved_road: DataPoint = Field(default_factory=DataPoint)

    # Educación (INEGI Censo 2020)
    literacy_rate_pct: DataPoint = Field(default_factory=DataPoint)
    avg_schooling_years: DataPoint = Field(default_factory=DataPoint)
    no_schooling_pct: DataPoint = Field(default_factory=DataPoint)


class EvidencePack(BaseModel):
    """Paquete consolidado de evidencia para un municipio de Tlaxcala."""
    municipality_id: str
    municipality_name: str
    state: str = "Tlaxcala"
    data_collection_timestamp: str = ""

    social: SocialLayer = Field(default_factory=SocialLayer)
    economic: EconomicLayer = Field(default_factory=EconomicLayer)
    infrastructure: InfrastructureLayer = Field(default_factory=InfrastructureLayer)

    # Trazabilidad de fuentes usadas
    sources_used: list[str] = Field(default_factory=list)
    sources_failed: list[str] = Field(default_factory=list)
    geographic_fallbacks: list[str] = Field(default_factory=list)
    data_quality: str = "reference"  # "live_api" | "reference" | "partial"
