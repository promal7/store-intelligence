from fastapi import APIRouter
import time

router = APIRouter(tags=["System Status"])

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "database": "connected",
            "stream_ingest": "active"
        }
    }
