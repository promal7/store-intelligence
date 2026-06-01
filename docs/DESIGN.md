# System Design — Store Intelligence API

## Architecture Overview

The system is a five-stage pipeline that transforms raw CCTV footage into live retail analytics:

1. **Detection Layer** — YOLOv8 processes video frames to detect and track people. ByteTrack assigns persistent IDs across frames. A Re-ID module handles re-entry detection by comparing appearance embeddings.

2. **Event Stream** — The detection layer emits structured JSONL events (ENTRY, EXIT, ZONE_DWELL, etc.) with visitor tokens, timestamps, and confidence scores.

3. **Intelligence API** — A FastAPI application ingests events, stores them in SQLite, and exposes queryable endpoints for metrics, funnel, heatmap, and anomaly detection.

4. **Live Dashboard** — A terminal dashboard polls the API every 5 seconds and displays real-time store metrics.

## Technology Choices

- **FastAPI** — Async support, automatic OpenAPI docs, Pydantic validation out of the box
- **SQLAlchemy + SQLite** — Zero-ops database sufficient for this scale; easily swappable to PostgreSQL
- **YOLOv8** — Pretrained model with ByteTrack built in, strong community support
- **Docker** — Single `docker compose up` starts everything

## Data Flow

