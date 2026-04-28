"""Analysis runs repository."""
from __future__ import annotations
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import AnalysisRunDB


class AnalysisRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_valid(self, municipality_id: str) -> Optional[AnalysisRunDB]:
        """Returns most recent analysis with status='completed' and validation_passed=True."""
        result = await self.db.execute(
            select(AnalysisRunDB)
            .where(
                AnalysisRunDB.municipality_id == municipality_id,
                AnalysisRunDB.status == "completed",
                AnalysisRunDB.validation_passed == True,
            )
            .order_by(desc(AnalysisRunDB.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, run_id: str) -> Optional[AnalysisRunDB]:
        result = await self.db.execute(
            select(AnalysisRunDB).where(AnalysisRunDB.id == run_id)
        )
        return result.scalar_one_or_none()

    async def history(self, municipality_id: str, limit: int = 20) -> list[AnalysisRunDB]:
        result = await self.db.execute(
            select(AnalysisRunDB)
            .where(AnalysisRunDB.municipality_id == municipality_id)
            .order_by(desc(AnalysisRunDB.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def save(self, run: AnalysisRunDB) -> AnalysisRunDB:
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def invalidate_all_for_municipality(self, municipality_id: str) -> int:
        """Marks all completed runs as invalid (e.g. when source data changes)."""
        from sqlalchemy import update
        result = await self.db.execute(
            update(AnalysisRunDB)
            .where(
                AnalysisRunDB.municipality_id == municipality_id,
                AnalysisRunDB.status == "completed",
            )
            .values(status="invalid")
        )
        await self.db.commit()
        return result.rowcount
