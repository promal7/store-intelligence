# System Architecture Design - Apex Retail Store Intelligence

This document outlines the end-to-end architectural layout of the Apex Retail Store Intelligence System, built under an Edge-to-Cloud paradigm to compute real-time retail analytics under network and resource constraints.

+-----------------------------------------------------------------------------------+
|                                  LOCAL STORE (EDGE)                               |
|                                                                                   |
|  +------------------+      +---------------------+      +----------------------+  |
|  | Raw CCTV Feed    | ---> |  Inference Engine   | ---> |  Trajectory Tracker  |  |
|  | (OpenCV Stream)  |      |  (YOLOv8 Object Det)|      |  (Re-entry Handling) |  |
|  +------------------+      +---------------------+      +----------------------+  |
|                                                                    |              |
|                                                                    v              |
|                                                         +----------------------+  |
|                                                         |  Stream Manager      |  |
|                                                         |  (JSON Event Post)   |  |
|                                                         +----------------------+  |
+--------------------------------------------------------------------+--------------+
|
HTTPS Payload | (Structured Events)
v
+-----------------------------------------------------------------------------------+
|                                  CLOUD CENTRAL BACKEND                            |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                                  FastAPI ASGI Server                        |  |
|  |                                                                             |  |
|  |  +-----------------------+     +-------------------+     +---------------+  |  |
|  |  | Telemetry Ingestion   |     | Analytics Router  |     | Anomaly Engine|  |  |
|  |  | /metrics              |     | /funnel           |     | Watchdog      |  |  |
|  |  +-----------------------+     +-------------------+     +---------------+  |  |
|  +----------------------+-------------------+-----------------------+----------+  |
|                         |                   |                       |             |
|                         v                   v                       v             |
|                  +------------+      +------------+          +-------------+      |
|                  | Staff      |      | Sessioned  |          | STALE_FEED  |      |
|                  | Filtering  |      | Storage    |          | Alert Log   |      |
|                  +------------+      +------------+          +-------------+      |
|                         |                   |                                     |
|                         +---------+---------+                                     |
|                                   |                                               |
|                                   v                                               |
|                        +---------------------+                                    |
|                        | SQLite DB           |                                    |
|                        | (SQLAlchemy Core)   |                                    |
|                        +---------------------+                                    |
+-----------------------------------------------------------------------------------+

## 2. Component Pipeline Breakdown

### A. Edge Detection & Localization Node
- **`inference.py`**: Intercepts local CCTV network video streams frame-by-frame via OpenCV and feeds them into a highly optimized localized YOLOv8 model for real-time person detection.
- **`tracker.py`**: Map-tracks sequential cross-frame bounding boxes. It implements an algorithmic spatial-temporal boundary window to handle re-entry detection and short-term occlusions, avoiding double-counting tracking profiles.
- **`stream_manager.py`**: Batches and fires off micro-structured JSON schema event logs into the cloud gateway over async HTTP client post protocols.

### B. High-Throughput Central Cloud Gateway
- **`main.py` & `endpoints.py` (FastAPI)**: Serves as an asynchronous non-blocking ingestion backend. Offers a dedicated `/metrics` endpoint to absorb incoming telemetry signals and a `/funnel` engine to compute traffic drop-off matrices cleanly.
- **`filters.py`**: Isolates staff behavioral telemetry (recurrent baseline routes, specialized movement velocities) to isolate actual customer footfall behaviors.
- **Database Layer (`database.py`)**: Persists state metrics utilizing SQLAlchemy abstractions on top of a highly optimized SQLite implementation structured with transaction isolation.
- **Health Watchdog Framework**: Evaluates transaction timelines dynamically. Fires a sliding time window monitor that raises an operational `STALE_FEED` alert status if an ingestion socket remains mute for over 10 minutes continuously.