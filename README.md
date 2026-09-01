# NEXUS — The Retail Investor's AI Research Desk

**HACKVERSE: INTO THE WEB — Sprint 1 · VIT Chennai 2026**
**PS-01: Multi-Agent Autonomous Financial Intelligence System for Retail Investors**

**Educational / research prototype. Not financial advice. Not a registered investment
advisor. Does not execute trades. Does not guarantee returns.**

---

## What it does

You ask a plain question like *"Should I increase my Reliance position?"*. NEXUS runs
five specialized agents in parallel (Technical, Fundamental, Sentiment, Risk,
Governance), grounds the Fundamental agent in retrieved document evidence via RAG,
checks for disagreement between agents, and produces **one personalized
recommendation** — ACCUMULATE / HOLD / WATCH / REDUCE / AVOID — with a confidence
score, a WHY, a WHY NOT, and a full audit trace. The same stock can get a different
call for a Conservative investor than for an Aggressive one, because the Risk Agent
checks *portfolio suitability*, not just market attractiveness.

## Where the data actually comes from

This is the important part — see the in-app **About** page for the full breakdown.

| Data | Live mode (toggle on, default) | Demo / fallback mode |
|---|---|---|
| Prices, volume, 52w high/low, indices | **Real**, fetched via `yfinance` (Yahoo Finance), NSE tickers | Cached local dataset |
| Technical indicators (DMA, RSI, volatility, momentum) | **Calculated by NEXUS** from that real price history | Pre-computed cached values |
| Fundamentals (growth, margin, debt/equity, P/E) | **Real**, from Yahoo's free `info` endpoint where available | Cached values |
| News headlines | **Real** recent headlines from `yfinance`, tone-classified locally | Cached curated headlines |
| RAG filing documents | Curated Q1 FY27 earnings-summary text (not a live regulatory feed — see About page for why) | same |

**Live mode falls back to demo automatically and labels it `DEMO (cached)`** whenever a
live fetch fails — blocked network, Yahoo rate-limit, missing field. Nothing is ever
silently presented as live when it isn't. This fallback is exercised for real, not just
in theory: several sandboxed/CI environments (including the one this was built in)
block outbound calls to Yahoo's endpoints outright, so you will see it trigger there —
on a normal laptop or on Streamlit Community Cloud with standard outbound internet, live
mode fetches real data.

## Pages

- **Home** — market overview, watchlist, navigation
- **Investigation** — the core 5-agent pipeline for one stock + question
- **Portfolio** — holdings, sector exposure, risk gauge, what-if allocation simulator
- **Evidence & RAG** — inspect the filing corpus, run ad-hoc retrieval queries directly
- **Decision Trace** — full timestamped audit trail + session history from SQLite
- **About** — exactly what's live vs demo, architecture, disclaimer

## Architecture

```
USER QUESTION
     │
     ▼
ORCHESTRATOR (core/orchestrator.py)
     ├──▶ Technical Agent   ─┐
     ├──▶ Fundamental Agent  │  parallel via ThreadPoolExecutor
     ├──▶ Sentiment Agent    │
     └──▶ Risk Agent        ─┘
                │
                ▼
     Governance Agent (conflict / low-confidence / missing-evidence checks)
                │
                ▼
     Synthesis Agent (blends signals + user profile + portfolio)
                │
                ▼
     Personalized decision + WHY / WHY NOT + confidence
                │
                ▼
     SQLite (sessions, agent_runs, recommendations, portfolio_snapshots)
```

Every agent returns a fixed structured contract (`agents/base.py`) — never free-form
prose as its primary output. RAG lives in `core/rag.py` (TF-IDF vector retrieval with
automatic keyword fallback — mode is always shown in the UI). The LLM
(`core/llm.py`, optional local Ollama) is used only to phrase the natural-language
synthesis summary; if unavailable, a deterministic template with identical substance is
used — no API key is ever required to run the app.

This mirrors the agent-graph shape from multi-agent financial-intelligence
architectures (ingestion → extraction → risk scoring → reporting as a directed graph),
adapted to a lighter dependency footprint (`ThreadPoolExecutor` instead of LangGraph,
TF-IDF instead of a downloaded embedding model, SQLite instead of Postgres) so it
installs and runs in minutes and deploys free on Streamlit Community Cloud.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

No `.env` required. Live market data works out of the box (no API key) — copy
`.env.example` to `.env` only if you want to point at a local Ollama instance for
LLM-phrased summaries.

## Deployment

Streamlit Community Cloud, entry point `app.py`, dependencies in `requirements.txt`.
No Docker, no cloud account, no background workers required.

## Testing

```bash
pytest tests/ -q
```

Covers: technical agent structure, risk concentration flagging, cross-profile
personalization divergence, conflict detection reducing confidence, degraded-mode
graceful handling, RAG retrieval with fallback, and full five-agent execution — all
against the deterministic demo dataset so tests are reproducible without live network
access.

## Limitations

- Five NSE-listed companies only, for hackathon scope.
- Yahoo's free tier has gaps for some fundamentals fields on Indian large-caps; missing
  fields fall back to the cached reference value for that field only.
- RAG corpus is curated earnings-summary text, not a live regulatory filings feed (see
  About page for why, and what a production version would use instead — e.g. NSE/BSE
  corporate-announcements APIs or a paid filings aggregator).
- "Institutional flow" is marked `UNAVAILABLE` in live mode since no free source
  provides it — it is never fabricated.

## Disclaimer

NEXUS is an educational / research prototype demonstrating explainable, multi-agent
decision-support architecture. It is **not financial advice**, is **not a registered
investment advisor**, does **not execute trades**, and does **not guarantee returns**.
Always do your own research and consult a qualified financial advisor before making
investment decisions.
# Nexus
