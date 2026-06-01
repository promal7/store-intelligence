# Store Intelligence API

A real-time retail analytics system that processes CCTV footage to deliver live store metrics for Apex Retail.

## Setup (5 commands)

```bash
git clone <your-repo-url>
cd store-intelligence
cp .env.example .env
docker compose up --build
```

API will be available at: http://localhost:8000
Interactive docs at: http://localhost:8000/docs

## Running the Detection Pipeline

```bash
source .venv/bin/activate
python pipeline/detect.py --input data/clips/ --output data/events/events.jsonl
```

Then ingest the events:
```bash
python pipeline/emit.py --events data/events/events.jsonl
```

## API Endpoints

| Endpoint | Description |
|---|---|
| POST /events/ingest | Ingest up to 500 events per batch |
| GET /stores/{id}/metrics | Live store metrics |
| GET /stores/{id}/funnel | Conversion funnel |
| GET /stores/{id}/heatmap | Zone heatmap |
| GET /stores/{id}/anomalies | Active anomalies |
| GET /health | Service health status |

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ --cov=app --cov-report=term-missing
```

## Dashboard

```bash
source .venv/bin/activate
python pipeline/dashboard.py
```
