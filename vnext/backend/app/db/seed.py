"""
Seed script — loads municipalities into the DB from reference JSON.
Run once on fresh DB: python -m app.db.seed
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.connection import AsyncSessionLocal, create_tables
from app.models.db_models import MunicipalityDB
from sqlalchemy import select

logger = logging.getLogger(__name__)
DATA_FILE = Path(__file__).parent.parent / "data" / "reference" / "municipalities.json"


async def seed_municipalities() -> int:
    await create_tables()
    with open(DATA_FILE, encoding="utf-8") as f:
        municipalities = json.load(f)

    async with AsyncSessionLocal() as db:
        inserted = 0
        for m in municipalities:
            existing = await db.execute(
                select(MunicipalityDB).where(MunicipalityDB.id == m["id"])
            )
            if existing.scalar_one_or_none():
                continue
            db.add(MunicipalityDB(
                id=m["id"],
                name=m["name"],
                state_id=m.get("state_id", "TLX"),
                population_approx=m.get("population_approx", 0),
                category=m.get("category", "municipio_rural"),
                region=m.get("region", ""),
            ))
            inserted += 1
        await db.commit()
        logger.info("Seeded %d municipalities (%d already existed)", inserted, len(municipalities) - inserted)
        return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    count = asyncio.run(seed_municipalities())
    print(f"Done. {count} municipalities inserted.")
