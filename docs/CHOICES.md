# Architecture Choices

## Decision 1 — Detection Model: YOLOv8

### Options Considered
- YOLOv8 (Ultralytics)
- RT-DETR (Transformer-based)
- MediaPipe (lightweight, mobile-first)

### What AI Suggested
Claude suggested YOLOv8 as the starting point due to its built-in ByteTrack integration, strong pretrained weights on COCO dataset, and large community support. It noted RT-DETR would be more accurate but harder to integrate with tracking.

### What I Chose and Why
YOLOv8 with ByteTrack. The built-in tracking support meant I didn't need to integrate a separate tracking library. The pretrained model handles person detection without any fine-tuning. For a hackathon timeline this was the right tradeoff — accuracy vs speed of implementation.

For production, I would evaluate RT-DETR on the actual footage and run an A/B test on detection accuracy.

## Decision 2 — Event Schema Design

### Options Considered
- Flat schema with all fields on every event
- Typed schema with different fields per event type
- Minimal schema with a generic `payload` JSON blob

### What AI Suggested
Claude suggested a flat schema with a `metadata` JSON field for event-type-specific data (like `queue_depth` for BILLING_QUEUE_JOIN). This keeps the core schema simple while allowing flexibility for event-specific data.

### What I Chose and Why
I adopted the flat schema with metadata JSON. This made database queries simpler — filtering by `event_type` and `store_id` is straightforward with standard SQL. The `metadata` field handles edge cases without requiring schema migrations.

The tradeoff is that `metadata` is not strongly typed at the database level. In production I would add a JSON schema validator at ingest time.

## Decision 3 — API Storage Engine

### Options Considered
- SQLite with SQLAlchemy async
- PostgreSQL with asyncpg
- In-memory dictionary store

### What AI Suggested
Claude suggested SQLite for development and PostgreSQL for production, with SQLAlchemy as the ORM so switching is a one-line config change. It warned against in-memory storage because it loses data on restart and cannot support the idempotency requirement.

### What I Chose and Why
SQLite with aiosqlite for async support. For this challenge scale (5 stores, batch events) SQLite is sufficient and requires zero infrastructure setup. The DATABASE_URL environment variable means switching to PostgreSQL in production requires only a config change — no code changes needed.
