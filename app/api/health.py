"""GET /v1/healthz endpoint."""

import time
from fastapi import APIRouter
from app.models.responses import HealthResponse
from app.state.context_store import context_store

router = APIRouter()
START_TIME = time.time()


@router.get("/v1/healthz", response_model=HealthResponse)
async def healthz():
    uptime = int(time.time() - START_TIME)
    counts = context_store.counts()
    return HealthResponse(
        status="ok",
        uptime_seconds=uptime,
        contexts_loaded=counts,
    )
