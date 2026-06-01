from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime, JSON
from app.database import Base
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class EventDB(Base):
    __tablename__ = "events"

    event_id   = Column(String, primary_key=True, index=True)
    store_id   = Column(String, index=True, nullable=False)
    camera_id  = Column(String, nullable=False)
    visitor_id = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    timestamp  = Column(DateTime, index=True, nullable=False)
    zone_id    = Column(String, nullable=True)
    dwell_ms   = Column(Integer, default=0)
    is_staff   = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)
    metadata_  = Column("metadata", JSON, nullable=True)

class EventMetadata(BaseModel):
    queue_depth : Optional[int] = None
    sku_zone    : Optional[str] = None
    session_seq : Optional[int] = None

class Event(BaseModel):
    event_id   : str           = Field(default_factory=lambda: str(uuid.uuid4()))
    store_id   : str
    camera_id  : str
    visitor_id : str
    event_type : str
    timestamp  : datetime
    zone_id    : Optional[str] = None
    dwell_ms   : int           = 0
    is_staff   : bool          = False
    confidence : float         = 1.0
    metadata   : Optional[EventMetadata] = None

    class Config:
        from_attributes = True

VALID_EVENT_TYPES = {
    "ENTRY", "EXIT", "ZONE_ENTER", "ZONE_EXIT",
    "ZONE_DWELL", "BILLING_QUEUE_JOIN",
    "BILLING_QUEUE_ABANDON", "REENTRY"
}

class IngestRequest(BaseModel):
    events: list[Event] = Field(..., max_length=500)

class IngestResponse(BaseModel):
    accepted  : int
    rejected  : int
    duplicate : int
    errors    : list[dict] = []
