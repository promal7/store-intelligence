from pydantic import BaseModel
from typing import List, Optional

class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: Optional[int] = None

class BehavioralEvent(BaseModel):
    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: str
    zone_id: Optional[str] = None
    dwell_ms: int
    is_staff: bool
    confidence: float
    metadata: EventMetadata

class EventIngestPayload(BaseModel):
    events: List[BehavioralEvent]

class POSRecord(BaseModel):
    store_id: str
    transaction_id: str
    timestamp: str
    basket_value_inr: float
