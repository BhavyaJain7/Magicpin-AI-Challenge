"""Deterministic grounding validator and quality assurance layer."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.models.contexts import (
    CategoryPayload,
    CustomerPayload,
    MerchantPayload,
    TriggerPayload,
)

logger = logging.getLogger(__name__)


class GroundingValidator:
    """Validates composed messages against source contexts to prevent hallucinations and taboo terms."""

    @staticmethod
    def extract_numbers_and_metrics(text: str) -> Set[str]:
        """Extract numbers, percentages, and prices from text."""
        # Clean currency and comma separators
        normalized = text.replace(",", "")

        # Find percentages, prices, and digits
        found = set()
        # Percentages
        for p in re.findall(r"\b\d+%", normalized):
            found.add(p)
        # Currency prices (₹ or Rs)
        for c in re.findall(r"(?:₹|rs\.?)\s*(\d+)", normalized, re.IGNORECASE):
            found.add(c)
        # Standalone numbers
        for n in re.findall(r"\b\d+\b", normalized):
            found.add(n)

        return found

    @staticmethod
    def collect_allowed_numbers(
        category: CategoryPayload,
        merchant: MerchantPayload,
        trigger: TriggerPayload,
        customer: Optional[CustomerPayload] = None,
    ) -> Set[str]:
        """Collect all verifiable numbers present in the 4 contexts."""
        raw_dump = " ".join([
            json.dumps(category.model_dump()),
            json.dumps(merchant.model_dump()),
            json.dumps(trigger.model_dump()),
            json.dumps(customer.model_dump()) if customer else "",
        ])
        clean = raw_dump.replace(",", "")
        numbers = set(re.findall(r"\b\d+\b", clean))

        # Add common conversational single-digits that are structurally safe
        safe_common = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "24", "30", "90"}
        numbers.update(safe_common)

        return numbers

    @classmethod
    def validate_message(
        cls,
        body: str,
        category: CategoryPayload,
        merchant: MerchantPayload,
        trigger: TriggerPayload,
        customer: Optional[CustomerPayload] = None,
    ) -> Tuple[bool, List[str]]:
        """Run all grounding checks against body. Returns (is_valid, list_of_violations)."""
        violations = []
        body_lower = body.lower()

        # 1. Taboo Vocabulary Check
        if category.voice and category.voice.vocab_taboo:
            for taboo in category.voice.vocab_taboo:
                # Taboo phrases can be like "guaranteed" or "100% safe"
                # Strip parenthetical annotations if any (e.g., "(use only when actually applicable)")
                clean_taboo = re.sub(r"\(.*?\)", "", taboo).strip().lower()
                if clean_taboo and clean_taboo in body_lower:
                    violations.append(f"Prohibited category taboo phrase detected: '{clean_taboo}'")

        # 2. Numeric Grounding Check
        extracted_numbers = cls.extract_numbers_and_metrics(body)
        allowed_numbers = cls.collect_allowed_numbers(category, merchant, trigger, customer)

        for num in extracted_numbers:
            # Strip % or currency symbols to check bare number
            bare_num = re.sub(r"[^\d]", "", num)
            if bare_num and bare_num not in allowed_numbers:
                violations.append(f"Hallucinated numeric claim or unverified price/statistic: '{num}'")

        # 3. Source Citation Check (if research digest)
        if trigger.kind == "research_digest":
            digest_items = category.digest
            valid_sources = [d.source.lower() for d in digest_items if d.source]
            # Check if any citation claim matches a valid source
            has_valid_source = any(s.split()[0] in body_lower for s in valid_sources)
            if not has_valid_source and "jida" not in body_lower:
                violations.append("Research digest message missing verifiable source citation.")

        is_valid = len(violations) == 0
        return is_valid, violations
