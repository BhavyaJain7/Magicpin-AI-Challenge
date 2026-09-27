"""HTTP Response models according to challenge-testing-brief.md."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContextPushResponse(BaseModel):
    """200 response for POST /v1/context"""
    accepted: bool = True
    ack_id: str
    stored_at: str


class ContextConflictResponse(BaseModel):
    """409 conflict response for POST /v1/context"""
    accepted: bool = False
    reason: Literal["stale_version"] = "stale_version"
    current_version: int


class ProactiveAction(BaseModel):
    """Single action item in POST /v1/tick response."""
    model_config = ConfigDict(extra="ignore")
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: Literal["vera", "merchant_on_behalf"] = "vera"
    trigger_id: str
    template_name: Optional[str] = None
    template_params: List[Any] = Field(default_factory=list)
    body: str
    cta: Literal["binary", "open_ended", "choice", "none"] = "open_ended"
    suppression_key: str
    rationale: str


class TickResponse(BaseModel):
    """200 response for POST /v1/tick"""
    actions: List[ProactiveAction] = Field(default_factory=list)


class ReplyResponse(BaseModel):
    """200 response for POST /v1/reply"""
    model_config = ConfigDict(extra="ignore")
    action: Literal["send", "wait", "end"]
    body: Optional[str] = None
    cta: Optional[Literal["binary", "open_ended", "choice", "none"]] = None
    wait_seconds: Optional[int] = None
    rationale: str


class ContextCounts(BaseModel):
    category: int = 0
    merchant: int = 0
    customer: int = 0
    trigger: int = 0


class HealthResponse(BaseModel):
    """200 response for GET /v1/healthz"""
    status: Literal["ok"] = "ok"
    uptime_seconds: int = 0
    contexts_loaded: ContextCounts = Field(default_factory=ContextCounts)


class MetadataResponse(BaseModel):
    """200 response for GET /v1/metadata"""
    team_name: str
    team_members: List[str]
    model: str
    approach: str
    contact_email: str
    version: str
    submitted_at: str
