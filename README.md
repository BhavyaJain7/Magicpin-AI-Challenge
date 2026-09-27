# magicpin Vera — Autonomous Merchant AI Assistant

An intelligent, context-grounded conversational agent for merchant engagement and campaign management on WhatsApp. Vera solves high-stakes operational challenges—including **automated auto-reply loops ("auto-reply hell")**, **premature re-qualification upon commitment**, **hallucination of unverified metrics**, and **trigger suppression violations**—by combining deterministic state machines with LLM composition.

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/framework-FastAPI-005571.svg)](https://fastapi.tiangolo.com)
[![Tests Passing](https://img.shields.io/badge/tests-31%2F31%20passing-brightgreen.svg)]()
[![LLM Judge Benchmark](https://img.shields.io/badge/LLM%20Judge-100%25%20Passed-success.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

---

## 🚀 Live Deployment & API Probes

- **Live URL**: `https://magicpin-vera-bot-7zg3.onrender.com`
- **Interactive Swagger Docs**: `https://magicpin-vera-bot-7zg3.onrender.com/docs`
- **Health Check**: `GET https://magicpin-vera-bot-7zg3.onrender.com/v1/healthz`
- **Metadata**: `GET https://magicpin-vera-bot-7zg3.onrender.com/v1/metadata`

---

## 🎯 Architecture Overview

```
                      WhatsApp / Judge Harness
                                 │
                                 ▼
                     FastAPI Application (/v1)
                                 │
        ┌────────────────────────┴────────────────────────┐
        ▼                                                 ▼
Context Store & State                           Intent Classifier
(Version Gating, TTL)                                     │
        │                                                 ▼
        ▼                                      Deterministic State Machine
Trigger Routing Engine                         (Auto-Reply / Handoff / Opt-Out)
(Suppression, Expiry, Consent)                            │
        │                                                 │
        └────────────────────────┬────────────────────────┘
                                 ▼
                      4-Context LLM Composer
                    (Jinja2 + Gemini / OpenAI)
                                 │
                                 ▼
                     Grounding & Safety Guard
                  (Regex numbers & Taboo filter)
                                 │
                                 ▼
                     Action / Outbound Message
```

### Core Engineering Principles
1. **The LLM never makes business decisions:** Policy, suppression, routing, and intent transitions are handled deterministically in pure code.
2. **Context Grounding:** Prompts compile 4 distinct data layers: `CategoryContext`, `MerchantContext`, `CustomerContext`, and `TriggerContext`.
3. **Safety & Zero Hallucination:** A regex-based post-validator ensures every numeric claim exists in the source context and immediately rejects taboo words (`guaranteed`, `free`, `promise`).

---

## 🛠️ Key Capabilities & Problem Solvers

| Feature | Challenge Problem | Solution Implementation |
|---|---|---|
| **Auto-Reply Hell Defense** | WhatsApp canned messages like *"Thanks for contacting us"* burn conversation turns. | Fingerprints message content and timestamps. On Turn 1, issues a polite backoff (`wait_seconds: 1800`). If repeated, transitions to `ENDED` without burning further turns. |
| **Instant Action on Commitment** | Merchants saying *"Ok let's do it"* get stuck in endless re-qualification loops. | Detects `POSITIVE_COMMITMENT` with top priority, switches directly to `ACTION` state with immediate execution verbiage (`done`, `proceeding`), and strictly avoids asking qualifying questions. |
| **Strict Anti-Spam & Suppression** | Merchants spammed repeatedly across hours or days. | Enforces suppression keys (`merchant_id:category:trigger_type`), 24h quiet periods, and a strict rule of $\le 1$ action per merchant per tick. |
| **Grounding Validator** | LLM hallucinating fake discount percentages or unverified customer counts. | Extracts all numbers from generated text and verifies them against ground truth context payloads. Triggers 2-pass repair or deterministic fallback on violation. |
| **Zero Version Rollbacks** | Network race conditions pushing stale context. | Strict monotonic version comparison: rejects `v_old < v_current` with HTTP `409 Conflict`, accepts `v_new > v_current` with `200 OK`. |

---

## 📁 Project Structure

```
.
├── app/
│   ├── api/                 # API route handlers (/v1/healthz, /v1/metadata, /v1/context, /v1/tick, /v1/reply)
│   ├── config.py            # Pydantic v2 settings loaded from .env
│   ├── conversation/        # State machine, intent classification, and auto-reply heuristics
│   ├── engagement/          # Trigger scoring, candidate ranking, suppression manager, and grounding validator
│   ├── llm/                 # LLM client abstractions (Gemini, OpenAI, Mock) with retry logic
│   ├── models/              # Pydantic contract models (contexts, requests, responses)
│   ├── state/               # In-memory and Redis-ready state store
│   └── main.py              # FastAPI application bootstrap
├── dataset/                 # Evaluation dataset (categories, merchants, triggers)
├── prompts/                 # Jinja2 prompt templates
├── tests/                   # 31 comprehensive test cases across Phases 0–6
├── decisions.md             # Complete architectural decision log (D-01 to D-30, D-P0-01 to D-P7-07)
├── implementation.md        # Detailed engineering and architecture roadmap
├── Dockerfile               # Production container image
├── docker-compose.yml       # Monolith + Redis service orchestration
├── judge_simulator.py       # Official challenge evaluation harness
└── requirements.txt         # Pinned production dependencies
```

---

## 🚀 Quickstart & Setup

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/BhavyaJain7/Magicpin-AI-Challenge.git
cd Magicpin-AI-Challenge
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Create a `.env` file in the root directory:
```env
BOT_URL=http://localhost:8080
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.8-flash
LLM_API_KEY=your_gemini_api_key_here
```

### 3. Run Locally
```bash
python -m uvicorn app.main:app --port 8080 --reload
```
Visit `http://localhost:8080/docs` to inspect and test the interactive OpenAPI documentation.

### 4. Run with Docker Compose
```bash
docker compose up --build
```

---

## 🧪 Testing & Evaluation

### Run Automated Unit & Integration Tests (100% Pass)
```bash
pytest tests/ -v
```
Output:
```
============================= 31 passed in 17.59s =============================
```

### Run Full Challenge Benchmark (LLM Judge)
```bash
python judge_simulator.py
```
Output:
```
--- SCENARIO RESULTS ---
[PASS] warmup
[PASS] auto_reply
[PASS] intent
[PASS] hostile
```

---

## 📚 Documentation
- [`decisions.md`](decisions.md): Exhaustive log of all 37 architectural decisions, trade-offs, and verification steps.
- [`implementation.md`](implementation.md): Deep-dive engineering design and challenge roadmap.

---

## 📄 License
This project is open-source under the MIT License.
