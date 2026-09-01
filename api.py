from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.technical import TechnicalAgent
from agents.fundamental import FundamentalAgent
from agents.sentiment import SentimentAgent
from agents.risk import RiskAgent
from agents.governance import GovernanceAgent
from agents.synthesis import synthesize
from core.profiler import load_portfolios as _load_portfolios, get_profile as _get_profile, get_portfolio as _get_portfolio
from core import live_data as _live_data

# Frontend-facing ticker symbols that don't exactly match the internal
# dataset keys (e.g. the UI shows "INFY" but the dataset key is "INFOSYS").
TICKER_ALIASES = {
    "INFY": "INFOSYS",
}

VALID_PROFILE_KEYS = {"conservative", "moderate", "aggressive"}


def resolve_ticker(ticker: str) -> str:
    ticker = ticker.upper().strip()
    return TICKER_ALIASES.get(ticker, ticker)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="NEXUS Financial Intelligence Engine",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


# ============================================================
# REQUEST MODELS
# ============================================================

class InvestigationRequest(BaseModel):
    ticker: str
    question: str = "Should I invest in this company?"
    proposed_allocation_pct: float | None = None
    profile: str = "moderate"


# ============================================================
# HELPERS
# ============================================================

def read_json(filename: str) -> dict[str, Any]:
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}"
        )

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_market_data(ticker: str) -> dict[str, Any]:
    data = read_json("market.json")

    ticker = resolve_ticker(ticker)

    # Case 1:
    # {
    #   "RELIANCE": {...}
    # }
    if ticker in data:
        return data[ticker]

    # Case 2:
    # {
    #   "technical": {...},
    #   "fundamental": {...}
    # }
    if "technical" in data:
        return data

    raise ValueError(
        f"No market data found for ticker: {ticker}"
    )


def load_news_data(ticker: str) -> dict[str, Any]:
    data = read_json("news.json")

    ticker = resolve_ticker(ticker)

    if ticker in data:
        return data[ticker]

    if "positive_count" in data:
        return data

    # Don't crash the whole investigation if there is
    # no dedicated news entry.
    return {
        "positive_count": 0,
        "negative_count": 0,
        "neutral_count": 0,
        "articles": [],
    }


def _normalize_profile_key(profile_key: str) -> str:
    profile_key = (profile_key or "moderate").lower().strip()
    return profile_key if profile_key in VALID_PROFILE_KEYS else "moderate"


def load_portfolio(profile_key: str = "moderate") -> dict[str, Any]:
    """Returns the ACTUAL holdings/sector_exposure/risk_score for the given
    investor profile — not the raw portfolio.json file, which is keyed by
    profile and has a different shape than what the agents expect."""
    profile_key = _normalize_profile_key(profile_key)
    portfolios = _load_portfolios()
    return _get_portfolio(portfolios, profile_key)


def get_profile(profile_key: str = "moderate") -> dict[str, Any]:
    profile_key = _normalize_profile_key(profile_key)
    portfolios = _load_portfolios()
    return _get_profile(portfolios, profile_key)


def get_question_mode(question: str) -> str:
    q = question.lower()

    if any(
        word in q
        for word in [
            "invest",
            "buy",
            "should i",
            "worth",
            "recommend",
        ]
    ):
        return "INVESTMENT_DECISION"

    if any(
        word in q
        for word in [
            "risk",
            "safe",
            "danger",
            "downside",
        ]
    ):
        return "RISK_ANALYSIS"

    if any(
        word in q
        for word in [
            "technical",
            "chart",
            "momentum",
            "trend",
        ]
    ):
        return "TECHNICAL_ANALYSIS"

    if any(
        word in q
        for word in [
            "financial",
            "fundamental",
            "valuation",
            "revenue",
            "profit",
        ]
    ):
        return "FUNDAMENTAL_ANALYSIS"

    return "GENERAL_RESEARCH"


def serialize_agent(result: Any) -> dict[str, Any]:
    """Serializes an AgentResult for the frontend, adding a couple of
    display-friendly aliases (`summary`, `recommendation`) on top of the
    real structured fields — the React AgentCard reads those two, while
    the underlying `signal`/`factors`/`evidence` stay available for anyone
    reading the raw payload."""
    if hasattr(result, "to_dict"):
        data = result.to_dict()
        factors = data.get("factors") or []
        confidence = data.get("confidence")
        summary_bits = factors[:2]
        if confidence is not None:
            summary_bits.append(f"Confidence {round(confidence * 100)}%")
        data["summary"] = " · ".join(summary_bits) if summary_bits else None
        data["recommendation"] = data.get("signal")
        return data

    if isinstance(result, dict):
        return result

    return {
        "result": str(result)
    }


def serialize_synthesis(result: Any) -> dict[str, Any]:
    """Same idea as serialize_agent but for the SynthesisResult — adds
    `decision` as an alias for `final_signal` since that's what the
    frontend's getDecision() looks for."""
    if hasattr(result, "to_dict"):
        data = result.to_dict()
        data["decision"] = data.get("final_signal")
        data["rationale"] = " ".join(data.get("decision_trace") or [])
        return data
    if isinstance(result, dict):
        return result
    return {"result": str(result)}


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
def root():
    return {
        "system": "NEXUS",
        "status": "online",
        "message": "NEXUS API is running",
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "system": "NEXUS",
        "backend": "FastAPI",
    }


# ============================================================
# MARKET DATA
# ============================================================

def build_history(ticker: str, market: dict[str, Any]) -> tuple[list[dict[str, Any]], str, bool]:
    """Returns (history, data_source, is_demo). Tries real historical prices
    via yfinance first; falls back to a deterministic synthetic series ending
    at the known demo price so the chart always has something to draw and
    never depends on a flaky direct-from-browser Yahoo call."""
    yf_symbol = _live_data.NSE_TICKERS.get(ticker)
    if yf_symbol:
        try:
            import yfinance as yf

            hist = yf.Ticker(yf_symbol).history(period="3mo", interval="1d")
            if hist is not None and not hist.empty:
                points = [
                    {"date": idx.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2),
                     "volume": int(row["Volume"])}
                    for idx, row in hist.iterrows()
                ]
                if points:
                    return points, "LIVE (Yahoo Finance)", False
        except Exception:
            pass

    # Deterministic synthetic fallback — seeded on the ticker so repeated
    # requests for the same stock return the same shape, ending at the
    # known demo price.
    import random
    import datetime as _dt

    price = market["technical"]["price"]
    rng = random.Random(ticker)
    days = 60
    walk = []
    level = price * 0.94
    for _ in range(days):
        level *= 1 + rng.uniform(-0.012, 0.014)
        walk.append(level)
    walk[-1] = price  # anchor the last point to the known current price
    today = _dt.date.today()
    points = [
        {"date": (today - _dt.timedelta(days=(days - 1 - i))).isoformat(), "close": round(v, 2)}
        for i, v in enumerate(walk)
    ]
    return points, "DEMO (simulated)", True


@app.get("/api/market/{ticker}")
def get_market(ticker: str):

    ticker = resolve_ticker(ticker)

    try:
        market = load_market_data(ticker)
        history, source, is_demo = build_history(ticker, market)
        t = market["technical"]
        change_pct = round((t["price"] - t["previous_close"]) / t["previous_close"] * 100, 2)

        return {
            "success": True,
            "ticker": ticker,
            "company": market.get("name", ticker),
            "currency": "INR",
            "current_price": t["price"],
            "change_pct": change_pct,
            "data_source": source,
            "demo": is_demo,
            "history": history,
            "data": market,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


# ============================================================
# NEWS
# ============================================================

@app.get("/api/news/{ticker}")
def get_news(ticker: str):

    ticker = resolve_ticker(ticker)

    try:
        news = load_news_data(ticker)

        return {
            "success": True,
            "ticker": ticker,
            "data": news,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


# ============================================================
# INVESTIGATION
# ============================================================

@app.post("/api/investigate")
def investigate(request: InvestigationRequest):

    started = time.time()

    ticker = resolve_ticker(request.ticker)

    if not ticker:
        raise HTTPException(
            status_code=400,
            detail="Ticker cannot be empty",
        )

    question_mode = get_question_mode(
        request.question
    )

    try:

        # ----------------------------------------------------
        # LOAD DATA
        # ----------------------------------------------------

        market_data = load_market_data(ticker)
        news_data = load_news_data(ticker)
        profile = get_profile(request.profile)
        portfolio = load_portfolio(request.profile)

        # ----------------------------------------------------
        # TECHNICAL AGENT
        # ----------------------------------------------------

        technical = TechnicalAgent().run(
            ticker,
            market_data,
        )

        # ----------------------------------------------------
        # FUNDAMENTAL AGENT
        # ----------------------------------------------------

        fundamental = FundamentalAgent().run(
            ticker,
            market_data,
            request.question,
        )

        # ----------------------------------------------------
        # SENTIMENT AGENT
        # ----------------------------------------------------

        sentiment = SentimentAgent().run(
            ticker,
            news_data,
        )

        # ----------------------------------------------------
        # RISK AGENT
        # ----------------------------------------------------

        risk = RiskAgent().run(
            ticker,
            market_data,
            profile,
            portfolio,
            request.proposed_allocation_pct,
        )

        # ----------------------------------------------------
        # GOVERNANCE AGENT
        # ----------------------------------------------------

        governance = GovernanceAgent().run(
            technical,
            fundamental,
            sentiment,
            risk,
            data_degraded=False,
        )

        # ----------------------------------------------------
        # SYNTHESIS
        # ----------------------------------------------------

        synthesis = synthesize(
            ticker=ticker,
            question=request.question,
            technical=technical,
            fundamental=fundamental,
            sentiment=sentiment,
            risk=risk,
            governance=governance,
            profile=profile,
            portfolio=portfolio,
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        elapsed = round(
            (time.time() - started) * 1000,
            1,
        )

        return {
            "success": True,
            "ticker": ticker,
            "question": request.question,
            "question_mode": question_mode,
            "elapsed_ms": elapsed,

            "agents": {
                "technical": serialize_agent(
                    technical
                ),

                "fundamental": serialize_agent(
                    fundamental
                ),

                "sentiment": serialize_agent(
                    sentiment
                ),

                "risk": serialize_agent(
                    risk
                ),

                "governance": serialize_agent(
                    governance
                ),
            },

            "synthesis": serialize_synthesis(
                synthesis
            ),

            "profile": profile,

            "market_data": market_data,
        }

    except Exception as exc:

        print(
            f"[NEXUS] Investigation failed for "
            f"{ticker}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# SERVER ENTRY
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "api:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )