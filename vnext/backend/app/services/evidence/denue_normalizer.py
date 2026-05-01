from __future__ import annotations

from collections import Counter
from typing import Any


HEALTH_KEYWORDS = (
    "consultorio",
    "clínica",
    "clinica",
    "hospital",
    "salud",
    "médico",
    "medico",
    "odontológico",
    "odontologico",
    "laboratorio médico",
    "laboratorio medico",
    "farmacia",
)

SCHOOL_KEYWORDS = (
    "escuela",
    "educación",
    "educacion",
    "preescolar",
    "primaria",
    "secundaria",
    "bachillerato",
    "universidad",
    "colegio",
    "instituto",
)

SECTOR_KEYWORDS = {
    "Comercio al por menor": (
        "comercio al por menor",
        "tiendas de abarrotes",
        "misceláneas",
        "miscelaneas",
        "farmacias",
    ),
    "Servicios personales": (
        "salones y clínicas de belleza",
        "peluquerías",
        "peluquerias",
        "lavanderías",
        "lavanderias",
        "reparación",
        "reparacion",
    ),
    "Alimentos y bebidas": (
        "restaurantes",
        "cafeterías",
        "cafeterias",
        "antojitos",
        "tortillerías",
        "tortillerias",
        "panificación",
        "panificacion",
    ),
    "Salud": HEALTH_KEYWORDS,
    "Educación": SCHOOL_KEYWORDS,
    "Manufactura": (
        "fabricación",
        "fabricacion",
        "manufactura",
        "confección",
        "confeccion",
        "industria",
    ),
    "Servicios profesionales": (
        "servicios profesionales",
        "contabilidad",
        "jurídicos",
        "juridicos",
        "arquitectura",
        "ingeniería",
        "ingenieria",
        "consultoría",
        "consultoria",
    ),
}


def normalize_denue_records(
    records: list[dict[str, Any]],
    *,
    municipality_name: str,
    source: str = "INEGI DENUE API",
) -> dict[str, Any]:
    """
    Normaliza registros DENUE crudos en indicadores útiles para EvidenceRecordDB.

    Entrada:
        Lista de establecimientos devuelta por INEGI DENUE.

    Salida:
        Diccionario listo para integrarse a:
            evidence.economic_data
            evidence.infrastructure_data
    """
    cleaned = [
        record for record in records
        if isinstance(record, dict)
    ]

    total = len(cleaned)

    activity_counter: Counter[str] = Counter()
    sector_counter: Counter[str] = Counter()
    size_counter: Counter[str] = Counter()
    neighborhood_counter: Counter[str] = Counter()

    health_count = 0
    school_count = 0

    for record in cleaned:
        activity = str(record.get("Clase_actividad") or "").strip()
        size = str(record.get("Estrato") or "No especificado").strip()
        neighborhood = str(record.get("Colonia") or "No especificada").strip()

        if activity:
            activity_counter[activity] += 1

        if size:
            size_counter[size] += 1

        if neighborhood:
            neighborhood_counter[neighborhood] += 1

        activity_low = activity.casefold()

        if any(keyword in activity_low for keyword in HEALTH_KEYWORDS):
            health_count += 1

        if any(keyword in activity_low for keyword in SCHOOL_KEYWORDS):
            school_count += 1

        matched_sector = False
        for sector, keywords in SECTOR_KEYWORDS.items():
            if any(keyword in activity_low for keyword in keywords):
                sector_counter[sector] += 1
                matched_sector = True
                break

        if not matched_sector:
            sector_counter["Otros servicios y actividades"] += 1

    top_activities = [
        {
            "activity": activity,
            "count": count,
            "share_pct": round((count / total) * 100, 2) if total else 0.0,
        }
        for activity, count in activity_counter.most_common(10)
    ]

    sector_distribution = [
        {
            "sector": sector,
            "count": count,
            "share_pct": round((count / total) * 100, 2) if total else 0.0,
        }
        for sector, count in sector_counter.most_common()
    ]

    business_size_distribution = [
        {
            "size": size,
            "count": count,
            "share_pct": round((count / total) * 100, 2) if total else 0.0,
        }
        for size, count in size_counter.most_common()
    ]

    top_neighborhoods = [
        {
            "neighborhood": neighborhood,
            "count": count,
            "share_pct": round((count / total) * 100, 2) if total else 0.0,
        }
        for neighborhood, count in neighborhood_counter.most_common(10)
    ]

    return {
        "economic_data": {
            "business_units_total_api": {
                "value": total,
                "source": source,
                "origin": "api",
                "scope": "municipal_area",
                "municipality_name": municipality_name,
            },
            "sector_distribution_api": {
                "value": sector_distribution,
                "source": source,
                "origin": "api",
                "scope": "municipal_area",
            },
            "top_economic_activities_api": {
                "value": top_activities,
                "source": source,
                "origin": "api",
                "scope": "municipal_area",
            },
            "business_size_distribution_api": {
                "value": business_size_distribution,
                "source": source,
                "origin": "api",
                "scope": "municipal_area",
            },
            "top_neighborhoods_business_api": {
                "value": top_neighborhoods,
                "source": source,
                "origin": "api",
                "scope": "municipal_area",
            },
        },
        "infrastructure_data": {
            "health_facilities_count_api": {
                "value": health_count,
                "source": source,
                "origin": "api",
                "scope": "municipal_area",
            },
            "schools_count_api": {
                "value": school_count,
                "source": source,
                "origin": "api",
                "scope": "municipal_area",
            },
        },
    }