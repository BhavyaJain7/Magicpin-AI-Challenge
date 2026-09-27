"""Integration tests for Phase 6: Adaptive Context Injection & Mid-Test Updates."""

import copy
import json
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
DATASET_DIR = ROOT_DIR / "dataset"


@pytest.fixture(autouse=True)
def reset_state():
    context_store.clear()
    conversation_store.clear()
    suppression_manager.clear()
    yield


def test_adaptive_category_update_v1_to_v2():
    """Verify that a category pushed with v2 mid-test immediately supersedes v1."""
    with open(DATASET_DIR / "categories" / "dentists.json", "r", encoding="utf-8") as f:
        cat_v1 = json.load(f)

    # 1. Push Version 1
    res1 = client.post(
        "/v1/context",
        json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_v1},
    )
    assert res1.status_code == 200
    assert context_store.get_version("category", "dentists") == 1
    stored_digest = context_store.get("category", "dentists")["digest"]
    assert len(stored_digest) == len(cat_v1["digest"])

    # 2. Prepare Version 2 with new adaptive research digest item
    cat_v2 = copy.deepcopy(cat_v1)
    new_paper = {
        "id": "d_adaptive_2026_paper",
        "kind": "research",
        "title": "Novel Silver Diamine Fluoride Protocol for Geriatric Root Caries",
        "source": "Indian Dental Journal Nov 2026, p.88",
        "trial_n": 850,
        "patient_segment": "geriatric",
        "summary": "Arrests active root caries in 82% of elderly cohort.",
        "actionable": "Pilot root caries protocol for seniors.",
    }
    cat_v2["digest"].insert(0, new_paper)

    # 3. Push Version 2 mid-test
    res2 = client.post(
        "/v1/context",
        json={"scope": "category", "context_id": "dentists", "version": 2, "payload": cat_v2},
    )
    assert res2.status_code == 200
    assert context_store.get_version("category", "dentists") == 2

    # 4. Confirm context store immediately reflects the newly injected paper
    updated_cat = context_store.get("category", "dentists")
    assert updated_cat["digest"][0]["id"] == "d_adaptive_2026_paper"


def test_adaptive_merchant_metric_update_v1_to_v2():
    """Verify merchant performance snapshot updates mid-test."""
    with open(DATASET_DIR / "merchants_seed.json", "r", encoding="utf-8") as f:
        mx_v1 = json.load(f)["merchants"][0]

    mid = mx_v1["merchant_id"]

    # 1. Push Version 1
    res1 = client.post(
        "/v1/context",
        json={"scope": "merchant", "context_id": mid, "version": 1, "payload": mx_v1},
    )
    assert res1.status_code == 200
    assert context_store.get("merchant", mid)["performance"]["views"] == 2410

    # 2. Mid-test performance dip injection (v2)
    mx_v2 = copy.deepcopy(mx_v1)
    mx_v2["performance"]["views"] = 1200
    mx_v2["performance"]["delta_7d"]["views_pct"] = -0.45
    mx_v2["signals"].append("sudden_view_drop:45pct")

    res2 = client.post(
        "/v1/context",
        json={"scope": "merchant", "context_id": mid, "version": 2, "payload": mx_v2},
    )
    assert res2.status_code == 200
    assert context_store.get_version("merchant", mid) == 2
    assert context_store.get("merchant", mid)["performance"]["views"] == 1200
    assert "sudden_view_drop:45pct" in context_store.get("merchant", mid)["signals"]


def test_dynamic_customer_injection_and_tick_routing():
    """Verify customer context injected mid-test can immediately be targeted by proactive ticks."""
    # 1. Base setup (category & merchant)
    with open(DATASET_DIR / "categories" / "dentists.json", "r", encoding="utf-8") as f:
        client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": json.load(f)})

    with open(DATASET_DIR / "merchants_seed.json", "r", encoding="utf-8") as f:
        mx = json.load(f)["merchants"][0]
        client.post("/v1/context", json={"scope": "merchant", "context_id": mx["merchant_id"], "version": 1, "payload": mx})

    # 2. Dynamically inject new Customer mid-test
    new_cx = {
        "customer_id": "c_adaptive_new_cx_099",
        "merchant_id": mx["merchant_id"],
        "identity": {"name": "Simran", "phone_redacted": "<phone>", "language_pref": "hi-en mix", "age_band": "25-35"},
        "relationship": {"first_visit": "2025-10-10", "last_visit": "2026-04-10", "visits_total": 3, "services_received": ["cleaning"]},
        "state": "lapsed_soft",
        "preferences": {"preferred_slots": "saturday_morning", "channel": "whatsapp", "reminder_opt_in": True},
        "consent": {"opted_in_at": "2025-10-10", "scope": ["recall_reminders"]},
    }
    res_cx = client.post(
        "/v1/context",
        json={"scope": "customer", "context_id": new_cx["customer_id"], "version": 1, "payload": new_cx},
    )
    assert res_cx.status_code == 200

    # 3. Dynamically inject new Trigger targeting this customer
    new_trg = {
        "id": "trg_adaptive_recall_simran",
        "scope": "customer",
        "kind": "recall_due",
        "source": "internal",
        "merchant_id": mx["merchant_id"],
        "customer_id": new_cx["customer_id"],
        "payload": {"service_due": "cleaning", "available_slots": [{"iso": "2026-11-07T10:00:00+05:30", "label": "Sat 7 Nov 10am"}]},
        "urgency": 4,
        "suppression_key": f"recall:{new_cx['customer_id']}:cleaning",
        "expires_at": "2026-12-01T00:00:00Z",
    }
    client.post(
        "/v1/context",
        json={"scope": "trigger", "context_id": new_trg["id"], "version": 1, "payload": new_trg},
    )

    # 4. Trigger tick: Router must dynamically select and format action for Simran
    tick_res = client.post(
        "/v1/tick",
        json={"now": "2026-04-26T10:30:00Z", "available_triggers": [new_trg["id"]]},
    )
    assert tick_res.status_code == 200
    actions = tick_res.json()["actions"]
    assert len(actions) == 1
    assert actions[0]["customer_id"] == "c_adaptive_new_cx_099"
    assert actions[0]["send_as"] == "merchant_on_behalf"
