from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import EventDB

router = APIRouter(prefix="/stores/{store_id}", tags=["Funnel"])

@router.get("/funnel")
async def get_store_funnel(store_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(EventDB.visitor_id, EventDB.event_type).where(
        EventDB.store_id == store_id, EventDB.is_staff == False
    )
    res = await db.execute(stmt)
    
    sessions = {}
    for vis_id, ev_type in res.all():
        if vis_id not in sessions:
            sessions[vis_id] = set()
        sessions[vis_id].add(ev_type)
        
    total_sessions = len(sessions)
    zone_visits = sum(1 for s in sessions.values() if "ZONE_ENTER" in s or "ZONE_DWELL" in s)
    queue_joins = sum(1 for s in sessions.values() if "BILLING_QUEUE_JOIN" in s)
    
    return {
        "store_id": store_id,
        "stages": [
            {"stage": "1_ENTRY", "count": total_sessions, "dropoff_pct": 0.0},
            {"stage": "2_ZONE_VISIT", "count": zone_visits, "dropoff_pct": round((1 - zone_visits/max(1, total_sessions))*100, 1)},
            {"stage": "3_BILLING_QUEUE", "count": queue_joins, "dropoff_pct": round((1 - queue_joins/max(1, zone_visits))*100, 1)}
        ]
    }
