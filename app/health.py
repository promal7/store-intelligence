from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import EventDB
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(EventDB.store_id, func.max(EventDB.timestamp))
            .group_by(EventDB.store_id)
        )
        rows = result.fetchall()

        stores = {}
        now = datetime.utcnow()
        for store_id, last_ts in rows:
            lag_minutes = (now - last_ts).seconds // 60 if last_ts else None
            stores[store_id] = {
                "last_event"  : last_ts.isoformat() if last_ts else None,
                "lag_minutes" : lag_minutes,
                "status"      : "STALE_FEED" if lag_minutes and lag_minutes > 10 else "OK"
            }

        return {
            "status"    : "healthy",
            "timestamp" : now.isoformat(),
            "stores"    : stores
        }
    except Exception as e:
        return {
            "status" : "unhealthy",
            "error"  : str(e)
        }
