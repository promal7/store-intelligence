from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import EventDB
from datetime import date

router = APIRouter()

@router.get("/stores/{store_id}/heatmap")
async def get_heatmap(store_id: str, db: AsyncSession = Depends(get_db)):
    today = date.today()

    result = await db.execute(
        select(
            EventDB.zone_id,
            func.count(func.distinct(EventDB.visitor_id)).label("visit_count"),
            func.avg(EventDB.dwell_ms).label("avg_dwell_ms")
        )
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.zone_id != None)
        .where(EventDB.event_type.in_(["ZONE_ENTER", "ZONE_DWELL"]))
        .where(func.date(EventDB.timestamp) == today)
        .group_by(EventDB.zone_id)
    )
    rows = result.fetchall()

    if not rows:
        return {
            "store_id": store_id,
            "date": str(today),
            "data_confidence": "LOW",
            "zones": []
        }

    max_visits = max(r.visit_count for r in rows)
    total_sessions = sum(r.visit_count for r in rows)

    zones = []
    for row in rows:
        normalised = round((row.visit_count / max_visits) * 100) if max_visits > 0 else 0
        zones.append({
            "zone_id": row.zone_id,
            "visit_count": row.visit_count,
            "avg_dwell_seconds": round((row.avg_dwell_ms or 0) / 1000, 1),
            "normalised_score": normalised
        })

    zones.sort(key=lambda x: x["normalised_score"], reverse=True)

    return {
        "store_id": store_id,
        "date": str(today),
        "data_confidence": "LOW" if total_sessions < 20 else "HIGH",
        "zones": zones
    }
