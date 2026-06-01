# Engineering Choices & Trade-offs - Apex Retail Store Intelligence
This document details the architectural decisions, trade-off justifications, and mitigation strategies implemented to solve the Store Intelligence challenge.

## 1. Architectural Strategy: Edge vs. Cloud Trade-off
- **Decision:** Heavy computer vision models (YOLOv8 inference) run locally at the Edge store node; analytics aggregation runs in the Cloud backend.
- **Justification:** Streaming raw multi-channel CCTV video frames to a cloud server consumes enormous network bandwidth, increases latency, and incurs exorbitant cloud GPU costs. Processing at the edge allows the system to compress rich environmental video signals into small, structured text-based JSON payloads (under 1 KB per event).
- **Trade-off:** Edge devices are resource-constrained and vulnerable to local hardware/network dropouts. This was mitigated by introducing a robust cloud-side health watchdog.

## 2. Framework Choice: FastAPI vs. Django/Flask
- **Decision:** Selected FastAPI as the primary API core tier.
- **Justification:** The cloud backend must process heavy concurrent event spikes from multiple edge-ingestion streams. FastAPI uses asynchronous ASGI protocols (`async/await`) out of the box, outperforming traditional synchronous frameworks like Flask or Django under high network concurrency. It natively implements structural data checking via Pydantic, enforcing contract validation before records hit storage.

## 3. Storage Architecture: SQLite with SQLAlchemy ORM
- **Decision:** Utilized SQLite as the initial relational datastore backed by SQLAlchemy abstractions.
- **Justification:** For single-store tracking operations, introducing bloated database architectures like PostgreSQL or MongoDB adds unnecessary deployment complexity and deployment overhead. SQLite operates with negligible footprint, fast read/write capabilities, and files directly on system disk, ensuring compliance with the zero-manual-intervention requirements for basic setup.

## 4. Handling Real-World Edge Cases

### A. Metric Inflation via Re-entry & Occlusion
- **Problem:** If a customer walks behind a store structural pillar or is temporarily blocked from a camera's line-of-sight, standard object detectors lose track and assign a completely new ID when they reappear, corrupting the conversion rate metrics.
- **Solution:** Implemented a temporal-spatial coordinate buffer within `tracker.py`. If a lost tracking profile reappears within a localized radius and a 5-second window, the pipeline merges the entity path instead of re-registering an account event.

### B. Staff Movement Contamination
- **Problem:** Store employees move back and forth continuously across the retail floor, heavily inflating conversion funnel statistics if unhandled.
- **Solution:** Applied a behavioral velocity filter within `filters.py`. Staff paths are filtered out programmatically based on prolonged dwell vectors, recurrence frequency across specified areas, and custom zone interaction profiles to ensure true customer conversion calculations.

### C. Live Stream Failure Protection
- **Problem:** Camera components face physical disconnections or streaming crashes in production.
- **Solution:** Built an internal cron-watchdog monitoring thread inside the ingestion layer. If incoming payload traffic updates for a registered camera cross a 10-minute timeout boundary, the server flags the channel status explicitly as `STALE_FEED` rather than silently failing, facilitating immediate visibility.