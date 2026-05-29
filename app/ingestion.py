from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import IngestRequest, IngestResponse, EventDB, POSTransaction, POSTransactionDB
from pydantic import BaseModel

router = APIRouter(tags=['Ingestion'])

class POSIngestRequest(BaseModel):
    transactions: list[POSTransaction]

@router.post('/events/ingest', response_model=IngestResponse)
async def ingest_events(payload: IngestRequest, db: AsyncSession = Depends(get_db)):
    accepted, rejected, duplicate = 0, 0, 0
    errors = []
    
    for event in payload.events:
        try:
            stmt = select(EventDB).where(EventDB.event_id == event.event_id)
            result = await db.execute(stmt)
            if result.scalar_one_or_none():
                duplicate += 1
                continue
            
            db_event = EventDB(
                event_id=event.event_id,
                store_id=event.store_id,
                camera_id=event.camera_id,
                visitor_id=event.visitor_id,
                event_type=event.event_type,
                timestamp=event.timestamp,
                zone_id=event.zone_id,
                dwell_ms=event.dwell_ms,
                is_staff=event.is_staff,
                confidence=event.confidence,
                metadata_=event.metadata.dict() if event.metadata else None
            )
            db.add(db_event)
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append({'event_id': event.event_id, 'error': str(e)})
            
    if accepted > 0:
        await db.commit()
        
    return IngestResponse(accepted=accepted, rejected=rejected, duplicate=duplicate, errors=errors)

@router.post('/pos/ingest')
async def ingest_pos(payload: POSIngestRequest, db: AsyncSession = Depends(get_db)):
    accepted = 0
    for txn in payload.transactions:
        stmt = select(POSTransactionDB).where(POSTransactionDB.transaction_id == txn.transaction_id)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            continue
        db_txn = POSTransactionDB(
            transaction_id=txn.transaction_id,
            store_id=txn.store_id,
            timestamp=txn.timestamp,
            basket_value_inr=txn.basket_value_inr
        )
        db.add(db_txn)
        accepted += 1
    if accepted > 0:
        await db.commit()
    return {'status': 'ok', 'accepted': accepted}
