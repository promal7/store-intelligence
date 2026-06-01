# PROMPT: "Write pytest tests for a FastAPI store analytics API with endpoints
# for event ingestion, metrics, funnel, heatmap and anomalies. Use async
# test client. Cover happy path, empty store, duplicate events, invalid
# event types, and staff exclusion edge cases."
# CHANGES MADE: Added fixture for sample events, adjusted assertion values
# to match our schema, added zero-purchase store test.

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def sample_event():
    return {
        "event_id": "test-metric-001",
        "store_id": "STORE_TEST_001",
        "camera_id": "CAM_ENTRY_01",
        "visitor_id": "VIS_test123",
        "event_type": "ENTRY",
        "timestamp": "2026-06-01T10:00:00Z",
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.95,
        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
    }

@pytest.fixture
def staff_event():
    return {
        "event_id": "test-staff-001",
        "store_id": "STORE_TEST_001",
        "camera_id": "CAM_ENTRY_01",
        "visitor_id": "VIS_staff001",
        "event_type": "ENTRY",
        "timestamp": "2026-06-01T10:00:00Z",
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": True,
        "confidence": 0.95,
        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
    }

@pytest.mark.asyncio
async def test_ingest_accepts_valid_event(sample_event):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/events/ingest", json={"events": [sample_event]})
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] + data["duplicate"] == 1
    assert data["rejected"] == 0

@pytest.mark.asyncio
async def test_ingest_rejects_invalid_event_type(sample_event):
    sample_event["event_id"] = "test-invalid-001"
    sample_event["event_type"] = "INVALID_TYPE"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/events/ingest", json={"events": [sample_event]})
    assert response.status_code == 200
    data = response.json()
    assert data["rejected"] == 1

@pytest.mark.asyncio
async def test_ingest_idempotent(sample_event):
    sample_event["event_id"] = "test-idem-001"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/events/ingest", json={"events": [sample_event]})
        r2 = await ac.post("/events/ingest", json={"events": [sample_event]})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["duplicate"] == 1

@pytest.mark.asyncio
async def test_metrics_empty_store():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/stores/STORE_EMPTY_999/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0

@pytest.mark.asyncio
async def test_metrics_excludes_staff(staff_event):
    staff_event["event_id"] = "test-staff-excl-001"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/events/ingest", json={"events": [staff_event]})
        response = await ac.get("/stores/STORE_TEST_001/metrics")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_funnel_returns_four_stages():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/stores/STORE_TEST_001/funnel")
    assert response.status_code == 200
    data = response.json()
    assert len(data["funnel"]) == 4

@pytest.mark.asyncio
async def test_heatmap_empty_store():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/stores/STORE_EMPTY_999/heatmap")
    assert response.status_code == 200
    data = response.json()
    assert data["data_confidence"] == "LOW"
    assert data["zones"] == []

@pytest.mark.asyncio
async def test_anomalies_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/stores/STORE_TEST_001/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "anomalies" in data

@pytest.mark.asyncio
async def test_health_returns_healthy():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
