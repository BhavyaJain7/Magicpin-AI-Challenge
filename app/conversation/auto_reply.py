"""Multi-signal auto-reply detector using merchant-level interaction state."""

from typing import Tuple
from app.conversation.intent import IntentDetector
from app.models.conversation import IntentEnum, MerchantInteractionState
from app.state.conversation_store import hash_text


class AutoReplyDetector:
    """Detects WhatsApp Business auto-replies across conversation sessions."""

    @staticmethod
    def evaluate(
        message: str,
        mx_state: MerchantInteractionState,
    ) -> Tuple[bool, str]:
        """Returns (is_auto_reply, reason).
        Checks message hashes across sessions and known canned phrases.
        """
        # Signal 1: Intent detector flagged canned phrase
        intent, _ = IntentDetector.detect_intent(message)
        if intent == IntentEnum.AUTO_REPLY:
            return True, "Canned business response pattern detected."

        # Signal 2: Repetition of identical normalized message for this merchant
        msg_hash = hash_text(message)
        count = mx_state.repeated_auto_reply_hashes.get(msg_hash, 0)

        # If seen >= 2 times across any conversation ID for this merchant
        if count >= 2:
            return True, f"Identical message received {count} times from this merchant."

        return False, "Legitimate reply"
