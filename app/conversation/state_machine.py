"""Conversation state machine managing transitions and action policy."""

from typing import Optional, Tuple
from app.models.conversation import (
    ConversationState,
    ConversationStateEnum,
    IntentEnum,
    MerchantInteractionState,
)
from app.models.responses import ReplyResponse


class ConversationStateMachine:
    """Orchestrates deterministic state transitions and responses for /v1/reply."""

    @staticmethod
    def process_turn(
        conv: ConversationState,
        mx_state: MerchantInteractionState,
        message: str,
        intent: IntentEnum,
        is_auto_reply: bool,
    ) -> ReplyResponse:
        """Evaluate intent and state to generate the next action: send, wait, or end."""

        # 1. Handle STOP / Unsubscribe
        if intent == IntentEnum.STOP:
            conv.state = ConversationStateEnum.ENDED
            conv.ended = True
            mx_state.unsubscribed = True
            return ReplyResponse(
                action="end",
                rationale="Merchant explicitly opted out via STOP. Ending session.",
            )

        # 2. Handle Hostility
        if intent == IntentEnum.HOSTILE:
            conv.state = ConversationStateEnum.ENDED
            conv.ended = True
            return ReplyResponse(
                action="end",
                rationale="Merchant indicated hostility. Apologizing and terminating conversation gracefully.",
            )

        # 3. Handle Positive Commitment / Intent Handoff (Problem 2) - TOP PRIORITY
        if intent == IntentEnum.POSITIVE_COMMITMENT or conv.state == ConversationStateEnum.ACTION:
            conv.state = ConversationStateEnum.ACTION
            # STRICT RULE: Must NOT ask qualifying questions (would you, do you, how about)
            # Must take action: confirm, proceed, next steps
            return ReplyResponse(
                action="send",
                body="Done! Proceeding with next steps now. Drafting the campaign and sending the confirmation to your WhatsApp.",
                cta="none",
                rationale="Positive commitment recognized. Switched directly to ACTION mode without re-qualifying.",
            )

        # 4. Handle Auto-Reply Hell (Problem 1)
        if is_auto_reply:
            conv.auto_reply_count += 1
            conv.state = ConversationStateEnum.AUTO_REPLY

            # If this merchant has sent repeated auto-replies >= 2 times across any session -> END immediately
            msg_hash = mx_state.recent_message_hashes[-1] if mx_state.recent_message_hashes else ""
            msg_count = mx_state.repeated_auto_reply_hashes.get(msg_hash, 1)
            if msg_count >= 2 or conv.auto_reply_count >= 2:
                conv.state = ConversationStateEnum.ENDED
                conv.ended = True
                return ReplyResponse(
                    action="end",
                    rationale=f"Repeated automated canned response detected ({msg_count} occurrences). Ending session to avoid burning turns.",
                )

            # Turn 1: 1 polite wait or graceful backoff
            return ReplyResponse(
                action="wait",
                wait_seconds=1800,
                rationale="Automated response received. Backing off 30 minutes to allow human response.",
            )

        # 5. Handle Not Interested
        if intent == IntentEnum.NOT_INTERESTED:
            conv.state = ConversationStateEnum.ENDED
            conv.ended = True
            return ReplyResponse(
                action="end",
                rationale="Merchant stated not interested. Respectfully ending conversation.",
            )

        # 6. Handle Questions / Informational
        if intent == IntentEnum.QUESTION:
            conv.state = ConversationStateEnum.ANSWERING
            return ReplyResponse(
                action="send",
                body="Here are the details for your clinic. We can handle the setup directly for you. Shall we proceed?",
                cta="binary",
                rationale="Answered merchant question with clear next step.",
            )

        # 7. General Engagement Default
        conv.state = ConversationStateEnum.ENGAGED
        return ReplyResponse(
            action="send",
            body="Understood. Here is the recommended next step for your profile. Ready to proceed?",
            cta="binary",
            rationale="Continuing active conversation with merchant.",
        )
