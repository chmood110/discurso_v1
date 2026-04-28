"""Speech runs repository."""
from __future__ import annotations
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import SpeechRunDB


class SpeechRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_valid(self, municipality_id: str) -> Optional[SpeechRunDB]:
        result = await self.db.execute(
            select(SpeechRunDB)
            .where(
                SpeechRunDB.municipality_id == municipality_id,
                SpeechRunDB.status == "completed",
                SpeechRunDB.validation_passed == True,
            )
            .order_by(desc(SpeechRunDB.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_by_params(
        self, municipality_id: str, parameter_hash: str
    ) -> Optional[SpeechRunDB]:
        """Return latest valid speech with matching parameter_hash (for cache reuse)."""
        result = await self.db.execute(
            select(SpeechRunDB)
            .where(
                SpeechRunDB.municipality_id == municipality_id,
                SpeechRunDB.parameter_hash == parameter_hash,
                SpeechRunDB.status == "completed",
                SpeechRunDB.validation_passed == True,
            )
            .order_by(desc(SpeechRunDB.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, run_id: str) -> Optional[SpeechRunDB]:
        result = await self.db.execute(
            select(SpeechRunDB).where(SpeechRunDB.id == run_id)
        )
        return result.scalar_one_or_none()

    async def save(self, run: SpeechRunDB) -> SpeechRunDB:
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run
