"""Unit tests for Phase 2: Trigger Routing, Suppression, and Cooldown."""

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path when running script directly
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.contexts import CategoryPayload, CustomerPayload, MerchantPayload, TriggerPayload
from app.state.context_store import context_store
from app.state.conversation_store import conversation_store
from app.suppression.manager import suppression_manager

client = TestClient(app)
DATASET_DIR = ROOT_DIR / "dataset"


@pytest.fixture(autouse=True)
def reset_all_state():
    context_store.clear()
    conversation_store.clear()
    suppression_manager.clear()
    yield


def load_fixtures():
    # Load dentists category
    with open(DATASET_DIR / "categories" / "dentists.json", "r", encoding="utf-8") as f:
        cat = json.load(f)
    context_store.put("category", "dentists", 1, cat)

    # Load first merchant (Dr. Meera)
    with open(DATASET_DIR / "merchants_seed.json", "r", encoding="utf-8") as f:
        mx = json.load(f)["merchants"][0]
    context_store.put("merchant", mx["merchant_id"], 1, mx)

    # Load first customer (Priya)
    with open(DATASET_DIR / "customers_seed.json", "r", encoding="utf-8") as f:
        cx = json.load(f)["customers"][0]
    context_store.put("customer", cx["customer_id"], 1, cx)

    # Load triggers
    with open(DATASET_DIR / "triggers_seed.json", "r", encoding="utf-8") as f:
        triggers = json.load(f)["triggers"]
    for t in triggers:
        context_store.put("trigger", t["id"], 1, t)


def test_proactive_tick_selection():
    load_fixtures()
    now_iso = "2026-04-26T10:30:00Z"
    available = ["trg_001_research_digest_dentists"]

    res = client.post(
        "/v1/tick",
        json={"now": now_iso, "available_triggers": available},
    )
    assert res.status_code == 200
    actions = res.json()["actions"]
    assert len(actions) == 1
    action = actions[0]
    assert action["trigger_id"] == "trg_001_research_digest_dentists"
    assert action["merchant_id"] == "m_001_drmeera_dentist_delhi"
    assert action["send_as"] == "vera"
    assert "Dr. Meera" in action["body"]


def test_trigger_expiry_filter():
    load_fixtures()
    # Trigger 1 expires 2026-05-03. Provide simulated 'now' past expiration
    future_now_iso = "2026-05-10T00:00:00Z"
    available = ["trg_001_research_digest_dentists"]

    res = client.post(
        "/v1/tick",
        json={"now": future_now_iso, "available_triggers": available},
    )
    assert res.status_code == 200
    actions = res.json()["actions"]
    # Expired trigger should NOT fire
    assert len(actions) == 0


def test_suppression_key_prevents_repeat_sends():
    load_fixtures()
    now_iso = "2026-04-26T10:30:00Z"
    available = ["trg_001_research_digest_dentists"]

    # First send -> fires
    res1 = client.post(
        "/v1/tick",
        json={"now": now_iso, "available_triggers": available},
    )
    assert len(res1.json()["actions"]) == 1

    # Second send at same time or within suppression window -> suppressed!
    res2 = client.post(
        "/v1/tick",
        json={"now": "2026-04-26T10:35:00Z", "available_triggers": available},
    )
    assert len(res2.json()["actions"]) == 0


def test_customer_consent_enforcement():
    load_fixtures()
    # Priya has consent for recall_due
    now_iso = "2026-04-26T10:30:00Z"
    available = ["trg_003_recall_due_priya"]

    res = client.post(
        "/v1/tick",
        json={"now": now_iso, "available_triggers": available},
    )
    assert res.status_code == 200
    actions = res.json()["actions"]
    assert len(actions) == 1
    assert actions[0]["send_as"] == "merchant_on_behalf"
    assert actions[0]["customer_id"] == "c_001_priya_for_m001"


def test_max_one_action_per_merchant_per_tick():
    load_fixtures()
    now_iso = "2026-04-26T10:30:00Z"
    # Both triggers target m_001
    available = [
        "trg_001_research_digest_dentists",
        "trg_002_compliance_dci_radiograph",
    ]

    res = client.post(
        "/v1/tick",
        json={"now": now_iso, "available_triggers": available},
    )
    assert res.status_code == 200
    actions = res.json()["actions"]
    # Enforces at most 1 action per merchant
    assert len(actions) == 1
