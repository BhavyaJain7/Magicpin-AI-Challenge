# magicpin AI Challenge --- Vera Merchant AI Assistant

## Technical Analysis, Architecture, Implementation Plan, Judge Strategy & Recommended Tech Stack

**Document status:** Draft implementation plan\
**Audience:** Engineering team / challenge participants\
**Primary sources:** `challenge-brief.md`, `challenge-testing-brief.md`,
`engagement-design.md`, `engagement-research.md`, `judge_simulator.py`\
**Last consolidated:** 2026-09-27

------------------------------------------------------------------------

# 1. Executive Summary

The magicpin AI Challenge asks participants to build an AI assistant
that engages merchants over WhatsApp in the style of Vera, while
improving on known production weaknesses.

The implementation should **not** be treated as a prompt-only chatbot.
The supplied challenge and judge simulator together define a **stateful,
event-driven, context-grounded conversational system**.

The recommended architecture is:

``` text
Judge Harness
     |
     | HTTPS / JSON
     v
FastAPI API
     |
     +-----------------------------+
     |                             |
     v                             v
Context / State Layer        Conversation Layer
     |                             |
     +-------------+---------------+
                   |
                   v
             Trigger Router
                   |
                   v
           Context Assembler
                   |
                   v
            LLM Composer
                   |
                   v
          Deterministic Validator
                   |
                   v
              Action / Reply
```

The core engineering principle is:

> **The LLM should be responsible for language generation, not system
> correctness.**

Deterministic code should handle state, context versions, trigger
eligibility, suppression, session rules, intent transitions, auto-reply
detection, grounding validation and hard constraints. The LLM should
primarily handle natural-language composition.

The recommended initial stack is:

-   **Python 3.11**
-   **FastAPI**
-   **Uvicorn**
-   **Pydantic v2**
-   **Redis**
-   **PostgreSQL**
-   **httpx**
-   **Jinja2**
-   **Custom thin LLM abstraction**
-   **pytest / pytest-asyncio / respx**
-   **Docker**
-   **GitHub Actions**
-   Public HTTPS deployment such as **Render** or **Cloud Run**

A modular monolith is preferable to a microservice architecture for the
challenge.

------------------------------------------------------------------------

# 2. Challenge Understanding

## 2.1 Objective

Build an AI chatbot that engages and assists merchants on WhatsApp as
Vera does, using a common dataset and an AI judge to evaluate the
resulting messages and conversations.

The challenge provides four context layers:

1.  `CategoryContext`
2.  `MerchantContext`
3.  `TriggerContext`
4.  `CustomerContext`

The canonical composition operation is:

``` python
compose(
    category,
    merchant,
    trigger,
    customer=None
) -> ComposedMessage
```

The composed result contains:

-   message body
-   CTA
-   `send_as`
-   suppression key
-   rationale
-   template parameters when applicable

------------------------------------------------------------------------

# 3. Primary Product Opportunities

The challenge identifies four important weaknesses in the existing Vera
experience.

## 3.1 Auto-reply pollution

A large proportion of merchant replies may be WhatsApp Business canned
auto-replies.

The improved system should:

-   recognize repeated canned responses
-   avoid burning multiple turns
-   make at most a graceful attempt
-   exit or wait appropriately

## 3.2 Intent-handoff failures

When a merchant moves from qualification to commitment, the assistant
should immediately transition to action.

Example:

``` text
Merchant:
"Ok lets do it. Whats next?"
```

The assistant should **not** ask another qualification question.

## 3.3 Generic marketing copy

Generic:

``` text
"Get 10% off"
"Grow your business"
"Increase your sales"
```

should be replaced by context-specific service/price and
merchant-relevant messaging.

Example:

``` text
"Dental Cleaning @ ₹299"
"Haircut @ ₹99"
```

when such offers are actually present in context.

## 3.4 Low engagement frequency

Functional reminders alone do not provide enough opportunities for
repeated engagement.

The system should support:

-   curiosity-driven messages
-   knowledge-driven messages
-   performance insights
-   customer engagement
-   local events
-   research
-   seasonal opportunities
-   relevant business triggers

------------------------------------------------------------------------

# 4. Four-Context Framework

## 4.1 CategoryContext

Slow-changing knowledge about a business vertical.

``` text
CategoryContext
├── slug
├── offer_catalog
├── voice
├── peer_stats
├── digest
├── patient_content_library
├── seasonal_beats
└── trend_signals
```

Examples of category-specific information:

-   allowed vocabulary
-   taboo vocabulary
-   canonical service + price offers
-   peer benchmarks
-   research digest
-   patient/customer content
-   seasonal patterns
-   search trends

The category context should influence **how** the assistant speaks.

------------------------------------------------------------------------

## 4.2 MerchantContext

Current state of a particular merchant.

``` text
MerchantContext
├── merchant_id
├── identity
├── subscription
├── performance
├── offers
├── conversation_history
├── customer_aggregate
└── signals
```

It should influence:

-   personalization
-   performance claims
-   current offers
-   merchant name
-   locality
-   language preferences
-   recent conversation state
-   customer aggregates
-   relevant business signals

------------------------------------------------------------------------

## 4.3 TriggerContext

The event explaining why the message is being sent now.

``` text
TriggerContext
├── id
├── scope
├── kind
├── source
├── merchant_id
├── customer_id
├── payload
├── urgency
├── suppression_key
└── expires_at
```

Examples:

``` text
research_digest
perf_spike
perf_dip
milestone_reached
review_theme_emerged
recall_due
customer_lapsed_soft
appointment_tomorrow
festival_upcoming
weather_heatwave
local_news_event
competitor_opened
category_trend_movement
```

The trigger should answer:

> "Why is this message relevant right now?"

------------------------------------------------------------------------

## 4.4 CustomerContext

Used for customer-facing messages.

``` text
CustomerContext
├── customer_id
├── merchant_id
├── identity
├── relationship
├── state
├── preferences
└── consent
```

The system must not invent:

-   customer history
-   appointment times
-   offers
-   consent
-   service history

Only supplied context may be used.

------------------------------------------------------------------------

# 5. Judge / API Contract

The testing brief defines five endpoints.

  Endpoint             Purpose
  -------------------- -----------------------------------------
  `POST /v1/context`   Receive context pushes
  `POST /v1/tick`      Periodic wake-up / proactive engagement
  `POST /v1/reply`     Process merchant/customer reply
  `GET /v1/healthz`    Liveness
  `GET /v1/metadata`   Bot identity

All endpoints use HTTPS and JSON.

------------------------------------------------------------------------

# 6. `/v1/context`

## Request

``` json
{
  "scope": "category",
  "context_id": "dentists",
  "version": 3,
  "payload": {},
  "delivered_at": "2026-04-26T10:00:00Z"
}
```

## Required semantics

Context storage must be idempotent by:

``` text
(context_id, version)
```

Rules:

``` text
incoming version < stored
    -> 409 stale_version

incoming version == stored
    -> 200 accepted/no-op

incoming version > stored
    -> atomically replace stored context
```

The implementation should retain the latest valid context for the
duration of the test.

------------------------------------------------------------------------

# 7. `/v1/tick`

The judge calls this every simulated five minutes.

``` json
{
  "now": "2026-04-26T10:30:00Z",
  "available_triggers": [
    "trg_001",
    "trg_002"
  ]
}
```

The bot may return zero or more actions.

Recommended action structure:

``` json
{
  "conversation_id": "conv_001",
  "merchant_id": "m_001",
  "customer_id": null,
  "send_as": "vera",
  "trigger_id": "trg_001",
  "template_name": "vera_research_digest_v1",
  "template_params": [],
  "body": "...",
  "cta": "open_ended",
  "suppression_key": "research:dentists:2026-W17",
  "rationale": "..."
}
```

### Recommended behavior

Do not generate an action merely because a trigger exists.

Filter:

1.  missing trigger
2.  expired trigger
3.  already consumed trigger
4.  suppressed trigger
5.  missing required context
6.  inactive conversation constraints
7.  duplicate content
8.  merchant cooldown
9.  consent requirements for customer-facing sends

Then select the most appropriate eligible trigger.

A conservative default is:

``` text
maximum 1 proactive action per merchant per tick
```

The API permits an empty action list, so restraint is valid.

------------------------------------------------------------------------

# 8. `/v1/reply`

The judge supplies:

``` json
{
  "conversation_id": "conv_001",
  "merchant_id": "m_001",
  "customer_id": null,
  "from_role": "merchant",
  "message": "Yes, send me the abstract",
  "received_at": "2026-04-26T10:45:00Z",
  "turn_number": 2
}
```

The response may be:

### Send

``` json
{
  "action": "send",
  "body": "...",
  "cta": "open_ended",
  "rationale": "..."
}
```

### Wait

``` json
{
  "action": "wait",
  "wait_seconds": 1800,
  "rationale": "..."
}
```

### End

``` json
{
  "action": "end",
  "rationale": "..."
}
```

The response must be fast enough to stay comfortably inside the judge's
30-second timeout.

------------------------------------------------------------------------

# 9. `/v1/healthz`

Keep this endpoint extremely simple and reliable.

Recommended response:

``` json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "contexts_loaded": {
    "category": 5,
    "merchant": 50,
    "customer": 200,
    "trigger": 100
  }
}
```

Three consecutive health failures can disqualify a test slot, so health
must not depend on the LLM.

------------------------------------------------------------------------

# 10. `/v1/metadata`

Return:

``` json
{
  "team_name": "...",
  "team_members": [],
  "model": "...",
  "approach": "...",
  "contact_email": "...",
  "version": "...",
  "submitted_at": "..."
}
```

------------------------------------------------------------------------

# 11. Judge Lifecycle

## Phase 1 --- Warmup

The judge:

1.  calls `/healthz`
2.  calls `/metadata`
3.  pushes:
    -   5 categories
    -   50 merchants
    -   200 customers
4.  waits for settlement
5.  checks health again

Therefore the implementation must support at least the base 255 contexts
cleanly.

------------------------------------------------------------------------

## Phase 2 --- Test Window

The judge advances simulated time in five-minute ticks.

At each tick:

``` text
1. Push incremental contexts
2. Call /v1/tick
3. Inspect actions
4. Simulate merchant/customer response
5. Call /v1/reply
6. Continue up to five turns
```

------------------------------------------------------------------------

## Phase 3 --- Adaptive Context Injection

The judge intentionally changes the context after development.

It injects:

-   new digest items
-   updated performance snapshots
-   new triggers
-   customer contexts appearing mid-test
-   recall triggers

Therefore:

> Never preload the development dataset as immutable knowledge.

The current context store must always be authoritative.

------------------------------------------------------------------------

## Phase 4 --- Replay

The deep-dive scenarios include:

1.  auto-reply hell
2.  intent transition
3.  hostile/off-topic behavior

Conversation behavior is evaluated in multi-turn interactions.

------------------------------------------------------------------------

## Phase 5 --- Final Scoring

The testing brief aggregates:

-   Phase 2 message scores
-   Phase 3 adaptation
-   Phase 4 replay scores
-   operational penalties

------------------------------------------------------------------------

# 12. Evaluation Rubric

The primary LLM judge scores five dimensions, each from 0--10.

## 12.1 Specificity

Does the message contain verifiable facts?

Strong signals:

-   numbers
-   dates
-   times
-   prices
-   source names
-   peer statistics
-   specific headlines
-   actual merchant data

Avoid generic claims.

------------------------------------------------------------------------

## 12.2 Category Fit

Does the message match the business type?

Examples:

### Dentist

``` text
clinical / peer-oriented / technically appropriate
```

### Salon

``` text
warm / practical / friendly
```

### Restaurant

``` text
operator-to-operator
```

### Gym

``` text
coaching / motivational
```

The category voice should be injected into the composer.

------------------------------------------------------------------------

## 12.3 Merchant Fit

Personalize using actual merchant state:

-   name
-   owner name
-   locality
-   performance
-   active offers
-   customer aggregate
-   signals
-   language preference
-   conversation history

Do not fabricate merchant data.

------------------------------------------------------------------------

## 12.4 Trigger Relevance

The message must clearly communicate:

> why this message, why now?

A message about generic profile optimization should not be emitted when
the active trigger is a research digest unless the connection is
explicit.

------------------------------------------------------------------------

## 12.5 Engagement Compulsion

Useful levers include:

-   curiosity
-   social proof
-   loss aversion
-   effort externalization
-   low-friction action
-   single CTA
-   useful information
-   personalized opportunity

Use only the levers relevant to the context.

------------------------------------------------------------------------

# 13. Penalties

The simulator's LLM judge explicitly identifies:

``` text
fabricated data       -> penalty
internal jargon      -> penalty
```

Therefore the validator should detect both.

------------------------------------------------------------------------

# 14. Core Architecture

``` text
                     Judge Harness
                          |
                          | HTTP/JSON
                          v
                 +------------------+
                 |    FastAPI API   |
                 +--------+---------+
                          |
             +------------+-------------+
             |            |             |
             v            v             v
       Context Store  Conversation  Trigger Store
             |            |             |
             +------------+-------------+
                          |
                          v
                  Context Assembler
                          |
                          v
                    Trigger Router
                          |
                          v
                  Conversation Policy
                          |
                          v
                    LLM Composer
                          |
                          v
                  Grounding Validator
                          |
                    +-----+-----+
                    |           |
                   PASS        FAIL
                    |           |
                    v           v
                  Action     Repair/Fallback
```

------------------------------------------------------------------------

# 15. State Architecture

Use two levels of state.

## 15.1 Conversation-level state

``` text
ConversationState
├── conversation_id
├── merchant_id
├── customer_id
├── turn_count
├── last_bot_message
├── last_received_at
├── session_started_at
├── detected_intent
├── language
├── auto_reply_count
├── last_trigger_id
├── ended
└── history
```

## 15.2 Merchant-level interaction state

``` text
MerchantInteractionState
├── merchant_id
├── recent_message_hashes
├── repeated_auto_reply_hashes
├── recent_triggers
├── recent_suppression_keys
├── last_contact_at
├── unsubscribe_state
└── engagement history
```

The second layer is important because the local simulator's auto-reply
test can use different conversation IDs for repeated canned messages.
Auto-reply detection should therefore not depend exclusively on
`conversation_id`.

------------------------------------------------------------------------

# 16. Conversation State Machine

``` text
NEW
 |
 v
ENGAGED
 |
 +---- question ------> ANSWERING
 |
 +---- commitment ----> ACTION
 |
 +---- auto-reply ----> AUTO_REPLY
 |
 +---- not interested -> ENDED
 |
 +---- STOP ----------> ENDED
 |
 +---- unclear -------> ENGAGED
```

Recommended states:

``` text
NEW
ENGAGED
ANSWERING
ACTION
AUTO_REPLY
WAITING
ENDED
```

------------------------------------------------------------------------

# 17. Intent Detection

Implement deterministic intent detection before invoking the LLM.

Suggested classes:

``` text
STOP
NOT_INTERESTED
POSITIVE_COMMITMENT
QUESTION
INFORMATIONAL
AUTO_REPLY
HOSTILE
OFF_TOPIC
UNKNOWN
```

Examples of positive commitment:

``` text
"I want to join"
"yes let's do it"
"okay proceed"
"go ahead"
"how do I sign up?"
"let's start"
```

When positive commitment is detected:

``` text
qualification
     |
     v
action
```

Do not ask another qualifying question.

------------------------------------------------------------------------

# 18. Auto-Reply Detection

Use multiple signals.

## Signal 1 --- repeated exact text

``` text
same normalized message repeated >= 3 times
```

## Signal 2 --- canned phrase detection

Examples:

``` text
"Thank you for contacting..."
"Your message has been received..."
"Our team will respond..."
"We will get back to you..."
```

## Signal 3 --- semantic similarity

Compare incoming messages with recent merchant messages.

## Signal 4 --- no response to the actual question

If the assistant asks:

``` text
"Would you like me to set this up?"
```

and receives the exact same canned response repeatedly, classify it as
auto-reply.

## Recommended behavior

``` text
AUTO_REPLY detected
       |
       v
one graceful attempt
       |
       v
END / WAIT
```

Do not repeatedly send generated messages.

------------------------------------------------------------------------

# 19. Hostile and Off-Topic Handling

For explicit STOP:

``` text
STOP
 |
 v
END
```

For hostile but non-explicit responses:

``` text
brief apology
     |
     v
END or WAIT
```

For unrelated requests:

``` text
recognize scope
     |
     v
politely state supported scope
     |
     v
redirect
```

Do not hallucinate capabilities.

------------------------------------------------------------------------

# 20. Context Store

Recommended interface:

``` text
ContextStore
├── put(scope, context_id, version, payload)
├── get(scope, context_id)
├── get_version(scope, context_id)
├── exists(scope, context_id)
└── counts()
```

Internally:

``` text
(scope, context_id)
        |
        v
{
    version: N,
    payload: {...}
}
```

Redis is the recommended production implementation.

For the challenge, an in-memory implementation is also acceptable if
process lifetime is stable.

------------------------------------------------------------------------

# 21. Context Assembly

Never send raw HTTP payloads directly to the LLM.

Build:

``` text
CompositionContext
├── category
├── merchant
├── trigger
├── customer
└── conversation_state
```

Resolution:

``` text
trigger
   |
   +--> merchant_id
   |       |
   |       +--> MerchantContext
   |                  |
   |                  +--> category_slug
   |                           |
   |                           +--> CategoryContext
   |
   +--> customer_id
           |
           +--> CustomerContext
```

If required context is unavailable:

``` text
DO NOT INVENT IT
```

Either wait or select another eligible trigger.

------------------------------------------------------------------------

# 22. Trigger Router

Recommended trigger handlers:

``` text
research_digest
perf_spike
perf_dip
milestone_reached
review_theme_emerged
recall_due
customer_lapsed_soft
customer_lapsed_hard
appointment_tomorrow
festival
weather
local_news
competitor_opened
category_trend
curious_ask
```

Each handler should determine:

-   eligibility
-   required context
-   composition strategy
-   CTA policy
-   suppression key
-   cooldown

------------------------------------------------------------------------

# 23. Trigger Priority

Use an internal ranking function:

``` text
effective_priority =
    urgency
    + freshness
    + merchant_relevance
    + engagement_potential
    - recent_contact_penalty
```

This is an engineering heuristic for selecting among eligible triggers.

It should not override hard rules such as:

-   expired trigger
-   STOP state
-   missing consent
-   missing required context
-   duplicate suppression

------------------------------------------------------------------------

# 24. Suppression System

Create:

``` text
SuppressionManager
```

Check:

``` text
suppression_key
trigger expiry
recent trigger
recent message
duplicate message hash
merchant cooldown
conversation active
STOP state
```

Example:

``` text
research:dentists:2026-W17
```

should not repeatedly send the same research digest.

Normalize messages before hashing:

``` text
normalize(body)
      |
      v
SHA-256
      |
      v
recent_message_hash
```

------------------------------------------------------------------------

# 25. WhatsApp Session Logic

Maintain:

``` text
last_merchant_reply_at
last_customer_reply_at
```

Then:

``` text
if no active session:
    use approved template

elif within 24 hours of reply:
    free-form message
```

The challenge does not call Meta directly, but the internal model should
still preserve this distinction.

------------------------------------------------------------------------

# 26. LLM Architecture

Do not make the LLM the system controller.

Recommended abstraction:

``` python
class LLMClient:
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type
    ) -> dict:
        ...
```

Implement provider adapters:

``` text
LLMClient
├── OpenAIClient
├── AnthropicClient
├── GeminiClient
└── FallbackClient
```

This keeps provider switching inexpensive.

------------------------------------------------------------------------

# 27. Prompt Architecture

Avoid one enormous prompt.

Use:

``` text
System prompt
+
Global grounding rules
+
Trigger-specific instructions
+
Structured context
+
Conversation state
```

Example:

``` text
SYSTEM
You are Vera, a merchant AI assistant.

OBJECTIVE
Compose one concise WhatsApp message that provides useful,
context-grounded value and creates a natural next step.

GROUNDING
Only use facts explicitly present in the supplied context.
Never invent:
- statistics
- prices
- dates
- sources
- competitors
- offers
- appointments
- customer history

CATEGORY
Follow category voice and taboo rules.

MERCHANT
Personalize using actual merchant state.

TRIGGER
Explain why the message is relevant now.

CTA
Use at most one primary CTA.

CONVERSATION
Respect prior turns and current intent.
```

Then add a trigger-specific prompt variant.

------------------------------------------------------------------------

# 28. Prompt Versioning

Use:

``` text
composer_v1
composer_v2
composer_v3
```

and trigger variants:

``` text
research_digest_v1
performance_v1
recall_due_v1
conversation_v1
```

Record:

``` text
composer_version
prompt_variant
model
model_version
context_versions
trigger_id
conversation_id
```

This allows replay and debugging.

------------------------------------------------------------------------

# 29. Prompt File Structure

Recommended:

``` text
prompts/
├── base.jinja2
├── merchant/
│   ├── research_digest.jinja2
│   ├── performance.jinja2
│   ├── milestone.jinja2
│   └── competitor.jinja2
│
├── customer/
│   ├── recall_due.jinja2
│   ├── appointment.jinja2
│   └── lapse.jinja2
│
└── conversation/
    ├── positive_intent.jinja2
    ├── question.jinja2
    └── general.jinja2
```

------------------------------------------------------------------------

# 30. Structured LLM Output

The internal model should return structured data:

``` json
{
  "body": "...",
  "cta": "open_ended",
  "send_as": "vera",
  "template_params": [],
  "reasoning_tags": [
    "specificity",
    "merchant_personalization",
    "curiosity"
  ]
}
```

Then deterministic code validates the result.

------------------------------------------------------------------------

# 31. Grounding Validator

Validate generated messages against context.

## Numeric validation

If output contains:

``` text
38%
₹299
2410
22 days
6 PM
```

verify each value exists in supplied context or is an allowed derived
value.

## Entity validation

Check:

-   merchant name
-   customer name
-   locality
-   source
-   competitor

## Offer validation

Only active offers should be presented as current offers.

## Source validation

If output says:

``` text
"JIDA says..."
```

the source must exist in the category digest.

## Taboo validation

Reject category-prohibited claims.

------------------------------------------------------------------------

# 32. Regeneration

Recommended:

``` text
LLM
 |
 v
Validator
 |
 +---- PASS ----> return
 |
 +---- FAIL
        |
        v
   repair prompt
        |
        v
    Validator
        |
     +--+--+
     |     |
   PASS   FAIL
     |     |
   return fallback
```

Maximum two LLM attempts.

A safe deterministic fallback is preferable to an invented answer.

------------------------------------------------------------------------

# 33. Message Construction Pattern

A strong general pattern is:

``` text
PERSONALIZED HOOK
+
VERIFIABLE FACT
+
WHY IT MATTERS NOW
+
LOW-FRICTION NEXT STEP
```

Example:

``` text
Dr. Meera, JIDA's latest issue has one finding relevant
to your high-risk adult cohort: ...

I can pull the abstract and turn it into a short
patient WhatsApp for your clinic. Want me to?
```

This naturally addresses:

-   specificity
-   category fit
-   merchant fit
-   trigger relevance
-   engagement

------------------------------------------------------------------------

# 34. CTA Policy

## Action trigger

Prefer:

``` text
YES
```

or one clear open-ended ask.

## Information trigger

No CTA is acceptable.

## Avoid

``` text
Yes for A
No for B
Maybe for C
```

The message should have one primary next step.

------------------------------------------------------------------------

# 35. Customer-Facing Composition

Use the same composer architecture:

``` text
Category
+
Merchant
+
Trigger
+
Customer
```

Customer-specific factors:

-   language preference
-   relationship
-   services
-   lapse state
-   preferred slots
-   consent

must influence the output.

Customer consent should be treated as a hard eligibility condition.

------------------------------------------------------------------------

# 36. Recommended Technology Stack

## 36.1 Application

  Technology      Recommendation
  --------------- -------------------
  Language        Python 3.11
  API             FastAPI
  ASGI server     Uvicorn
  Validation      Pydantic v2
  Configuration   pydantic-settings
  HTTP            httpx
  Templates       Jinja2

------------------------------------------------------------------------

## 36.2 State and storage

  Technology   Purpose
  ------------ -----------------------------------------------------------
  Redis        hot state, context cache, suppression, conversation state
  PostgreSQL   audit logs, message history, evaluation/replay data

PostgreSQL should not be on the critical request path for the initial
implementation.

------------------------------------------------------------------------

## 36.3 LLM

Use a thin provider abstraction:

``` text
OpenAI
Anthropic
Gemini
```

Do not make LangChain a core dependency initially.

Do not use a vector database initially.

------------------------------------------------------------------------

## 36.4 Testing

``` text
pytest
pytest-asyncio
httpx
respx
```

Use the supplied judge simulator as an external acceptance test.

------------------------------------------------------------------------

## 36.5 Deployment

``` text
Docker
GitHub Actions
Public HTTPS deployment
```

Possible hosting:

-   Render
-   Google Cloud Run
-   Railway
-   Fly.io

For challenge simplicity, Render or Cloud Run are reasonable choices.

------------------------------------------------------------------------

# 37. Technologies Explicitly Not Recommended Initially

  -----------------------------------------------------------------------
  Technology              Decision                Reason
  ----------------------- ----------------------- -----------------------
  LangChain               No                      unnecessary abstraction

  LangGraph               No initially            explicit state machine
                                                  is sufficient

  Celery                  No                      no background workload
                                                  required initially

  Kafka                   No                      excessive for challenge
                                                  scale

  Kubernetes              No                      operational overhead

  Vector DB               No                      judge supplies
                                                  structured context

  Elasticsearch           No                      unnecessary

  MongoDB                 No                      PostgreSQL is
                                                  sufficient

  Microservices           No                      modular monolith is
                                                  simpler

  Heavy ML intent         No initially            deterministic + LLM
  classifier                                      fallback is sufficient
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 38. Repository Structure

``` text
vera-bot/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── context.py
│   │   ├── tick.py
│   │   ├── reply.py
│   │   ├── health.py
│   │   └── metadata.py
│   │
│   ├── models/
│   │   ├── contexts.py
│   │   ├── requests.py
│   │   ├── responses.py
│   │   └── conversation.py
│   │
│   ├── state/
│   │   ├── context_store.py
│   │   ├── conversation_store.py
│   │   └── trigger_store.py
│   │
│   ├── engagement/
│   │   ├── composer.py
│   │   ├── router.py
│   │   ├── policies.py
│   │   ├── prompts.py
│   │   └── validator.py
│   │
│   ├── conversation/
│   │   ├── state_machine.py
│   │   ├── intent.py
│   │   ├── auto_reply.py
│   │   └── language.py
│   │
│   ├── suppression/
│   │   └── manager.py
│   │
│   ├── llm/
│   │   ├── client.py
│   │   ├── primary.py
│   │   └── fallback.py
│   │
│   └── config.py
│
├── prompts/
│   ├── base.jinja2
│   ├── merchant/
│   ├── customer/
│   └── conversation/
│
├── tests/
│   ├── api/
│   ├── state/
│   ├── conversation/
│   ├── validation/
│   ├── composition/
│   └── integration/
│
├── judge_simulator.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

------------------------------------------------------------------------

# 39. API Processing Flow

## `/v1/context`

``` text
Request
  |
  v
Validate schema
  |
  v
Check version
  |
  +--> stale -> 409
  |
  +--> same -> 200 no-op
  |
  +--> newer -> atomic replace
  |
  v
Return acknowledgement
```

## `/v1/tick`

``` text
Request
  |
  v
Load active triggers
  |
  v
Filter invalid/expired/suppressed
  |
  v
Resolve merchant/category/customer
  |
  v
Check eligibility
  |
  v
Rank triggers
  |
  v
Compose
  |
  v
Validate
  |
  v
Persist interaction state
  |
  v
Return actions
```

## `/v1/reply`

``` text
Request
  |
  v
Load conversation
  |
  +--> missing -> initialize fallback state
  |
  v
Store incoming message
  |
  v
Intent detection
  |
  +--> STOP
  +--> AUTO_REPLY
  +--> COMMITMENT
  +--> HOSTILE
  +--> OFF_TOPIC
  +--> QUESTION
  +--> UNKNOWN
  |
  v
Conversation policy
  |
  v
LLM if needed
  |
  v
Validate
  |
  v
Return send/wait/end
```

------------------------------------------------------------------------

# 40. Performance Targets

The judge timeout is 30 seconds per request.

Recommended internal targets:

  Operation             Target
  ----------------- ----------
  `/healthz`           \<50 ms
  `/metadata`          \<50 ms
  `/context`          \<100 ms
  `/tick`, no LLM     \<100 ms
  `/tick`, LLM        \<5--8 s
  `/reply`, LLM       \<5--8 s
  validation          \<100 ms

Never design around the full 30-second timeout.

------------------------------------------------------------------------

# 41. Testing Strategy

## Layer 1 --- API Contract

Test:

-   valid context
-   malformed context
-   duplicate version
-   stale version
-   newer version
-   missing fields
-   unknown trigger
-   unknown merchant
-   unknown conversation
-   expired trigger

------------------------------------------------------------------------

## Layer 2 --- Deterministic Policy

Test:

``` text
test_stop_detection
test_positive_intent_detection
test_auto_reply_detection
test_trigger_expiry
test_suppression
test_24h_window
test_customer_consent
test_offer_validation
test_hallucinated_number_detection
test_duplicate_message_detection
```

These should not require an LLM.

------------------------------------------------------------------------

## Layer 3 --- Composition

Create golden scenarios:

``` text
dentist + research_digest
dentist + perf_dip
dentist + perf_spike
salon + milestone
restaurant + festival
customer + recall_due
```

Avoid exact-string assertions.

Assert:

-   relevant fact included
-   trigger represented
-   merchant personalization
-   no fabricated facts
-   correct CTA
-   no taboo terms
-   appropriate category voice

------------------------------------------------------------------------

## Layer 4 --- Judge Simulator

Run:

``` bash
python judge_simulator.py
```

Scenarios:

``` text
warmup
phase2_short
auto_reply_hell
intent_transition
hostile
all
full_evaluation
```

------------------------------------------------------------------------

# 42. Simulator-Specific Findings

## 42.1 Auto-reply test

The local simulator can use different conversation IDs for repeated
auto-replies.

Therefore:

``` text
Do not detect auto-reply only per conversation_id.
```

Use merchant-level interaction history.

------------------------------------------------------------------------

## 42.2 Unknown conversation test

The simulator's intent test can call `/v1/reply` without fully
establishing the preceding conversation.

Therefore:

``` text
Unknown conversation ID
        |
        v
create fallback state
        |
        v
classify current message
        |
        v
respond
```

Do not return a server error solely because the conversation does not
already exist.

------------------------------------------------------------------------

# 43. Recommended Implementation Phases

## Phase 0 --- Contract Freeze

Deliver:

-   endpoint schemas
-   context schemas
-   action schemas
-   error schemas
-   state-machine specification
-   simulator observations
-   acceptance criteria

Do not optimize prompts yet.

------------------------------------------------------------------------

## Phase 1 --- API + State Foundation

Implement:

-   FastAPI
-   all five endpoints
-   context store
-   versioning
-   conversation store
-   basic health/metadata

Exit criteria:

-   warmup passes
-   all 255 base contexts load
-   versioning works
-   API is stable

------------------------------------------------------------------------

## Phase 2 --- Trigger + Suppression

Implement:

-   trigger resolution
-   expiration
-   suppression
-   deduplication
-   cooldown
-   trigger selection
-   session state

Exit criteria:

-   same trigger cannot repeatedly fire
-   expired triggers cannot fire
-   duplicate messages are suppressed

------------------------------------------------------------------------

## Phase 3 --- Conversation Intelligence

Implement:

-   intent detector
-   STOP detector
-   positive commitment detector
-   auto-reply detector
-   hostile detector
-   off-topic detector
-   language detector
-   state machine

Exit criteria:

``` text
auto_reply_hell
intent_transition
hostile
```

behave correctly.

------------------------------------------------------------------------

## Phase 4 --- LLM Composer

Implement:

-   base prompt
-   trigger-specific prompts
-   structured output
-   context assembly
-   CTA logic
-   rationale

Start with:

``` text
research_digest
perf_spike
perf_dip
milestone_reached
recall_due
```

------------------------------------------------------------------------

## Phase 5 --- Grounding + Quality

Implement:

-   numeric validation
-   entity validation
-   source validation
-   offer validation
-   taboo validation
-   duplicate detection
-   CTA validation
-   regeneration
-   deterministic fallback

------------------------------------------------------------------------

## Phase 6 --- Adaptive Context

Test:

``` text
category v1 -> v2
merchant v1 -> v2
new customer context
new trigger
changed performance
new digest item
```

Ensure the newest context is used.

------------------------------------------------------------------------

## Phase 7 --- Judge Optimization

Repeatedly run:

``` text
phase2_short
full_evaluation
```

Track:

``` text
specificity
category fit
merchant fit
trigger relevance
engagement
penalties
latency
```

Optimize from message-level failure analysis rather than only aggregate
averages.

------------------------------------------------------------------------

# 44. Definition of Done

## API

-   [ ] All five endpoints implemented
-   [ ] Request validation implemented
-   [ ] Correct HTTP status codes
-   [ ] `/healthz` independent of LLM
-   [ ] `/metadata` implemented

## State

-   [ ] 255 base contexts supported
-   [ ] Context persistence
-   [ ] Versioning
-   [ ] Stale-version handling
-   [ ] Conversation persistence
-   [ ] Merchant-level interaction state

## Engagement

-   [ ] Trigger routing
-   [ ] Suppression
-   [ ] Expiration
-   [ ] Deduplication
-   [ ] Cooldowns
-   [ ] 24-hour session logic

## Conversation

-   [ ] Auto-reply detection
-   [ ] Positive intent transition
-   [ ] STOP handling
-   [ ] Not-interested handling
-   [ ] Hostile handling
-   [ ] Off-topic handling
-   [ ] Unknown conversation recovery
-   [ ] Language adaptation

## LLM

-   [ ] Provider abstraction
-   [ ] Structured output
-   [ ] Trigger-specific prompts
-   [ ] Grounding
-   [ ] Validation
-   [ ] Regeneration
-   [ ] Fallback

## Evaluation

-   [ ] Warmup passes
-   [ ] Phase 2 passes
-   [ ] Auto-reply scenario passes
-   [ ] Intent transition passes
-   [ ] Hostile scenario passes
-   [ ] Full evaluation runs
-   [ ] Adaptive context tested
-   [ ] Latency measured

------------------------------------------------------------------------

# 45. Engineering Principles

## Principle 1 --- Deterministic code controls correctness

LLM:

``` text
wording
tone
phrasing
naturalness
```

Code:

``` text
state
eligibility
consent
suppression
context
intent
grounding
```

------------------------------------------------------------------------

## Principle 2 --- Current context is authoritative

Never assume development data remains current.

The judge deliberately changes context after submission.

------------------------------------------------------------------------

## Principle 3 --- Missing information must remain missing

Never fill gaps with plausible facts.

If the system does not know:

``` text
price
appointment
customer history
competitor
research result
```

it must not invent it.

------------------------------------------------------------------------

## Principle 4 --- Fewer high-quality messages are preferable to spam

The system should be comfortable returning:

``` json
{
  "actions": []
}
```

when nothing is sufficiently relevant.

------------------------------------------------------------------------

## Principle 5 --- Every outbound message needs a reason

The trigger must explain:

``` text
why this merchant
why this message
why now
```

------------------------------------------------------------------------

## Principle 6 --- Conversation transitions must be explicit

Do not rely solely on the LLM to remember:

``` text
qualification -> commitment -> action
```

Represent it as application state.

------------------------------------------------------------------------

# 46. Final Recommended Stack

``` text
                    ┌─────────────────────┐
                    │     Judge Harness   │
                    └──────────┬──────────┘
                               │
                         HTTPS / JSON
                               │
                               v
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │      Python 3.11    │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             v                 v                 v
          Redis           PostgreSQL         LLM API
        hot state        audit/history      provider
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               v
                     Composer + Validator
                               │
                               v
                         Docker / HTTPS
```

### Core dependencies

``` text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
httpx
redis
asyncpg
jinja2
structlog
python-dotenv

pytest
pytest-asyncio
respx
```

------------------------------------------------------------------------

# 47. Final Recommendation

The implementation should be a **Python/FastAPI modular monolith with
Redis-backed operational state, PostgreSQL for durable audit/replay
data, a thin provider-independent LLM layer, deterministic
conversation/trigger policy, and a strict grounding validator**.

The highest engineering priority is not adding more AI infrastructure.
It is ensuring that:

``` text
Context
   ↓
Correct current version
   ↓
Correct trigger
   ↓
Correct merchant/customer
   ↓
Correct conversation state
   ↓
Grounded message
   ↓
Validated action
```

This architecture directly addresses the challenge's scoring dimensions
while also satisfying the judge's operational requirements around
statefulness, incremental context updates, proactive ticks, multi-turn
replies, auto-reply detection, intent transitions, and graceful exits.

------------------------------------------------------------------------

# 48. Source Documents

This implementation plan is based primarily on:

1.  `challenge-brief.md`
    -   product definition
    -   four-context framework
    -   composition contract
    -   evaluation rubric
    -   engagement requirements
2.  `challenge-testing-brief.md`
    -   HTTP API contract
    -   judge lifecycle
    -   context versioning
    -   rate limits
    -   timeouts
    -   adaptive context injection
    -   replay scenarios
3.  `engagement-design.md`
    -   Category/Merchant/Trigger/Customer architecture
    -   composer design
    -   trigger families
    -   suppression
    -   engagement loops
    -   prompt versioning
4.  `engagement-research.md`
    -   existing Vera data-access architecture
    -   Redis usage
    -   existing merchant/customer state
    -   missing abstractions
    -   operational risks
5.  `judge_simulator.py`
    -   executable local judge behavior
    -   scoring implementation
    -   available scenarios
    -   simulator-specific edge cases

------------------------------------------------------------------------

# 49. Immediate Next Steps

The recommended implementation sequence is:

``` text
1. Create FastAPI project
2. Define all Pydantic schemas
3. Implement ContextStore
4. Implement /v1/context
5. Implement ConversationStore
6. Implement /v1/reply skeleton
7. Implement /v1/tick skeleton
8. Implement suppression
9. Implement intent + auto-reply detection
10. Run simulator warmup
11. Implement first LLM composer
12. Add grounding validator
13. Implement trigger-specific prompts
14. Run phase2_short
15. Fix judge failures
16. Run replay scenarios
17. Run full evaluation
18. Containerize
19. Deploy public HTTPS endpoint
20. Run final end-to-end judge validation
```

**Target architecture:** modular monolith first, provider-independent
LLM layer, deterministic policy around the LLM, Redis for operational
state, PostgreSQL for audit/replay, and Dockerized public HTTPS
deployment.
