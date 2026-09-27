"""Engagement policies, context validation, and CTA rules."""

from typing import Literal, Optional, Tuple
from app.models.contexts import CategoryPayload, CustomerPayload, MerchantPayload, TriggerPayload
from app.models.conversation import MerchantInteractionState


class EngagementPolicies:
    """Deterministic validation and CTA rules for candidate proactive actions."""

    @staticmethod
    def validate_context_readiness(
        trigger: TriggerPayload,
        category: Optional[CategoryPayload],
        merchant: Optional[MerchantPayload],
        customer: Optional[CustomerPayload],
        mx_state: Optional[MerchantInteractionState],
    ) -> Tuple[bool, str]:
        """Verify that all prerequisite contexts exist and merchant is active."""
        if not merchant:
            return False, f"Missing MerchantContext for merchant_id: {trigger.merchant_id}"

        if not category:
            return False, f"Missing CategoryContext for category_slug: {merchant.category_slug}"

        if trigger.scope == "customer":
            if not trigger.customer_id:
                return False, "Customer-scope trigger missing customer_id"
            if not customer:
                return False, f"Missing CustomerContext for customer_id: {trigger.customer_id}"

        if mx_state and mx_state.unsubscribed:
            return False, f"Merchant {trigger.merchant_id} has unsubscribed (STOP)"

        return True, "Context ready"

    @staticmethod
    def get_cta_policy(trigger: TriggerPayload) -> Literal["binary", "open_ended", "choice", "none"]:
        """Determine appropriate CTA policy based on trigger nature."""
        # Action triggers prefer binary commit
        if trigger.kind in [
            "research_digest",
            "recall_due",
            "wedding_package_followup",
            "perf_dip",
            "renewal_due",
        ]:
            return "open_ended" if trigger.kind == "research_digest" else "binary"

        # Information / milestone triggers can be open-ended or none
        if trigger.kind in ["milestone_reached", "festival_upcoming"]:
            return "open_ended"

        return "none"
