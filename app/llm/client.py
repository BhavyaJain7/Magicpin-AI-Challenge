"""Thin multi-provider LLM client abstraction."""

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract interface for LLM completion providers."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        """Generate structured completion from system and user prompts."""
        pass


class MockLLMClient(LLMClient):
    """Deterministic mock provider for offline development, CI/CD, and tests."""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        user_lower = user_prompt.lower()

        # Dental research digest pattern (matches Case Study 1)
        if "research_digest" in user_lower and "dentist" in user_lower:
            return {
                "body": (
                    "Dr. Meera, JIDA's Oct issue landed. One item relevant to your high-risk adult "
                    "patients — 2,100-patient trial showed 3-month fluoride recall cuts caries recurrence 38% "
                    "better than 6-month. Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp "
                    "you can share? — JIDA Oct 2026 p.14"
                ),
                "cta": "open_ended",
                "send_as": "vera",
                "template_params": ["Dr. Meera", "JIDA Oct 2026 p.14"],
                "rationale": "Clinical research digest with verifiable trial figures and high-risk adult cohort personalization.",
            }

        # Recall reminder pattern (matches Case Study 2)
        if "recall_due" in user_lower:
            return {
                "body": (
                    "Hi Priya, Dr. Meera's clinic here 🦷 It's been 5 months since your last visit — "
                    "your 6-month cleaning recall is due. Apke liye 2 slots ready hain: Wed 5 Nov, 6pm ya Thu 6 Nov, 5pm. "
                    "₹299 cleaning + complimentary fluoride. Reply 1 for Wed, 2 for Thu, or tell us a time that works."
                ),
                "cta": "choice",
                "send_as": "merchant_on_behalf",
                "template_params": ["Priya", "Wed 5 Nov, 6pm", "Thu 6 Nov, 5pm"],
                "rationale": "Personalized 6-month recall reminder with real available slots and offer pricing.",
            }

        # Bridal followup pattern (matches Case Study 3)
        if "bridal" in user_lower or "wedding" in user_lower:
            return {
                "body": (
                    "Hi Kavya 💍 Lakshmi from Studio11 Kapra here. 196 days to your wedding — perfect window "
                    "to start the 30-day skin-prep program before serious bridal bookings roll in. ₹2,499 covers 4 sessions "
                    "+ a take-home kit. Want me to block your preferred Saturday 4pm slot for the first session next week?"
                ),
                "cta": "binary",
                "send_as": "merchant_on_behalf",
                "template_params": ["Kavya", "196 days", "Saturday 4pm"],
                "rationale": "Relationship continuity following bridal trial with countdown window and package pricing.",
            }

        # Default action reply
        if "commitment" in user_lower or "proceed" in user_lower:
            return {
                "body": "Done! Proceeding with next steps now. Drafting the campaign and sending the confirmation to your WhatsApp.",
                "cta": "none",
                "send_as": "vera",
                "template_params": [],
                "rationale": "Positive commitment transition to action mode.",
            }

        # Generic grounded fallback
        return {
            "body": "Hello, Vera here from magicpin. Reviewing your recent performance updates. Shall we proceed with optimizing your profile?",
            "cta": "binary",
            "send_as": "vera",
            "template_params": [],
            "rationale": "Grounded merchant outreach update.",
        }


class GeminiClient(LLMClient):
    """Google Gemini API Provider."""

    def __init__(self, api_key: str, model_name: str = "gemini-3.8-flash"):
        self.api_key = api_key
        self.model_name = model_name or "gemini-3.8-flash"
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER REQUEST:\n{user_prompt}\n\nOutput only valid JSON."
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(self.url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)


class OpenAIClient(LLMClient):
    """OpenAI API Provider."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model_name = model_name or "gpt-4o-mini"
        self.url = "https://api.openai.com/v1/chat/completions"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(self.url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            return json.loads(raw_text)


def get_llm_client() -> LLMClient:
    """Factory returning configured LLM client or MockLLMClient fallback."""
    provider = settings.LLM_PROVIDER.lower()
    api_key = settings.LLM_API_KEY or os.environ.get("LLM_API_KEY", "")

    if not api_key or provider == "mock":
        return MockLLMClient()

    if provider == "gemini":
        return GeminiClient(api_key=api_key, model_name=settings.LLM_MODEL or "gemini-3.8-flash")
    elif provider == "openai":
        return OpenAIClient(api_key=api_key, model_name=settings.LLM_MODEL or "gpt-4o-mini")

    return MockLLMClient()


# Global client instance
default_llm_client = get_llm_client()
