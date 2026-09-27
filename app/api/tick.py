"""POST /v1/tick endpoint."""

from fastapi import APIRouter
from app.engagement.router import trigger_router
from app.models.requests import TickRequest
from app.models.responses import TickResponse

router = APIRouter()


@router.post("/v1/tick", response_model=TickResponse)
async def tick(req: TickRequest):
    # Route available triggers through deterministic policies and suppression
    actions = trigger_router.route_triggers(
        available_trigger_ids=req.available_triggers,
        now_iso=req.now,
    )
    return TickResponse(actions=actions)
