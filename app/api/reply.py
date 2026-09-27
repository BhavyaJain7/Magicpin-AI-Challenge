"""POST /v1/reply endpoint."""

from fastapi import APIRouter
from app.conversation.auto_reply import AutoReplyDetector
from app.conversation.intent import IntentDetector
from app.conversation.state_machine import ConversationStateMachine
from app.models.requests import ReplyRequest
from app.models.responses import ReplyResponse
from app.state.conversation_store import conversation_store

router = APIRouter()


@router.post("/v1/reply", response_model=ReplyResponse)
async def reply(req: ReplyRequest):
    # 1. Record incoming turn in conversation and merchant state (handles unknown session recovery)
    conv, mx_state = conversation_store.record_incoming_turn(
        conversation_id=req.conversation_id,
        merchant_id=req.merchant_id,
        message=req.message,
        turn_number=req.turn_number,
        from_role=req.from_role,
        customer_id=req.customer_id,
    )

    # 2. Detect intent
    intent, confidence = IntentDetector.detect_intent(req.message)
    conv.detected_intent = intent

    # 3. Detect auto-reply across merchant session history
    is_auto_reply, _ = AutoReplyDetector.evaluate(req.message, mx_state)

    # 4. Process state transition and return action
    response = ConversationStateMachine.process_turn(
        conv=conv,
        mx_state=mx_state,
        message=req.message,
        intent=intent,
        is_auto_reply=is_auto_reply,
    )

    return response
