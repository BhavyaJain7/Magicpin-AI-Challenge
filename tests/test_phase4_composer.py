"""Unit tests for Phase 4: LLM Composer, Prompt Manager, and Multi-Provider Abstraction."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import pytest
from app.engagement.composer import LLMComposer
from app.engagement.prompts import PromptManager
from app.llm.client import MockLLMClient
from app.models.contexts import (
    CategoryPayload,
    CustomerPayload,
    MerchantPayload,
    TriggerPayload,
)

DATASET_DIR = ROOT_DIR / "dataset"


@pytest.fixture
def sample_contexts():
    with open(DATASET_DIR / "categories" / "dentists.json", "r", encoding="utf-8") as f:
        cat = CategoryPayload.model_validate(json.load(f))

    with open(DATASET_DIR / "merchants_seed.json", "r", encoding="utf-8") as f:
        mx = MerchantPayload.model_validate(json.load(f)["merchants"][0])

    with open(DATASET_DIR / "customers_seed.json", "r", encoding="utf-8") as f:
        cx = CustomerPayload.model_validate(json.load(f)["customers"][0])

    with open(DATASET_DIR / "triggers_seed.json", "r", encoding="utf-8") as f:
        trg = TriggerPayload.model_validate(json.load(f)["triggers"][0])

    return cat, mx, trg, cx


def test_prompt_manager_compilation(sample_contexts):
    cat, mx, trg, cx = sample_contexts
    sys_prompt = PromptManager.render_system_prompt()
    assert "You are Vera" in sys_prompt
    assert "TABOO VOCABULARY" in sys_prompt

    user_prompt = PromptManager.render_user_prompt(cat, mx, trg, cx)
    assert "dentists" in user_prompt
    assert "Dr. Meera" in user_prompt
    assert "research_digest" in user_prompt


def test_composer_research_digest_output(sample_contexts):
    cat, mx, trg, _ = sample_contexts
    composer = LLMComposer(llm_client=MockLLMClient())
    result = composer.compose_proactive_message(
        category=cat,
        merchant=mx,
        trigger=trg,
    )

    assert "body" in result
    assert "JIDA" in result["body"]
    assert "2,100" in result["body"]
    assert "38%" in result["body"]
    assert result["cta"] == "open_ended"
    assert result["send_as"] == "vera"


def test_composer_recall_due_output(sample_contexts):
    cat, mx, _, cx = sample_contexts
    with open(DATASET_DIR / "triggers_seed.json", "r", encoding="utf-8") as f:
        trg_recall = TriggerPayload.model_validate(json.load(f)["triggers"][2])

    composer = LLMComposer(llm_client=MockLLMClient())
    result = composer.compose_proactive_message(
        category=cat,
        merchant=mx,
        trigger=trg_recall,
        customer=cx,
    )

    assert "body" in result
    assert "Priya" in result["body"]
    assert "₹299" in result["body"]
    assert result["send_as"] == "merchant_on_behalf"
