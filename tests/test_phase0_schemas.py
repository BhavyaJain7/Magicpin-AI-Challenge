"""Test Phase 0 schemas and dataset compatibility."""

import json
from pathlib import Path
import pytest
from app.models.contexts import (
    CategoryPayload,
    MerchantPayload,
    CustomerPayload,
    TriggerPayload,
)
from app.models.requests import ContextPushRequest, TickRequest, ReplyRequest
from app.models.responses import (
    ContextPushResponse,
    HealthResponse,
    MetadataResponse,
    TickResponse,
    ReplyResponse,
)
from app.models.conversation import ConversationState, ConversationStateEnum, IntentEnum

DATASET_DIR = Path(__file__).parent.parent / "dataset"


def test_category_schema_parsing():
    cat_file = DATASET_DIR / "categories" / "dentists.json"
    with open(cat_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    cat = CategoryPayload.model_validate(data)
    assert cat.slug == "dentists"
    assert len(cat.offer_catalog) > 0
    assert len(cat.digest) > 0
    assert "guaranteed" in cat.voice.vocab_taboo


def test_merchant_schema_parsing():
    mx_file = DATASET_DIR / "merchants_seed.json"
    with open(mx_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    merchants = data["merchants"]
    for m in merchants:
        merchant = MerchantPayload.model_validate(m)
        assert merchant.merchant_id
        assert merchant.identity.name


def test_customer_schema_parsing():
    cx_file = DATASET_DIR / "customers_seed.json"
    with open(cx_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    customers = data["customers"]
    for c in customers:
        customer = CustomerPayload.model_validate(c)
        assert customer.customer_id
        assert customer.merchant_id


def test_trigger_schema_parsing():
    trg_file = DATASET_DIR / "triggers_seed.json"
    with open(trg_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    triggers = data["triggers"]
    for t in triggers:
        trigger = TriggerPayload.model_validate(t)
        assert trigger.id
        assert trigger.scope in ["merchant", "customer"]
        assert trigger.suppression_key


def test_requests_and_responses():
    push_req = ContextPushRequest(
        scope="category",
        context_id="dentists",
        version=1,
        payload={"slug": "dentists"}
    )
    assert push_req.scope == "category"

    tick_req = TickRequest(
        now="2026-04-26T10:30:00Z",
        available_triggers=["trg_001"]
    )
    assert tick_req.available_triggers == ["trg_001"]

    reply_req = ReplyRequest(
        conversation_id="conv_001",
        merchant_id="m_001",
        message="Ok lets do it",
        turn_number=2
    )
    assert reply_req.turn_number == 2

    health = HealthResponse(status="ok", uptime_seconds=10)
    assert health.status == "ok"
    assert health.contexts_loaded.category == 0

    reply_resp = ReplyResponse(
        action="send",
        body="Starting now",
        rationale="Merchant confirmed"
    )
    assert reply_resp.action == "send"


def test_conversation_state_enum():
    state = ConversationState(
        conversation_id="conv_123",
        merchant_id="m_001",
        state=ConversationStateEnum.ENGAGED,
        detected_intent=IntentEnum.POSITIVE_COMMITMENT
    )
    assert state.state == ConversationStateEnum.ENGAGED
    assert state.detected_intent == IntentEnum.POSITIVE_COMMITMENT
