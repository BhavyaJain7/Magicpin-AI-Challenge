"""Integration tests for Phase 3 Conversation Intelligence (Auto-Reply, Intent, Hostile)."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.state.context_store import context_store
from app.state.conversation_store import conversation_store
from app.suppression.manager import suppression_manager

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    context_store.clear()
    conversation_store.clear()
    suppression_manager.clear()
    yield


def test_auto_reply_hell_scenario():
    """Verify bot ends after repeated canned auto-replies across changing conversation IDs."""
    merchant_id = "m_001_drmeera"
    canned_msg = "Thank you for contacting us! Our team will respond shortly."

    # Turn 1: bot backs off with wait
    res1 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_auto_1",
            "merchant_id": merchant_id,
            "message": canned_msg,
            "turn_number": 2,
        },
    )
    assert res1.status_code == 200
    assert res1.json()["action"] in ["wait", "end"]

    # Turn 2: same canned message on different conversation ID -> MUST END!
    res2 = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_auto_2",
            "merchant_id": merchant_id,
            "message": canned_msg,
            "turn_number": 3,
        },
    )
    assert res2.status_code == 200
    assert res2.json()["action"] == "end"


def test_intent_transition_scenario():
    """Verify commitment switches immediately to ACTION without re-qualifying questions."""
    merchant_id = "m_001_drmeera"
    commitment = "Ok lets do it. Whats next?"

    res = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_intent_1",
            "merchant_id": merchant_id,
            "message": commitment,
            "turn_number": 2,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action"] == "send"
    body = data.get("body", "").lower()

    # Must contain action-oriented terms
    action_words = ["done", "proceeding", "draft", "sending", "next"]
    assert any(w in body for w in action_words)

    # Must NOT ask qualifying questions
    qualifying_words = ["would you", "do you", "how about", "what if"]
    assert not any(w in body for w in qualifying_words)


def test_hostile_scenario():
    """Verify hostile message terminates conversation politely."""
    merchant_id = "m_001_drmeera"
    hostile_msg = "Stop messaging me. This is useless spam."

    res = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_hostile_1",
            "merchant_id": merchant_id,
            "message": hostile_msg,
            "turn_number": 2,
        },
    )
    assert res.status_code == 200
    assert res.json()["action"] == "end"


def test_stop_opt_out():
    """Verify explicit STOP opts out merchant."""
    merchant_id = "m_002_bharat"
    res = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_stop",
            "merchant_id": merchant_id,
            "message": "STOP",
            "turn_number": 2,
        },
    )
    assert res.status_code == 200
    assert res.json()["action"] == "end"
    mx_state = conversation_store.get_or_create_merchant_state(merchant_id)
    assert mx_state.unsubscribed is True
