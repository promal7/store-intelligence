from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Event, EventDB, IngestRequest, IngestResponse, VALID_EVENT_TYPES

router = APIRouter()

@router.post("/events/ingest", response_model=IngestResponse)
async def ingest_events(payload: IngestRequest, db: AsyncSession = Depends(get_db)):
    accepted = 0
    rejected = 0
    duplicate = 0
    errors = []

    for event in payload.events:
        if event.event_type not in VALID_EVENT_TYPES:
            rejected += 1
            errors.append({"event_id": event.event_id, "error": f"Invalid event_type: {event.event_type}"})
            continue

        existing = await db.get(EventDB, event.event_id)
        if existing:
            duplicate += 1
            continue

        db_event = EventDB(
            event_id   = event.event_id,
            store_id   = event.store_id,
            camera_id  = event.camera_id,
            visitor_id = event.visitor_id,
            event_type = event.event_type,
            timestamp  = event.timestamp,
            zone_id    = event.zone_id,
            dwell_ms   = event.dwell_ms,
            is_staff   = event.is_staff,
            confidence = event.confidence,
            metadata_  = event.metadata.model_dump() if event.metadata else None
        )
        db.add(db_event)
        accepted += 1

    await db.commit()
    return IngestResponse(accepted=accepted, rejected=rejected, duplicate=duplicate, errors=errors)
