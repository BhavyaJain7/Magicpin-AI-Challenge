"""Deterministic pre-LLM intent detection."""

import re
from typing import Tuple
from app.models.conversation import IntentEnum

# Common canned WhatsApp Business phrases
CANNED_PHRASES = [
    "thank you for contacting",
    "thanks for contacting",
    "our team will respond",
    "will get back to you",
    "currently unavailable",
    "we have received your message",
    "thank you for reaching out",
    "auto-reply",
    "automated response",
    "business hours are",
]

# Explicit commitment triggers
COMMITMENT_PATTERNS = [
    r"\b(yes\s+)?(let'?s\s+do\s+it|lets\s+do\s+it)\b",
    r"\bwhat'?s\s+next\b",
    r"\bhow\s+do\s+i\s+sign\s+up\b",
    r"\b(i\s+want\s+to\s+join|proceed|go\s+ahead|start\s+now|sign\s+me\s+up)\b",
    r"\b(yes\s+please|confirm|i'?m\s+ready|let'?s\s+start)\b",
    r"\b(send\s+me\s+the\s+abstract|send\s+the\s+draft|draft\s+it)\b",
]

# Stop / opt-out triggers
STOP_PATTERNS = [
    r"\b(stop|unsubscribe|cancel|opt\s*out|quit)\b",
]

# Hostility / complaint triggers
HOSTILE_PATTERNS = [
    r"\b(useless\s+spam|stop\s+messaging|stop\s+spamming|harassment|leave\s+me\s+alone|don'?t\s+message)\b",
    r"\b(annoying|scam|fraud|terrible|horrible|go\s+away)\b",
]

# Rejection triggers
NOT_INTERESTED_PATTERNS = [
    r"\b(not\s+interested|no\s+thanks|no\s+need|don'?t\s+need|pass)\b",
]


class IntentDetector:
    """Classifies incoming messages into distinct intents before invoking LLMs."""

    @staticmethod
    def detect_intent(message: str) -> Tuple[IntentEnum, float]:
        """Classify message text. Returns (IntentEnum, confidence: 0.0 - 1.0)."""
        clean = message.strip().lower()

        # 1. Stop / Opt-out
        for pat in STOP_PATTERNS:
            if re.search(pat, clean):
                return IntentEnum.STOP, 1.0

        # 2. Hostility
        for pat in HOSTILE_PATTERNS:
            if re.search(pat, clean):
                return IntentEnum.HOSTILE, 0.95

        # 3. Not Interested
        for pat in NOT_INTERESTED_PATTERNS:
            if re.search(pat, clean):
                return IntentEnum.NOT_INTERESTED, 0.90

        # 4. Positive Commitment
        for pat in COMMITMENT_PATTERNS:
            if re.search(pat, clean):
                return IntentEnum.POSITIVE_COMMITMENT, 0.95

        # 5. Canned phrases
        for phrase in CANNED_PHRASES:
            if phrase in clean:
                return IntentEnum.AUTO_REPLY, 0.90

        # 6. Question
        if clean.endswith("?") or any(clean.startswith(w) for w in ["what", "how", "why", "when", "where", "can you", "could you"]):
            return IntentEnum.QUESTION, 0.85

        return IntentEnum.UNKNOWN, 0.50
