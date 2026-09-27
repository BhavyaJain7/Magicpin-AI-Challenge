"""Integration tests for Phase 1 FastAPI endpoints and ContextStore."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.state.context_store import context_store
from app.state.conversation_store import conversation_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    context_store.clear()
    conversation_store.clear()
    yield


def test_healthz_endpoint():
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert data["contexts_loaded"] == {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}


def test_metadata_endpoint():
    response = client.get("/v1/metadata")
    assert response.status_code == 200
    data = response.json()
    assert "team_name" in data
    assert "model" in data
    assert "approach" in data
    assert "submitted_at" in data


def test_context_push_and_versioning():
    # Push version 1
    payload_v1 = {"slug": "dentists", "title": "Dentists vertical"}
    res1 = client.post(
        "/v1/context",
        json={
            "scope": "category",
            "context_id": "dentists",
            "version": 1,
            "payload": payload_v1,
        },
    )
    assert res1.status_code == 200
    assert res1.json()["accepted"] is True

    # Check health counts updated
    health_res = client.get("/v1/healthz")
    assert health_res.json()["contexts_loaded"]["category"] == 1

    # Idempotent push of same version (v1 == v1) -> 200
    res_same = client.post(
        "/v1/context",
        json={
            "scope": "category",
            "context_id": "dentists",
            "version": 1,
            "payload": payload_v1,
        },
    )
    assert res_same.status_code == 200
    assert res_same.json()["accepted"] is True

    # Push newer version (v2 > v1) -> 200
    payload_v2 = {"slug": "dentists", "title": "Updated Dentists vertical"}
    res2 = client.post(
        "/v1/context",
        json={
            "scope": "category",
            "context_id": "dentists",
            "version": 2,
            "payload": payload_v2,
        },
    )
    assert res2.status_code == 200
    assert res2.json()["accepted"] is True
    assert context_store.get_version("category", "dentists") == 2

    # Push stale version (v1 < v2) -> 409 Conflict
    res_stale = client.post(
        "/v1/context",
        json={
            "scope": "category",
            "context_id": "dentists",
            "version": 1,
            "payload": payload_v1,
        },
    )
    assert res_stale.status_code == 409
    assert res_stale.json()["detail"]["reason"] == "stale_version"
    assert res_stale.json()["detail"]["current_version"] == 2


def test_tick_endpoint():
    res = client.post(
        "/v1/tick",
        json={
            "now": "2026-04-26T10:30:00Z",
            "available_triggers": ["trg_001"],
        },
    )
    assert res.status_code == 200
    assert "actions" in res.json()
    assert isinstance(res.json()["actions"], list)


def test_reply_endpoint():
    res = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_001",
            "merchant_id": "m_001",
            "message": "Hello Vera",
            "turn_number": 1,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action"] == "send"
    assert "body" in data
    assert "rationale" in data


def test_reply_stop_intent():
    res = client.post(
        "/v1/reply",
        json={
            "conversation_id": "conv_002",
            "merchant_id": "m_001",
            "message": "Please stop messaging me",
            "turn_number": 2,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action"] == "end"
