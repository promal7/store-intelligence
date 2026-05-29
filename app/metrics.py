from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.database import get_db
from app.models import EventDB, POSTransactionDB
from datetime import datetime, timedelta

router = APIRouter(prefix='/stores/{store_id}', tags=['Metrics'])

@router.get('/metrics')
async def get_store_metrics(store_id: str, db: AsyncSession = Depends(get_db)):
    # 1. Fetch raw matrix structures cleanly via scalar lists
    events_stmt = select(EventDB).where(EventDB.store_id == store_id, EventDB.is_staff == False)
    events_res = await db.execute(events_stmt)
    all_events = list(events_res.scalars().all())
    
    pos_stmt = select(POSTransactionDB).where(POSTransactionDB.store_id == store_id)
    pos_res = await db.execute(pos_stmt)
    all_txns = list(pos_res.scalars().all())

    # Build memory-safe dictionaries to avoid lazy loading issues
    sessions = {}
    total_queue_joins = 0
    current_depth = 0
    
    for ev in all_events:
        v_id = ev.visitor_id
        if v_id not in sessions:
            sessions[v_id] = []
        sessions[v_id].append({
            'type': ev.event_type,
            'time': ev.timestamp,
            'meta': ev.metadata_ or {}
        })

    unique_visitors = len(sessions)
    converted_visitors = set()
    queue_abandonments = 0

    for v_id, ev_list in sessions.items():
        has_joined_queue = False
        ev_list.sort(key=lambda x: x['time'])
        
        for ev in ev_list:
            if ev['type'] == 'BILLING_QUEUE_JOIN':
                has_joined_queue = True
                total_queue_joins += 1
                current_depth = max(current_depth, ev['meta'].get('queue_depth', 1) or 1)
            
            # Check transaction pairing window
            for txn in all_txns:
                time_diff = (txn.timestamp - ev['time']).total_seconds()
                if has_joined_queue and 0 <= time_diff <= 300: # 5 minute window
                    converted_visitors.add(v_id)
                    
        if has_joined_queue and v_id not in converted_visitors:
            queue_abandonments += 1

    conversion_rate = 0.0
    if unique_visitors > 0:
        conversion_rate = round((len(converted_visitors) / unique_visitors) * 100, 2)
        
    abandonment_rate = 0.0
    if total_queue_joins > 0:
        abandonment_rate = round((queue_abandonments / total_queue_joins) * 100, 2)

    # 2. Extract Dwell averages safely
    dwell_stmt = select(EventDB.zone_id, func.avg(EventDB.dwell_ms)).where(
        EventDB.store_id == store_id, EventDB.is_staff == False, EventDB.zone_id.isnot(None)
    ).group_by(EventDB.zone_id)
    dwell_res = await db.execute(dwell_stmt)
    avg_dwell_per_zone = {str(row[0]): round(float(row[1]), 2) for row in dwell_res.all()}
    
    return {
        'store_id': store_id,
        'unique_visitors': unique_visitors,
        'conversion_rate': conversion_rate,
        'avg_dwell_per_zone': avg_dwell_per_zone,
        'current_queue_depth': int(current_depth) if unique_visitors > 0 else 0,
        'abandonment_rate': abandonment_rate
    }

@router.get('/heatmap')
async def get_store_heatmap(store_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(EventDB.zone_id, func.count(EventDB.event_id)).where(
        EventDB.store_id == store_id, EventDB.is_staff == False, EventDB.zone_id.isnot(None)
    ).group_by(EventDB.zone_id)
    res = await db.execute(stmt)
    
    raw_counts = {str(row[0]): int(row[1]) for row in res.all()}
    max_val = max(raw_counts.values()) if raw_counts else 1
    normalized_heatmap = {zone: round((count / max_val) * 100, 1) for zone, count in raw_counts.items()}
    
    sess_stmt = select(func.count(func.distinct(EventDB.visitor_id))).where(EventDB.store_id == store_id)
    sess_res = await db.execute(sess_stmt)
    session_count = sess_res.scalar() or 0
    
    return {
        'store_id': store_id,
        'data_confidence': 'HIGH' if session_count >= 20 else 'LOW',
        'heatmap': normalized_heatmap
    }
