"""Seed municipalities from reference JSON into DB. Run: python -m scripts.seed"""
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.connection import AsyncSessionLocal, create_tables
from app.models.db_models import MunicipalityDB


async def seed():
    await create_tables()
    data = json.loads((Path(__file__).parent.parent / "app/data/reference/municipalities.json").read_text(encoding="utf-8"))

    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM municipalities"))
        count = result.scalar()
        if count and count > 0:
            print(f"Already seeded: {count} municipalities. Use --force to re-seed.")
            return

        for m in data:
            db.add(MunicipalityDB(
                id=m["id"], name=m["name"],
                state_id=m.get("state_id","TLX"),
                population_approx=m.get("population_approx",0),
                category=m.get("category","municipio_rural"),
                region=m.get("region","Valle Central"),
            ))
        await db.commit()
        print(f"✓ Seeded {len(data)} municipalities.")


if __name__ == "__main__":
    asyncio.run(seed())
