"""
Seed script — loads municipalities into the DB from reference JSON.

Run once on fresh DB:

    python -m app.db.seed
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select

from app.db.connection import AsyncSessionLocal
from app.models.db_models import MunicipalityDB


logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent.parent / "data" / "reference" / "municipalities.json"


async def seed_municipalities() -> int:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Municipalities file not found: {DATA_FILE}")

    with open(DATA_FILE, encoding="utf-8") as f:
        municipalities = json.load(f)

    async with AsyncSessionLocal() as db:
        inserted = 0
        skipped = 0

        for m in municipalities:
            municipality_id = m.get("id")
            if not municipality_id:
                skipped += 1
                continue

            existing = await db.execute(
                select(MunicipalityDB).where(MunicipalityDB.id == municipality_id)
            )

            if existing.scalar_one_or_none():
                skipped += 1
                continue

            population_2020 = (
                m.get("population_2020")
                or m.get("population")
                or m.get("population_approx")
                or 0
            )

            db.add(
                MunicipalityDB(
                    id=municipality_id,
                    name=m.get("name", ""),
                    state_id=m.get("state_id", "TLX"),
                    population_2020=int(population_2020 or 0),
                    category=m.get("category", "municipio_rural"),
                    region=m.get("region", ""),
                )
            )

            inserted += 1

        await db.commit()

        logger.info(
            "Seed completed. Inserted=%d | Skipped=%d | Total=%d",
            inserted,
            skipped,
            len(municipalities),
        )

        return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    count = asyncio.run(seed_municipalities())
    print(f"Done. {count} municipalities inserted.")