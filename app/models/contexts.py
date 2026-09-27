"""Domain models for the 4-context architecture:
- CategoryContext
- MerchantContext
- CustomerContext
- TriggerContext
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    tone: Optional[str] = None
    register_tone: Optional[str] = Field(default=None, alias="register")
    code_mix: Optional[str] = None
    vocab_allowed: List[str] = Field(default_factory=list)
    vocab_taboo: List[str] = Field(default_factory=list)
    salutation_examples: List[str] = Field(default_factory=list)
    tone_examples: List[str] = Field(default_factory=list)


class OfferCatalogItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    value: Union[str, int, float] = ""
    audience: Optional[str] = None
    type: Optional[str] = None


class PeerStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scope: Optional[str] = None
    avg_rating: Optional[float] = None
    avg_review_count: Optional[int] = None
    avg_views_30d: Optional[int] = None
    avg_calls_30d: Optional[int] = None
    avg_directions_30d: Optional[int] = None
    avg_ctr: Optional[float] = None
    avg_photos: Optional[int] = None
    avg_post_freq_days: Optional[int] = None
    retention_6mo_pct: Optional[float] = None
    retention_3mo_pct: Optional[float] = None


class DigestItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    kind: Optional[str] = None
    title: str
    source: Optional[str] = None
    summary: Optional[str] = None
    actionable: Optional[str] = None
    trial_n: Optional[int] = None
    patient_segment: Optional[str] = None


class SeasonalBeat(BaseModel):
    model_config = ConfigDict(extra="ignore")
    month_range: Optional[str] = None
    note: Optional[str] = None


class TrendSignal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: Optional[str] = None
    delta_yoy: Optional[float] = None


class CategoryPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slug: str
    display_name: Optional[str] = None
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    offer_catalog: List[OfferCatalogItem] = Field(default_factory=list)
    peer_stats: PeerStats = Field(default_factory=PeerStats)
    digest: List[DigestItem] = Field(default_factory=list)
    patient_content_library: List[Dict[str, Any]] = Field(default_factory=list)
    seasonal_beats: List[SeasonalBeat] = Field(default_factory=list)
    trend_signals: List[TrendSignal] = Field(default_factory=list)


# --- Merchant Context Models ---

class MerchantIdentity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    city: Optional[str] = None
    locality: Optional[str] = None
    place_id: Optional[str] = None
    verified: bool = False
    languages: List[str] = Field(default_factory=list)
    owner_first_name: Optional[str] = None
    established_year: Optional[int] = None


class SubscriptionInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Optional[str] = None
    plan: Optional[str] = None
    days_remaining: Optional[int] = None
    renewed_at: Optional[str] = None


class PerformanceDelta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    views_pct: Optional[float] = None
    calls_pct: Optional[float] = None
    ctr_pct: Optional[float] = None


class MerchantPerformance(BaseModel):
    model_config = ConfigDict(extra="ignore")
    window_days: int = 30
    views: Optional[int] = None
    calls: Optional[int] = None
    directions: Optional[int] = None
    ctr: Optional[float] = None
    leads: Optional[int] = None
    delta_7d: Optional[PerformanceDelta] = None


class MerchantOffer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    status: Literal["active", "expired", "draft", "paused"] = "active"
    started: Optional[str] = None
    ended: Optional[str] = None


class ConversationHistoryTurn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ts: Optional[str] = None
    from_: Optional[str] = Field(default=None, alias="from")
    body: str = ""
    engagement: Optional[str] = None


class CustomerAggregate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    total_unique_ytd: Optional[int] = None
    lapsed_180d_plus: Optional[int] = None
    retention_6mo_pct: Optional[float] = None
    high_risk_adult_count: Optional[int] = None


class ReviewTheme(BaseModel):
    model_config = ConfigDict(extra="ignore")
    theme: str
    sentiment: Literal["pos", "neg", "neutral"] = "neutral"
    occurrences_30d: int = 0
    common_quote: Optional[str] = None


class MerchantPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    merchant_id: str
    category_slug: str
    identity: MerchantIdentity
    subscription: Optional[SubscriptionInfo] = None
    performance: Optional[MerchantPerformance] = None
    offers: List[MerchantOffer] = Field(default_factory=list)
    conversation_history: List[ConversationHistoryTurn] = Field(default_factory=list)
    customer_aggregate: Optional[CustomerAggregate] = None
    signals: List[str] = Field(default_factory=list)
    review_themes: List[ReviewTheme] = Field(default_factory=list)


# --- Customer Context Models ---

class CustomerIdentity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    phone_redacted: Optional[str] = None
    language_pref: Optional[str] = None
    age_band: Optional[str] = None


class CustomerRelationship(BaseModel):
    model_config = ConfigDict(extra="ignore")
    first_visit: Optional[str] = None
    last_visit: Optional[str] = None
    visits_total: int = 0
    services_received: List[str] = Field(default_factory=list)
    lifetime_value: Optional[float] = None
    favourite_dish: Optional[str] = None


class CustomerPreferences(BaseModel):
    model_config = ConfigDict(extra="ignore")
    preferred_slots: Optional[str] = None
    channel: str = "whatsapp"
    reminder_opt_in: bool = True
    preferred_stylist: Optional[str] = None
    wedding_date: Optional[str] = None


class CustomerConsent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    opted_in_at: Optional[str] = None
    scope: List[str] = Field(default_factory=list)


class CustomerPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_id: str
    merchant_id: str
    identity: CustomerIdentity
    relationship: Optional[CustomerRelationship] = None
    state: Optional[str] = None  # active, lapsed_soft, lapsed_hard, new
    preferences: Optional[CustomerPreferences] = None
    consent: Optional[CustomerConsent] = None


# --- Trigger Context Models ---

class TriggerPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    scope: Literal["merchant", "customer"]
    kind: str
    source: Literal["internal", "external"] = "internal"
    merchant_id: str
    customer_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    urgency: int = Field(ge=1, le=5, default=3)
    suppression_key: str
    expires_at: Optional[str] = None
