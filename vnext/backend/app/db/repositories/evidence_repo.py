"""Evidence records repository."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import EvidenceRecordDB


class EvidenceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest(self, municipality_id: str) -> Optional[EvidenceRecordDB]:
        result = await self.db.execute(
            select(EvidenceRecordDB)
            .where(EvidenceRecordDB.municipality_id == municipality_id)
            .order_by(desc(EvidenceRecordDB.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, record_id: str) -> Optional[EvidenceRecordDB]:
        result = await self.db.execute(
            select(EvidenceRecordDB).where(EvidenceRecordDB.id == record_id)
        )
        return result.scalar_one_or_none()

    async def is_fresh(self, record: EvidenceRecordDB, current_snapshot: str) -> bool:
        if record.snapshot_version != current_snapshot:
            return False
        if record.expires_at:
            now = datetime.now(timezone.utc)
            exp = record.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
                return False
        return True

    async def save(self, record: EvidenceRecordDB) -> EvidenceRecordDB:
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def list_by_municipality(
        self, municipality_id: str, limit: int = 10
    ) -> list[EvidenceRecordDB]:
        result = await self.db.execute(
            select(EvidenceRecordDB)
            .where(EvidenceRecordDB.municipality_id == municipality_id)
            .order_by(desc(EvidenceRecordDB.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
