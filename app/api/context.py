"""POST /v1/context endpoint."""

from fastapi import APIRouter, HTTPException, status
from app.models.requests import ContextPushRequest
from app.models.responses import ContextPushResponse
from app.state.context_store import StaleVersionError, context_store

router = APIRouter()


@router.post("/v1/context", response_model=ContextPushResponse)
async def push_context(req: ContextPushRequest):
    try:
        is_updated, ack_id, stored_at = context_store.put(
            scope=req.scope,
            context_id=req.context_id,
            version=req.version,
            payload=req.payload,
        )
        return ContextPushResponse(
            accepted=True,
            ack_id=ack_id,
            stored_at=stored_at,
        )
    except StaleVersionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "accepted": False,
                "reason": "stale_version",
                "current_version": e.current_version,
            },
        )
