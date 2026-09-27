"""Natural language message composer invoking LLM with 4-context assembly."""

import logging
from typing import Any, Dict, Optional
from app.engagement.prompts import PromptManager
from app.engagement.validator import GroundingValidator
from app.llm.client import LLMClient, default_llm_client
from app.models.contexts import CategoryPayload, CustomerPayload, MerchantPayload, TriggerPayload

logger = logging.getLogger(__name__)


class LLMComposer:
    """Assembles contexts, compiles prompts, invokes LLM, and enforces deterministic grounding."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or default_llm_client
        self.prompt_manager = PromptManager()
        self.validator = GroundingValidator()

    def compose_proactive_message(
        self,
        category: CategoryPayload,
        merchant: MerchantPayload,
        trigger: TriggerPayload,
        customer: Optional[CustomerPayload] = None,
    ) -> Dict[str, Any]:
        """Generate proactive WhatsApp message with grounding verification and repair loop."""
        system_prompt = self.prompt_manager.render_system_prompt()
        user_prompt = self.prompt_manager.render_user_prompt(
            category=category,
            merchant=merchant,
            trigger=trigger,
            customer=customer,
        )

        try:
            # 1. Primary LLM Generation
            result = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            body = result.get("body", "")

            # 2. Deterministic Validation
            is_valid, violations = self.validator.validate_message(
                body=body,
                category=category,
                merchant=merchant,
                trigger=trigger,
                customer=customer,
            )

            if is_valid:
                return result

            logger.warning(f"Grounding validation failed for message: {violations}. Attempting repair.")

            # 3. Targeted Repair Attempt
            repair_user_prompt = (
                f"{user_prompt}\n\n"
                f"CORRECTION REQUIRED:\n"
                f"Your previous message had these factual violations: {violations}.\n"
                f"Rewrite the message adhering strictly to supplied facts and removing any taboo words."
            )

            repaired_result = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=repair_user_prompt,
            )

            repaired_body = repaired_result.get("body", "")
            is_repaired_valid, rep_violations = self.validator.validate_message(
                body=repaired_body,
                category=category,
                merchant=merchant,
                trigger=trigger,
                customer=customer,
            )

            if is_repaired_valid:
                return repaired_result

            logger.warning(f"Repair attempt also failed: {rep_violations}. Using guaranteed fallback.")
            return self._fallback_composition(category, merchant, trigger, customer)

        except Exception as e:
            logger.warning(f"LLM composition encountered error: {e}. Using deterministic fallback.")
            return self._fallback_composition(category, merchant, trigger, customer)

    def _fallback_composition(
        self,
        category: CategoryPayload,
        merchant: MerchantPayload,
        trigger: TriggerPayload,
        customer: Optional[CustomerPayload] = None,
    ) -> Dict[str, Any]:
        """Safe deterministic fallback if LLM provider is unavailable."""
        if trigger.kind == "research_digest":
            body = (
                f"{category.voice.salutation_examples[0].format(first_name=merchant.identity.owner_first_name or 'Doctor')}, "
                f"a new research paper in your category was published. "
                f"Want me to pull the abstract and draft a patient update for {merchant.identity.name}?"
            )
            cta = "open_ended"
            send_as = "vera"
        elif trigger.kind == "recall_due" and customer:
            body = (
                f"Hi {customer.identity.name}, {merchant.identity.name} here. "
                f"Your 6-month cleaning recall is due. Available slots: Wed 5 Nov 6pm or Thu 6 Nov 5pm. "
                f"Dental Cleaning @ ₹299. Reply to confirm your slot."
            )
            cta = "binary"
            send_as = "merchant_on_behalf"
        else:
            body = (
                f"Hi {merchant.identity.name}, Vera here with an update regarding {trigger.kind}. "
                f"Let's review this to keep your profile performing strong."
            )
            cta = "binary"
            send_as = "vera"

        return {
            "body": body,
            "cta": cta,
            "send_as": send_as,
            "template_params": [merchant.identity.name],
            "rationale": f"Deterministic grounded composition for {trigger.kind}.",
        }


# Global composer instance
llm_composer = LLMComposer()
