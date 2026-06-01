import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import init_db
from app.ingestion import router as ingest_router
from app.metrics   import router as metrics_router
from app.funnel    import router as funnel_router
from app.anomalies import router as anomalies_router
from app.health    import router as health_router
from app.heatmap   import router as heatmap_router

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialised")
    yield
    logger.info("Shutting down")

app = FastAPI(
    title="Store Intelligence API",
    version="1.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = str(uuid.uuid4())[:8]
    store_id = request.path_params.get("store_id", "-")
    start    = time.time()
    request.state.trace_id = trace_id
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"trace_id={trace_id} unhandled error: {exc}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
    latency = int((time.time() - start) * 1000)
    logger.info(
        f"trace_id={trace_id} store_id={store_id} "
        f"method={request.method} path={request.url.path} "
        f"status={response.status_code} latency_ms={latency}"
    )
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=503,
        content={"error": "Service temporarily unavailable", "detail": str(exc)}
    )

app.include_router(ingest_router)
app.include_router(metrics_router)
app.include_router(funnel_router)
app.include_router(anomalies_router)
app.include_router(health_router)
app.include_router(heatmap_router)

@app.get("/")
async def root():
    return {"status": "ok", "service": "Store Intelligence API"}
