"""
TerritoryRepository — loads municipalities, reference zones and profiles from
reference JSON files.

Read-only, in-memory, singleton.

Expected directory:
    app/data/reference/

Expected files:
    municipalities.json
    neighborhoods.json
    territorial_profiles.json
    schema_version.json

Notes:
    - neighborhoods.json may actually contain one reference zone per municipality.
    - Some files use "id" instead of "municipality_id".
    - This repository is intentionally tolerant to schema variations.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "reference"


class TerritoryRepository:
    _instance: Optional["TerritoryRepository"] = None

    def __init__(self) -> None:
        self._municipalities: dict[str, dict[str, Any]] = {}
        self._neighborhoods: dict[str, dict[str, Any]] = {}
        self._profiles: dict[str, dict[str, Any]] = {}
        self._schema_version: dict[str, Any] = {}
        self._load()

    @classmethod
    def get_instance(cls) -> "TerritoryRepository":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset singleton instance.

        Useful only for tests or development reloads.
        The running backend normally reloads this module on process restart.
        """
        cls._instance = None

    # ─────────────────────────────────────────────────────────────────────
    # Loading
    # ─────────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        municipalities_path = DATA_DIR / "municipalities.json"
        neighborhoods_path = DATA_DIR / "neighborhoods.json"
        profiles_path = DATA_DIR / "territorial_profiles.json"
        schema_path = DATA_DIR / "schema_version.json"

        self._ensure_file_exists(municipalities_path)
        self._ensure_file_exists(neighborhoods_path)
        self._ensure_file_exists(profiles_path)

        municipalities = self._read_json_list(municipalities_path)
        neighborhoods = self._read_json_list(neighborhoods_path)
        profiles = self._read_json_list(profiles_path)

        for m in municipalities:
            mid = self._normalize_id(m.get("id"))

            if not mid:
                logger.warning("Municipality skipped because it has no id: %s", m)
                continue

            self._municipalities[mid] = m

        for index, n in enumerate(neighborhoods):
            nid = self._normalize_id(
                n.get("id")
                or n.get("entity_id")
                or n.get("municipality_id")
                or n.get("municipio_id")
                or n.get("cvegeo")
                or n.get("CVEGEO")
                or f"zone-{index}"
            )

            if not nid:
                logger.warning("Reference zone skipped because it has no id: %s", n)
                continue

            self._neighborhoods[nid] = n

        for p in profiles:
            entity_id = self._normalize_id(
                p.get("entity_id")
                or p.get("id")
                or p.get("municipality_id")
                or p.get("municipio_id")
                or p.get("cvegeo")
                or p.get("CVEGEO")
            )

            if not entity_id:
                logger.warning("Territorial profile skipped because it has no id: %s", p)
                continue

            self._profiles[entity_id] = p

        if schema_path.exists():
            with open(schema_path, encoding="utf-8") as f:
                loaded_schema = json.load(f)

            if isinstance(loaded_schema, dict):
                self._schema_version = loaded_schema
            else:
                self._schema_version = {"version": str(loaded_schema)}
        else:
            self._schema_version = {"version": "unknown", "hash": "unknown"}

        logger.info(
            "TerritoryRepository: %d municipios, %d zonas, %d perfiles | schema=%s | data_dir=%s",
            len(self._municipalities),
            len(self._neighborhoods),
            len(self._profiles),
            self._schema_version.get("version")
            or self._schema_version.get("hash")
            or "?",
            DATA_DIR,
        )

    def _ensure_file_exists(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(
                f"Required reference file not found: {path}. "
                "Verify that reference files are located under app/data/reference/."
            )

    def _read_json_list(self, path: Path) -> list[dict[str, Any]]:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)

        if not isinstance(payload, list):
            raise ValueError(f"Reference file must contain a JSON list: {path}")

        cleaned: list[dict[str, Any]] = []

        for item in payload:
            if isinstance(item, dict):
                cleaned.append(item)
            else:
                logger.warning("Non-dict item skipped in %s: %s", path.name, item)

        return cleaned

    # ─────────────────────────────────────────────────────────────────────
    # Public getters
    # ─────────────────────────────────────────────────────────────────────

    def get_municipality(self, municipality_id: str) -> Optional[dict[str, Any]]:
        target = self._normalize_id(municipality_id)

        if not target:
            return None

        return self._municipalities.get(target)

    def get_all_municipalities(self) -> list[dict[str, Any]]:
        return list(self._municipalities.values())

    def get_neighborhoods_for(self, municipality_id: str) -> list[dict[str, Any]]:
        """
        Return reference zones/neighborhoods associated with a municipality.

        This method is intentionally tolerant because reference files may use:
            - municipality_id
            - entity_id
            - municipio_id
            - municipality
            - id
            - cvegeo
            - CVEGEO
            - Cvegeo

        In the current reference dataset, neighborhoods.json may contain records like:

            {
                "id": "TLX-TZM",
                "name": "Tzompantepec",
                "seat_lat_decimal": 19.376062,
                "seat_lon_decimal": -98.091171
            }

        Therefore, matching by "id" is necessary for DENUE coordinate resolution.
        """
        target = self._normalize_id(municipality_id)

        if not target:
            return []

        matches: list[dict[str, Any]] = []

        for zone in self._neighborhoods.values():
            candidate_ids = self._candidate_ids(zone)

            if target in candidate_ids:
                matches.append(zone)

        if not matches:
            logger.warning(
                "No neighborhoods/zones found for municipality_id=%s. "
                "Available zone keys sample=%s | first zone sample=%s",
                municipality_id,
                self._sample_neighborhood_keys(),
                self._sample_neighborhood_summary(),
            )

        return matches

    def get_profile(self, entity_id: str) -> Optional[dict[str, Any]]:
        target = self._normalize_id(entity_id)

        if not target:
            return None

        return self._profiles.get(target)

    def get_schema_version(self) -> str:
        return str(
            self._schema_version.get("hash")
            or self._schema_version.get("version")
            or "unknown"
        )

    def exists(self, municipality_id: str) -> bool:
        target = self._normalize_id(municipality_id)
        return bool(target and target in self._municipalities)

    # ─────────────────────────────────────────────────────────────────────
    # Optional helpers useful for diagnostics
    # ─────────────────────────────────────────────────────────────────────

    def find_reference_zone(self, municipality_id: str) -> Optional[dict[str, Any]]:
        """
        Return the first matching reference zone for a municipality.

        Useful when only one zone per municipality is expected.
        """
        matches = self.get_neighborhoods_for(municipality_id)
        return matches[0] if matches else None

    def get_coordinates_for(
        self,
        municipality_id: str,
    ) -> tuple[float | None, float | None, str | None]:
        """
        Resolve municipality coordinates directly from repository data.

        Priority:
            1. municipalities.json
            2. neighborhoods.json / reference zones

        Returns:
            (lat, lon, source_label)
        """
        municipality = self.get_municipality(municipality_id)

        lat = self._first_float_from(
            municipality,
            (
                "lat",
                "latitude",
                "lat_decimal",
                "seat_lat_decimal",
                "municipal_seat_lat",
                "cabecera_lat",
            ),
        )
        lon = self._first_float_from(
            municipality,
            (
                "lon",
                "lng",
                "longitude",
                "lon_decimal",
                "seat_lon_decimal",
                "municipal_seat_lon",
                "cabecera_lon",
            ),
        )

        if lat is not None and lon is not None:
            return lat, lon, "municipalities.json"

        for zone in self.get_neighborhoods_for(municipality_id):
            lat = self._first_float_from(
                zone,
                (
                    "seat_lat_decimal",
                    "lat",
                    "latitude",
                    "lat_decimal",
                    "municipal_seat_lat",
                    "cabecera_lat",
                ),
            )
            lon = self._first_float_from(
                zone,
                (
                    "seat_lon_decimal",
                    "lon",
                    "lng",
                    "longitude",
                    "lon_decimal",
                    "municipal_seat_lon",
                    "cabecera_lon",
                ),
            )

            if lat is not None and lon is not None:
                return lat, lon, "neighborhoods.json"

        return None, None, None

    # ─────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────

    def _candidate_ids(self, payload: dict[str, Any]) -> set[str]:
        """
        Build a normalized set of possible identifiers for a reference record.
        """
        values = [
            payload.get("municipality_id"),
            payload.get("entity_id"),
            payload.get("municipio_id"),
            payload.get("municipality"),
            payload.get("id"),
            payload.get("cvegeo"),
            payload.get("CVEGEO"),
            payload.get("Cvegeo"),
            payload.get("clave_municipio"),
            payload.get("municipality_code"),
        ]

        candidates = {
            normalized
            for value in values
            if (normalized := self._normalize_id(value))
        }

        return candidates

    def _normalize_id(self, value: Any) -> str:
        return str(value or "").strip()

    def _first_float_from(
        self,
        payload: Optional[dict[str, Any]],
        keys: tuple[str, ...],
    ) -> float | None:
        if not isinstance(payload, dict):
            return None

        for key in keys:
            raw = payload.get(key)

            if raw is None:
                continue

            try:
                return float(raw)
            except (TypeError, ValueError):
                continue

        return None

    def _sample_neighborhood_keys(self) -> list[str]:
        """
        Return a small sample of keys present in the first loaded zone.
        Useful for diagnosing schema mismatches.
        """
        first = next(iter(self._neighborhoods.values()), None)

        if not isinstance(first, dict):
            return []

        return list(first.keys())[:20]

    def _sample_neighborhood_summary(self) -> dict[str, Any]:
        """
        Return a small safe summary of the first loaded zone.
        Avoids dumping the full file into logs.
        """
        first = next(iter(self._neighborhoods.values()), None)

        if not isinstance(first, dict):
            return {}

        keys = [
            "id",
            "entity_id",
            "municipality_id",
            "name",
            "seat_lat_decimal",
            "seat_lon_decimal",
            "lat",
            "lon",
            "latitude",
            "longitude",
        ]

        return {
            key: first.get(key)
            for key in keys
            if key in first
        }