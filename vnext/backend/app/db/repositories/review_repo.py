"""Review runs repository."""
from __future__ import annotations
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import ReviewRunDB


class ReviewRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest(self, municipality_id: str) -> Optional[ReviewRunDB]:
        result = await self.db.execute(
            select(ReviewRunDB)
            .where(ReviewRunDB.municipality_id == municipality_id)
            .order_by(desc(ReviewRunDB.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, review_id: str) -> Optional[ReviewRunDB]:
        result = await self.db.execute(
            select(ReviewRunDB).where(ReviewRunDB.id == review_id)
        )
        return result.scalar_one_or_none()

    async def list_by_municipality(
        self, municipality_id: str, limit: int = 10
    ) -> list[ReviewRunDB]:
        result = await self.db.execute(
            select(ReviewRunDB)
            .where(ReviewRunDB.municipality_id == municipality_id)
            .order_by(desc(ReviewRunDB.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def save(self, review: ReviewRunDB) -> ReviewRunDB:
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review
