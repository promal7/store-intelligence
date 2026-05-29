# PROMPT: Generate pytest-asyncio integration tests for a FastAPI store intelligence application. Cover event array ingest processing, metrics assertions, and funnel analytics endpoints using AsyncClient.
# CHANGES MADE: Swapped base AsyncClient parameter signatures from url to base_url and bound the FastAPI app instance directly to enable fast, zero-dependency in-memory testing.

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
import uuid
from app.main import app

@pytest.mark.asyncio
async def test_health_and_ingestion():
    async with AsyncClient(app=app, base_url='http://test') as client:
        event_id = str(uuid.uuid4())
        payload = {
            'events': [
                {
                    'event_id': event_id,
                    'store_id': 'STORE_BLR_002',
                    'camera_id': 'CAM_ENT_01',
                    'visitor_id': 'VIS_TEST_99',
                    'event_type': 'BILLING_QUEUE_JOIN',
                    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    'zone_id': 'BILLING_QUEUE_JOIN',
                    'dwell_ms': 4500,
                    'is_staff': False,
                    'confidence': 0.95,
                    'metadata': {'queue_depth': 4}
                }
            ]
        }
        response = await client.post('/events/ingest', json=payload)
        assert response.status_code == 200
        assert response.json()['status'] == 'accepted'

@pytest.mark.asyncio
async def test_metrics_calculation_logic():
    async with AsyncClient(app=app, base_url='http://test') as client:
        response = await client.get('/stores/STORE_BLR_002/metrics')
        assert response.status_code == 200
        data = response.json()
        assert 'conversion_rate' in data
        assert 'abandonment_rate' in data
        assert 'data_confidence' in data

@pytest.mark.asyncio
async def test_funnel_and_anomalies_endpoints():
    async with AsyncClient(app=app, base_url='http://test') as client:
        funnel_res = await client.get('/stores/STORE_BLR_002/funnel')
        assert funnel_res.status_code == 200
        assert 'stages' in funnel_res.json()

        heatmap_res = await client.get('/stores/STORE_BLR_002/heatmap')
        assert heatmap_res.status_code == 200
        assert 'zones' in heatmap_res.json()

        health_res = await client.get('/health')
        assert health_res.status_code == 200
        assert 'status' in health_res.json()
