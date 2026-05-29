# CHOICES.md - Engineering Trade-Offs & Decisions

## 1. Detection Model Selection & Trade-Offs
* **Options Considered:** YOLOv8n (Nano), YOLOv8m (Medium), and RT-DETR.
* **AI Recommendation:** The assistant suggested utilizing a mid-tier YOLOv8m weight configuration to ensure highly stable detection parameters across occluded retail spaces.
* **Final Choice & Justification:** YOLOv8n was chosen for the edge loop. Testing revealed that while the medium weight layout increases raw inference frame metrics slightly, its computational footprint degrades frames-per-second processing heavily when deployed on baseline CPU infrastructure. YOLOv8n maintains high frame execution rates, and downstream software tracking filters compensate for transient bounding box occlusions.

## 2. Event Schema Design Rationale
* **Options Considered:** Flat transactional indexing records vs Hierarchical nested state tracking documents.
* **AI Recommendation:** Suggested a highly dynamic, variable-length nested dictionary pattern for handling custom camera telemetry updates.
* **Final Choice & Justification:** A concrete flat behavioral payload template was chosen. It contains explicit indexing attributes for store tracking identifiers, uniform session sequence tracking keys, and staff exclusion flags. This approach guarantees strict compliance with analytical mapping constraints, speeds up relational filtering passes inside the SQLite architecture, and eliminates query translation overhead.

## 3. API Storage Architecture Choice
* **Options Considered:** In-memory Redis cache pools vs Relational SQLite engines.
* **AI Recommendation:** Recommended a temporary Redis structures cache to manage shifting real-time analytics window values.
* **Final Choice & Justification:** An asynchronous SQLAlchemy abstraction layer routing to an isolated SQLite file block was chosen. This entirely isolates database operations from system RAM volatile losses. It also avoids external container network dependencies during evaluation, fulfilling the core goal of zero deployment friction.
