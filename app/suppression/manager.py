"""Suppression and deduplication manager for proactive engagement."""

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from app.models.contexts import CustomerPayload, TriggerPayload
from app.state.conversation_store import hash_text


def parse_iso(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        # Normalize trailing Z to +00:00 for python fromisoformat
        clean = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None


class SuppressionManager:
    """Manages suppression keys, TTL expiration, message deduplication, and cooldowns."""

    def __init__(self, merchant_cooldown_seconds: int = 3600):
        self._lock = threading.RLock()
        self.merchant_cooldown_seconds = merchant_cooldown_seconds

        # Active suppression keys: {suppression_key: expiry_iso}
        self._suppressed_keys: Dict[str, Optional[str]] = {}

        # Outbound message hashes sent: {hash: timestamp_iso}
        self._sent_message_hashes: Dict[str, str] = {}

        # Last proactive outbound contact per merchant: {merchant_id: timestamp_iso}
        self._merchant_last_contact: Dict[str, str] = {}

        # Consumed triggers: set of trigger IDs
        self._consumed_triggers: Set[str] = set()

    def is_trigger_expired(self, trigger: TriggerPayload, now_iso: str) -> bool:
        """Check if trigger has expired relative to simulated now."""
        if not trigger.expires_at:
            return False

        now_dt = parse_iso(now_iso) or datetime.now(timezone.utc)
        exp_dt = parse_iso(trigger.expires_at)
        if not exp_dt:
            return False

        return now_dt > exp_dt

    def is_suppression_key_active(self, suppression_key: str, now_iso: str) -> bool:
        """Check if suppression key is currently active."""
        with self._lock:
            if suppression_key not in self._suppressed_keys:
                return False

            expiry_str = self._suppressed_keys[suppression_key]
            if not expiry_str:
                return True  # Indefinite suppression

            now_dt = parse_iso(now_iso) or datetime.now(timezone.utc)
            exp_dt = parse_iso(expiry_str)
            if not exp_dt:
                return True

            if now_dt > exp_dt:
                # Key expired, clean up
                del self._suppressed_keys[suppression_key]
                return False

            return True

    def is_consumed(self, trigger_id: str) -> bool:
        with self._lock:
            return trigger_id in self._consumed_triggers

    def is_merchant_in_cooldown(self, merchant_id: str, now_iso: str) -> bool:
        """Check if merchant was proactively contacted within cooldown window."""
        with self._lock:
            last_ts = self._merchant_last_contact.get(merchant_id)
            if not last_ts:
                return False

            now_dt = parse_iso(now_iso) or datetime.now(timezone.utc)
            last_dt = parse_iso(last_ts)
            if not last_dt:
                return False

            elapsed = (now_dt - last_dt).total_seconds()
            return elapsed < self.merchant_cooldown_seconds

    def has_duplicate_message(self, message_body: str) -> bool:
        """Check if an identical normalized message was previously generated."""
        msg_hash = hash_text(message_body)
        with self._lock:
            return msg_hash in self._sent_message_hashes

    def has_customer_consent(self, customer: CustomerPayload, trigger_kind: str) -> bool:
        """Verify that customer has active consent for this kind of outreach."""
        if not customer.consent:
            return False

        # Map trigger kinds to consent scopes
        kind_scope_map = {
            "recall_due": ["recall_reminders"],
            "appointment_tomorrow": ["appointment_reminders"],
            "wedding_package_followup": ["bridal_package_followup", "appointment_reminders"],
            "treatment_followup": ["treatment_followup"],
            "promotional": ["promotional_offers"],
        }

        required_scopes = kind_scope_map.get(trigger_kind, ["recall_reminders"])
        customer_scopes = set(customer.consent.scope)

        return any(req in customer_scopes for req in required_scopes)

    def record_proactive_send(
        self,
        trigger_id: str,
        suppression_key: str,
        merchant_id: str,
        message_body: str,
        now_iso: str,
        expiry_iso: Optional[str] = None,
    ):
        """Record that an action was executed to prevent repeat fires."""
        with self._lock:
            self._consumed_triggers.add(trigger_id)
            self._suppressed_keys[suppression_key] = expiry_iso
            self._merchant_last_contact[merchant_id] = now_iso

            msg_hash = hash_text(message_body)
            self._sent_message_hashes[msg_hash] = now_iso

    def clear(self):
        """Reset state (useful for tests)."""
        with self._lock:
            self._suppressed_keys.clear()
            self._sent_message_hashes.clear()
            self._merchant_last_contact.clear()
            self._consumed_triggers.clear()


# Global singleton instance
suppression_manager = SuppressionManager()
