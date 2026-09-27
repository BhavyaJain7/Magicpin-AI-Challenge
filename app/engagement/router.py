"""Trigger routing and proactive engagement prioritization."""

import uuid
from typing import List, Optional, Tuple
from app.engagement.policies import EngagementPolicies
from app.models.contexts import CategoryPayload, CustomerPayload, MerchantPayload, TriggerPayload
from app.models.responses import ProactiveAction
from app.state.context_store import context_store
from app.state.conversation_store import conversation_store
from app.suppression.manager import suppression_manager


class TriggerRouter:
    """Evaluates available triggers during POST /v1/tick and selects the best proactive action."""

    def __init__(self):
        self.policies = EngagementPolicies()

    def calculate_priority(
        self,
        trigger: TriggerPayload,
        merchant: MerchantPayload,
        now_iso: str,
    ) -> float:
        """Heuristic priority ranking function.
        Priority = urgency * 10 + merchant_relevance + engagement_score
        """
        score = float(trigger.urgency * 10)

        # Boost if merchant has relevant signals
        if trigger.kind == "research_digest" and "high_risk_adult_cohort" in merchant.signals:
            score += 15.0

        if trigger.kind == "perf_dip" and "ctr_below_peer_median" in merchant.signals:
            score += 20.0

        # Customer-facing recall is urgent and personalized
        if trigger.scope == "customer":
            score += 10.0

        return score

    def route_triggers(
        self, available_trigger_ids: List[str], now_iso: str
    ) -> List[ProactiveAction]:
        """Filter, rank, and assemble proactive actions for available triggers.
        Limits outreach to at most 1 action per merchant per tick.
        """
        eligible_candidates: List[Tuple[float, TriggerPayload, CategoryPayload, MerchantPayload, Optional[CustomerPayload]]] = []
        merchants_seen_this_tick = set()

        for tid in available_trigger_ids:
            # 1. Fetch trigger context
            raw_trg = context_store.get("trigger", tid)
            if not raw_trg:
                continue

            try:
                trigger = TriggerPayload.model_validate(raw_trg)
            except Exception:
                continue

            # 2. Check consumed & expiration
            if suppression_manager.is_consumed(trigger.id):
                continue

            if suppression_manager.is_trigger_expired(trigger, now_iso):
                continue

            # 3. Check suppression key
            if suppression_manager.is_suppression_key_active(trigger.suppression_key, now_iso):
                continue

            # 4. Check merchant cooldown
            if suppression_manager.is_merchant_in_cooldown(trigger.merchant_id, now_iso):
                continue

            # 5. Resolve merchant context
            raw_mx = context_store.get("merchant", trigger.merchant_id)
            if not raw_mx:
                continue
            try:
                merchant = MerchantPayload.model_validate(raw_mx)
            except Exception:
                continue

            # 6. Resolve category context
            raw_cat = context_store.get("category", merchant.category_slug)
            if not raw_cat:
                continue
            try:
                category = CategoryPayload.model_validate(raw_cat)
            except Exception:
                continue

            # 7. Resolve customer context if customer scope
            customer: Optional[CustomerPayload] = None
            if trigger.scope == "customer" and trigger.customer_id:
                raw_cx = context_store.get("customer", trigger.customer_id)
                if not raw_cx:
                    continue
                try:
                    customer = CustomerPayload.model_validate(raw_cx)
                except Exception:
                    continue

                # Verify customer consent
                if not suppression_manager.has_customer_consent(customer, trigger.kind):
                    continue

            # 8. Check context readiness & opt-out
            mx_state = conversation_store.get_or_create_merchant_state(merchant.merchant_id)
            ready, reason = self.policies.validate_context_readiness(
                trigger, category, merchant, customer, mx_state
            )
            if not ready:
                continue

            # Score candidate
            priority = self.calculate_priority(trigger, merchant, now_iso)
            eligible_candidates.append((priority, trigger, category, merchant, customer))

        # Sort descending by priority
        eligible_candidates.sort(key=lambda x: x[0], reverse=True)

        selected_actions: List[ProactiveAction] = []

        for _, trigger, category, merchant, customer in eligible_candidates:
            if trigger.merchant_id in merchants_seen_this_tick:
                continue  # Max 1 proactive action per merchant per tick

            # Assemble baseline message body according to trigger type
            # (In Phase 4, the LLM Composer takes over dynamic text generation)
            send_as = "vera" if trigger.scope == "merchant" else "merchant_on_behalf"
            cta = self.policies.get_cta_policy(trigger)
            conv_id = f"conv_{uuid.uuid4().hex[:8]}"

            if trigger.kind == "research_digest":
                body = (
                    f"{category.voice.salutation_examples[0].format(first_name=merchant.identity.owner_first_name or 'Doctor')}, "
                    f"a new research paper in your category was published. "
                    f"Would you like me to pull the abstract and draft a patient update for {merchant.identity.name}?"
                )
                rationale = f"Proactive research digest update grounded in {merchant.category_slug} category context."
            elif trigger.kind == "recall_due" and customer:
                body = (
                    f"Hi {customer.identity.name}, {merchant.identity.name} here. "
                    f"Your scheduled visit window is open. Reply to book your preferred slot."
                )
                rationale = f"Customer recall due reminder for {customer.customer_id}."
            else:
                body = (
                    f"Hi {merchant.identity.name}, Vera here with an update regarding {trigger.kind}. "
                    f"Let's review this to keep your business profile performing strong."
                )
                rationale = f"Proactive alert for trigger {trigger.kind}."

            # Check message deduplication
            if suppression_manager.has_duplicate_message(body):
                continue

            action = ProactiveAction(
                conversation_id=conv_id,
                merchant_id=trigger.merchant_id,
                customer_id=trigger.customer_id,
                send_as=send_as,
                trigger_id=trigger.id,
                template_name=f"vera_{trigger.kind}_v1",
                template_params=[merchant.identity.name],
                body=body,
                cta=cta,
                suppression_key=trigger.suppression_key,
                rationale=rationale,
            )

            # Record send in suppression manager to enforce cooldown & deduplication
            suppression_manager.record_proactive_send(
                trigger_id=trigger.id,
                suppression_key=trigger.suppression_key,
                merchant_id=trigger.merchant_id,
                message_body=body,
                now_iso=now_iso,
                expiry_iso=trigger.expires_at,
            )

            merchants_seen_this_tick.add(trigger.merchant_id)
            selected_actions.append(action)

        return selected_actions


# Global singleton instance
trigger_router = TriggerRouter()
