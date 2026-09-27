"""HTTP Request models according to challenge-testing-brief.md."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContextPushRequest(BaseModel):
    """POST /v1/context"""
    model_config = ConfigDict(extra="ignore")
    scope: Literal["category", "merchant", "customer", "trigger"]
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: Optional[str] = None


class TickRequest(BaseModel):
    """POST /v1/tick"""
    model_config = ConfigDict(extra="ignore")
    now: str
    available_triggers: List[str] = Field(default_factory=list)


class ReplyRequest(BaseModel):
    """POST /v1/reply"""
    model_config = ConfigDict(extra="ignore")
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    from_role: Literal["merchant", "customer"] = "merchant"
    message: str
    received_at: Optional[str] = None
    turn_number: int = 1
