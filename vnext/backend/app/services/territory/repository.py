"""
TerritoryRepository — loads municipalities and profiles from reference JSON files.
Read-only, in-memory, singleton.
"""
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "reference"


class TerritoryRepository:
    _instance: Optional["TerritoryRepository"] = None

    def __init__(self):
        self._municipalities: dict[str, dict] = {}
        self._neighborhoods: dict[str, dict] = {}
        self._profiles: dict[str, dict] = {}
        self._schema_version: dict = {}
        self._load()

    @classmethod
    def get_instance(cls) -> "TerritoryRepository":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self):
        with open(DATA_DIR / "municipalities.json", encoding="utf-8") as f:
            for m in json.load(f):
                self._municipalities[m["id"]] = m

        with open(DATA_DIR / "neighborhoods.json", encoding="utf-8") as f:
            for n in json.load(f):
                self._neighborhoods[n["id"]] = n

        with open(DATA_DIR / "territorial_profiles.json", encoding="utf-8") as f:
            for p in json.load(f):
                eid = p.get("entity_id")
                if eid:
                    self._profiles[eid] = p

        sv_path = DATA_DIR / "schema_version.json"
        if sv_path.exists():
            with open(sv_path) as f:
                self._schema_version = json.load(f)

        logger.info(
            "TerritoryRepository: %d municipios, %d zonas, %d perfiles | schema=%s",
            len(self._municipalities), len(self._neighborhoods),
            len(self._profiles), self._schema_version.get("version","?"),
        )

    def get_municipality(self, municipality_id: str) -> Optional[dict]:
        return self._municipalities.get(municipality_id)

    def get_all_municipalities(self) -> list[dict]:
        return list(self._municipalities.values())

    def get_neighborhoods_for(self, municipality_id: str) -> list[dict]:
        return [n for n in self._neighborhoods.values() if n.get("municipality_id") == municipality_id]

    def get_profile(self, entity_id: str) -> Optional[dict]:
        return self._profiles.get(entity_id)

    def get_schema_version(self) -> str:
        return self._schema_version.get("hash", "unknown")

    def exists(self, municipality_id: str) -> bool:
        return municipality_id in self._municipalities
