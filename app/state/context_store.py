"""Context store implementation with strict version gating and scope tracking."""

import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from app.models.responses import ContextCounts


class StaleVersionError(Exception):
    def __init__(self, current_version: int):
        self.current_version = current_version
        super().__init__(f"Stale version provided. Current version is {current_version}")


class ContextStore:
    """Thread-safe context store supporting category, merchant, customer, and trigger contexts.
    Enforces atomic replace and idempotent versioning per (scope, context_id).
    """

    def __init__(self):
        self._lock = threading.RLock()
        # Storage structure: {scope: {context_id: (version, payload, stored_at)}}
        self._store: Dict[str, Dict[str, Tuple[int, Dict[str, Any], str]]] = {
            "category": {},
            "merchant": {},
            "customer": {},
            "trigger": {},
        }

    def put(
        self, scope: str, context_id: str, version: int, payload: Dict[str, Any]
    ) -> Tuple[bool, str, str]:
        """Store context payload with version enforcement.
        Returns (is_new_or_updated, ack_id, stored_at_iso).
        Raises StaleVersionError if incoming version < stored version.
        """
        with self._lock:
            if scope not in self._store:
                self._store[scope] = {}

            now_iso = datetime.now(timezone.utc).isoformat()
            ack_id = f"ack_{context_id}_v{version}"

            current = self._store[scope].get(context_id)
            if current is not None:
                current_version, _, _ = current
                if version < current_version:
                    raise StaleVersionError(current_version=current_version)
                if version == current_version:
                    # Idempotent no-op
                    return False, ack_id, now_iso

            # version > current_version or first time seeing context_id
            self._store[scope][context_id] = (version, payload, now_iso)
            return True, ack_id, now_iso

    def get(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored payload for a given scope and context_id."""
        with self._lock:
            entry = self._store.get(scope, {}).get(context_id)
            return entry[1] if entry else None

    def get_version(self, scope: str, context_id: str) -> Optional[int]:
        """Retrieve stored version number."""
        with self._lock:
            entry = self._store.get(scope, {}).get(context_id)
            return entry[0] if entry else None

    def exists(self, scope: str, context_id: str) -> bool:
        with self._lock:
            return context_id in self._store.get(scope, {})

    def counts(self) -> ContextCounts:
        """Return counts of loaded contexts across all four scopes."""
        with self._lock:
            return ContextCounts(
                category=len(self._store.get("category", {})),
                merchant=len(self._store.get("merchant", {})),
                customer=len(self._store.get("customer", {})),
                trigger=len(self._store.get("trigger", {})),
            )

    def clear(self):
        """Reset store (useful in testing)."""
        with self._lock:
            for s in self._store:
                self._store[s].clear()


# Global singleton instance
context_store = ContextStore()
