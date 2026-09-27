"""State and conversation tracking models for Phase 0."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ConversationStateEnum(str, Enum):
    NEW = "NEW"
    ENGAGED = "ENGAGED"
    ANSWERING = "ANSWERING"
    ACTION = "ACTION"
    AUTO_REPLY = "AUTO_REPLY"
    WAITING = "WAITING"
    ENDED = "ENDED"


class IntentEnum(str, Enum):
    STOP = "STOP"
    NOT_INTERESTED = "NOT_INTERESTED"
    POSITIVE_COMMITMENT = "POSITIVE_COMMITMENT"
    QUESTION = "QUESTION"
    INFORMATIONAL = "INFORMATIONAL"
    AUTO_REPLY = "AUTO_REPLY"
    HOSTILE = "HOSTILE"
    OFF_TOPIC = "OFF_TOPIC"
    UNKNOWN = "UNKNOWN"


class TurnRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    turn_number: int
    from_role: Literal["vera", "merchant", "customer"]
    message: str
    timestamp: str
    intent: Optional[str] = None


class ConversationState(BaseModel):
    """Per-conversation state tracking."""
    model_config = ConfigDict(extra="ignore")
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    turn_count: int = 0
    state: ConversationStateEnum = ConversationStateEnum.NEW
    detected_intent: Optional[IntentEnum] = None
    last_bot_message: Optional[str] = None
    last_received_at: Optional[str] = None
    session_started_at: Optional[str] = None
    language: Optional[str] = "en"
    auto_reply_count: int = 0
    last_trigger_id: Optional[str] = None
    ended: bool = False
    history: List[TurnRecord] = Field(default_factory=list)


class MerchantInteractionState(BaseModel):
    """Merchant-level state across conversations (crucial for auto-reply detection)."""
    model_config = ConfigDict(extra="ignore")
    merchant_id: str
    recent_message_hashes: List[str] = Field(default_factory=list)
    repeated_auto_reply_hashes: Dict[str, int] = Field(default_factory=dict)
    recent_triggers: List[str] = Field(default_factory=list)
    recent_suppression_keys: List[str] = Field(default_factory=list)
    last_contact_at: Optional[str] = None
    unsubscribed: bool = False
