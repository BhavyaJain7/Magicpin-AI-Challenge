"""State management for conversations and merchant interactions."""

import hashlib
import re
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from app.models.conversation import (
    ConversationState,
    ConversationStateEnum,
    MerchantInteractionState,
    TurnRecord,
)


def normalize_text(text: str) -> str:
    """Normalize text for consistent duplicate/auto-reply hashing."""
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return re.sub(r"[^\w\s]", "", cleaned)


def hash_text(text: str) -> str:
    """SHA-256 hash of normalized text."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ConversationStore:
    """Thread-safe store managing per-conversation sessions and cross-conversation merchant states."""

    def __init__(self):
        self._lock = threading.RLock()
        self._conversations: Dict[str, ConversationState] = {}
        self._merchant_states: Dict[str, MerchantInteractionState] = {}

    def get_or_create_conversation(
        self, conversation_id: str, merchant_id: str, customer_id: Optional[str] = None
    ) -> ConversationState:
        with self._lock:
            if conversation_id not in self._conversations:
                now_iso = datetime.now(timezone.utc).isoformat()
                self._conversations[conversation_id] = ConversationState(
                    conversation_id=conversation_id,
                    merchant_id=merchant_id,
                    customer_id=customer_id,
                    session_started_at=now_iso,
                    state=ConversationStateEnum.NEW,
                )
            return self._conversations[conversation_id]

    def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        with self._lock:
            return self._conversations.get(conversation_id)

    def record_incoming_turn(
        self,
        conversation_id: str,
        merchant_id: str,
        message: str,
        turn_number: int,
        from_role: str = "merchant",
        customer_id: Optional[str] = None,
    ) -> Tuple[ConversationState, MerchantInteractionState]:
        with self._lock:
            conv = self.get_or_create_conversation(conversation_id, merchant_id, customer_id)
            mx_state = self.get_or_create_merchant_state(merchant_id)

            now_iso = datetime.now(timezone.utc).isoformat()
            conv.turn_count = max(conv.turn_count, turn_number)
            conv.last_received_at = now_iso

            # Append turn
            conv.history.append(
                TurnRecord(
                    turn_number=turn_number,
                    from_role=from_role,  # type: ignore
                    message=message,
                    timestamp=now_iso,
                )
            )

            # Record in merchant-level interaction state
            msg_hash = hash_text(message)
            mx_state.recent_message_hashes.append(msg_hash)
            if len(mx_state.recent_message_hashes) > 20:
                mx_state.recent_message_hashes.pop(0)

            mx_state.repeated_auto_reply_hashes[msg_hash] = (
                mx_state.repeated_auto_reply_hashes.get(msg_hash, 0) + 1
            )
            mx_state.last_contact_at = now_iso

            return conv, mx_state

    def get_or_create_merchant_state(self, merchant_id: str) -> MerchantInteractionState:
        with self._lock:
            if merchant_id not in self._merchant_states:
                self._merchant_states[merchant_id] = MerchantInteractionState(
                    merchant_id=merchant_id
                )
            return self._merchant_states[merchant_id]

    def clear(self):
        with self._lock:
            self._conversations.clear()
            self._merchant_states.clear()


# Global singleton instance
conversation_store = ConversationStore()
