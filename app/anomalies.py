from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import EventDB
from datetime import datetime, timedelta, date

router = APIRouter()

@router.get("/stores/{store_id}/anomalies")
async def get_anomalies(store_id: str, db: AsyncSession = Depends(get_db)):
    anomalies = []
    now = datetime.utcnow()
    window_30m = now - timedelta(minutes=30)

    # 1. Queue spike
    queue_result = await db.execute(
        select(EventDB.metadata_)
        .where(EventDB.store_id == store_id)
        .where(EventDB.event_type == "BILLING_QUEUE_JOIN")
        .where(EventDB.timestamp >= window_30m)
        .order_by(EventDB.timestamp.desc())
        .limit(1)
    )
    queue_row = queue_result.scalar()
    if queue_row and queue_row.get("queue_depth", 0) > 5:
        anomalies.append({
            "type": "BILLING_QUEUE_SPIKE",
            "severity": "CRITICAL",
            "message": f"Queue depth is {queue_row['queue_depth']}",
            "suggested_action": "Open additional billing counter immediately"
        })

    # 2. Dead zone
    zone_result = await db.execute(
        select(func.count())
        .where(EventDB.store_id == store_id)
        .where(EventDB.event_type.in_(["ZONE_ENTER", "ZONE_DWELL"]))
        .where(EventDB.timestamp >= window_30m)
    )
    zone_count = zone_result.scalar() or 0
    if zone_count == 0:
        anomalies.append({
            "type": "DEAD_ZONE",
            "severity": "WARN",
            "message": "No zone activity in last 30 minutes",
            "suggested_action": "Check camera feed and store traffic"
        })

    # 3. Conversion drop
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
        .where(EventDB.event_type == "BILLING_QUEUE_JOIN")
        .where(func.date(EventDB.timestamp) == today)
    )
    billing_visitors = billing_result.scalar() or 0
    conversion = billing_visitors / unique_visitors if unique_visitors > 0 else 0

    if unique_visitors > 10 and conversion < 0.05:
        anomalies.append({
            "type": "CONVERSION_DROP",
            "severity": "WARN",
            "message": f"Conversion rate is {round(conversion*100,1)}% — below 5% threshold",
            "suggested_action": "Review floor staff positioning and promotions"
        })

    return {"store_id": store_id, "anomalies": anomalies}
