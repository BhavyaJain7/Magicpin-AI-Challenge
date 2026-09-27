"""Prompt manager for compiling Jinja2 templates with context."""

from pathlib import Path
from typing import Any, Dict, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.models.contexts import CategoryPayload, CustomerPayload, MerchantPayload, TriggerPayload

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    autoescape=select_autoescape(["html", "xml", "jinja2"]),
)


class PromptManager:
    """Renders Jinja2 system and user prompts with 4-context variables."""

    @staticmethod
    def render_system_prompt() -> str:
        template = _env.get_template("base_system.jinja2")
        return template.render()

    @staticmethod
    def render_user_prompt(
        category: CategoryPayload,
        merchant: MerchantPayload,
        trigger: TriggerPayload,
        customer: Optional[CustomerPayload] = None,
    ) -> str:
        template = _env.get_template("user_prompt.jinja2")
        return template.render(
            category=category,
            merchant=merchant,
            trigger=trigger,
            customer=customer,
        )
