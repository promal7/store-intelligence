from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import EventDB
from datetime import date

router = APIRouter()

@router.get("/stores/{store_id}/funnel")
async def get_funnel(store_id: str, db: AsyncSession = Depends(get_db)):
    today = date.today()

    entries_result = await db.execute(
        select(func.count(func.distinct(EventDB.visitor_id)))
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type.in_(["ENTRY", "REENTRY"]))
        .where(func.date(EventDB.timestamp) == today)
    )
    entries = entries_result.scalar() or 0

    zone_result = await db.execute(
        select(func.count(func.distinct(EventDB.visitor_id)))
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type.in_(["ZONE_ENTER", "ZONE_DWELL"]))
        .where(func.date(EventDB.timestamp) == today)
    )
    zone_visits = zone_result.scalar() or 0

    billing_result = await db.execute(
        select(func.count(func.distinct(EventDB.visitor_id)))
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type == "BILLING_QUEUE_JOIN")
        .where(func.date(EventDB.timestamp) == today)
    )
    billing_queue = billing_result.scalar() or 0

    abandon_result = await db.execute(
        select(func.count(func.distinct(EventDB.visitor_id)))
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type == "BILLING_QUEUE_ABANDON")
        .where(func.date(EventDB.timestamp) == today)
    )
    abandonments = abandon_result.scalar() or 0
    purchases = billing_queue - abandonments

    def drop(a, b):
        return round((1 - b / a) * 100, 1) if a > 0 else 0.0

    return {
        "store_id": store_id,
        "date": str(today),
        "funnel": [
            {"stage": "Entry",         "visitors": entries,       "drop_off_pct": 0},
            {"stage": "Zone Visit",    "visitors": zone_visits,   "drop_off_pct": drop(entries, zone_visits)},
            {"stage": "Billing Queue", "visitors": billing_queue, "drop_off_pct": drop(zone_visits, billing_queue)},
            {"stage": "Purchase",      "visitors": purchases,     "drop_off_pct": drop(billing_queue, purchases)},
        ]
    }
