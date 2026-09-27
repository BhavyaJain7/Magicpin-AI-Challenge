"""Unit tests for Phase 5 GroundingValidator and quality assurance."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import pytest
from app.engagement.composer import LLMComposer
from app.engagement.validator import GroundingValidator
from app.llm.client import LLMClient
from app.models.contexts import (
    CategoryPayload,
    CustomerPayload,
    MerchantPayload,
    TriggerPayload,
)

DATASET_DIR = ROOT_DIR / "dataset"


@pytest.fixture
def fixtures():
    with open(DATASET_DIR / "categories" / "dentists.json", "r", encoding="utf-8") as f:
        cat = CategoryPayload.model_validate(json.load(f))
    with open(DATASET_DIR / "merchants_seed.json", "r", encoding="utf-8") as f:
        mx = MerchantPayload.model_validate(json.load(f)["merchants"][0])
    with open(DATASET_DIR / "triggers_seed.json", "r", encoding="utf-8") as f:
        trg = TriggerPayload.model_validate(json.load(f)["triggers"][0])
    return cat, mx, trg


def test_validator_detects_taboo_word(fixtures):
    cat, mx, trg = fixtures
    # Message containing taboo term "guaranteed" for dentists
    bad_msg = "Dr. Meera, we offer a guaranteed cleaning program for your clinic."
    is_valid, violations = GroundingValidator.validate_message(
        body=bad_msg, category=cat, merchant=mx, trigger=trg
    )
    assert is_valid is False
    assert any("taboo" in v.lower() for v in violations)


def test_validator_detects_hallucinated_number(fixtures):
    cat, mx, trg = fixtures
    # 79% does not exist in any dentist context
    bad_msg = "Dr. Meera, JIDA says this cuts decay by 79% in 4500 patients."
    is_valid, violations = GroundingValidator.validate_message(
        body=bad_msg, category=cat, merchant=mx, trigger=trg
    )
    assert is_valid is False
    assert any("hallucinated" in v.lower() for v in violations)


def test_validator_passes_grounded_message(fixtures):
    cat, mx, trg = fixtures
    # Uses genuine facts from dentists.json digest: 2100 trial, 38%, JIDA Oct 2026 p.14
    good_msg = (
        "Dr. Meera, JIDA's Oct issue landed. One item relevant to your high-risk adult "
        "patients — 2,100-patient trial showed 3-month fluoride recall cuts caries recurrence 38% "
        "better than 6-month. Worth a look (2-min abstract). Want me to pull it? — JIDA Oct 2026 p.14"
    )
    is_valid, violations = GroundingValidator.validate_message(
        body=good_msg, category=cat, merchant=mx, trigger=trg
    )
    assert is_valid is True
    assert len(violations) == 0


class HallucinatingLLM(LLMClient):
    """Mock LLM that hallucinates to test the repair/fallback mechanism."""
    def generate(self, system_prompt: str, user_prompt: str, response_schema=None):
        return {
            "body": "Guaranteed 100% cure for caries at ₹19 with 99% success rate!",
            "cta": "binary",
            "send_as": "vera",
            "rationale": "Hallucinating",
        }


def test_composer_repair_and_fallback_on_hallucination(fixtures):
    cat, mx, trg = fixtures
    composer = LLMComposer(llm_client=HallucinatingLLM())

    # When LLM repeatedly hallucinates taboo words and prices, composer must fallback to safe grounded message
    result = composer.compose_proactive_message(
        category=cat,
        merchant=mx,
        trigger=trg,
    )

    assert "guaranteed" not in result["body"].lower()
    assert "100%" not in result["body"]
    assert result["send_as"] == "vera"
    assert "Doctor" in result["body"] or "Dr." in result["body"]
