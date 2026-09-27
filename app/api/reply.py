"""POST /v1/reply endpoint."""

from fastapi import APIRouter
from app.models.conversation import IntentEnum
from app.models.requests import ReplyRequest
from app.models.responses import ReplyResponse
from app.state.conversation_store import conversation_store

router = APIRouter()


@router.post("/v1/reply", response_model=ReplyResponse)
async def reply(req: ReplyRequest):
    # Record incoming turn and update conversation and merchant interaction states
    conv, mx_state = conversation_store.record_incoming_turn(
        conversation_id=req.conversation_id,
        merchant_id=req.merchant_id,
        message=req.message,
        turn_number=req.turn_number,
        from_role=req.from_role,
        customer_id=req.customer_id,
    )

    # Initial deterministic classification baseline for Phase 1
    # Full multi-turn intent policy will be enriched in Phase 3
    msg_lower = req.message.lower().strip()

    if "stop" in msg_lower or "unsubscribe" in msg_lower:
        conv.detected_intent = IntentEnum.STOP
        conv.ended = True
        mx_state.unsubscribed = True
        return ReplyResponse(
            action="end",
            rationale="Opt-out requested by user. Ended conversation gracefully.",
        )

    # Return baseline acknowledge turn
    return ReplyResponse(
        action="send",
        body="Understood. We are processing this for your business.",
        cta="open_ended",
        rationale="Acknowledged merchant message.",
    )
