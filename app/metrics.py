from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import EventDB
from datetime import date

router = APIRouter()

@router.get("/stores/{store_id}/metrics")
async def get_metrics(store_id: str, db: AsyncSession = Depends(get_db)):
    today = date.today()

    visitors_result = await db.execute(
        select(func.count(func.distinct(EventDB.visitor_id)))
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type == "ENTRY")
        .where(func.date(EventDB.timestamp) == today)
    )
    unique_visitors = visitors_result.scalar() or 0

    billing_result = await db.execute(
        select(func.count(func.distinct(EventDB.visitor_id)))
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type.in_(["BILLING_QUEUE_JOIN", "ZONE_ENTER"]))
        .where(EventDB.zone_id == "BILLING")
        .where(func.date(EventDB.timestamp) == today)
    )
    billing_visitors = billing_result.scalar() or 0
    conversion_rate = round(billing_visitors / unique_visitors, 3) if unique_visitors > 0 else 0.0

    dwell_result = await db.execute(
        select(EventDB.zone_id, func.avg(EventDB.dwell_ms))
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type == "ZONE_DWELL")
        .where(EventDB.zone_id != None)
        .where(func.date(EventDB.timestamp) == today)
        .group_by(EventDB.zone_id)
    )
    avg_dwell = {row[0]: round(row[1] / 1000, 1) for row in dwell_result.fetchall()}

    queue_result = await db.execute(
        select(EventDB.metadata_)
        .where(EventDB.store_id == store_id)
        .where(EventDB.event_type == "BILLING_QUEUE_JOIN")
        .order_by(EventDB.timestamp.desc())
        .limit(1)
    )
    queue_row = queue_result.scalar()
    queue_depth = queue_row.get("queue_depth", 0) if queue_row else 0

    abandon_result = await db.execute(
        select(func.count())
        .where(EventDB.store_id == store_id)
        .where(EventDB.event_type == "BILLING_QUEUE_ABANDON")
        .where(func.date(EventDB.timestamp) == today)
    )
    abandonments = abandon_result.scalar() or 0
    abandonment_rate = round(abandonments / billing_visitors, 3) if billing_visitors > 0 else 0.0

    return {
        "store_id": store_id,
        "date": str(today),
        "unique_visitors": unique_visitors,
        "conversion_rate": conversion_rate,
        "avg_dwell_seconds_per_zone": avg_dwell,
        "queue_depth": queue_depth,
        "abandonment_rate": abandonment_rate
    }
