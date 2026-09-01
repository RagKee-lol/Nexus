import { useState } from "react";

import StockChart from "./StockChart";

import "./index.css";

const API_BASE =
  "";

type AgentResult = {
  name?: string;
  score?: number;
  status?: string;
  summary?: string;
  recommendation?: string;
  [key: string]: unknown;
};

type InvestigationResponse = {
  success?: boolean;
  ticker?: string;
  question?: string;
  question_mode?: string;
  elapsed_ms?: number;

  agents?: {
    technical?: AgentResult;
    fundamental?: AgentResult;
    sentiment?: AgentResult;
    risk?: AgentResult;
    governance?: AgentResult;
  };

  synthesis?: {
    decision?: string;
    recommendation?: string;
    confidence?: number;
    summary?: string;
    rationale?: string;
    [key: string]: unknown;
  };

  profile?: {
    name?: string;
    max_preferred_position_pct?: number;
    volatility_tolerance?: string;
    investment_horizon?: string;
    [key: string]: unknown;
  };

  detail?: string;
};

type AgentCardProps = {
  number: string;
  name: string;
  description: string;
  icon: string;
  result?: AgentResult;
  running: boolean;
};

function AgentCard({
  number,
  name,
  description,
  icon,
  result,
  running,
}: AgentCardProps) {
  const status =
    running
      ? "RUNNING"
      : result
        ? "COMPLETE"
        : "READY";

  return (
    <div className="agent-card">
      <div className="agent-top">
        <div className="agent-number">
          {number}
        </div>

        <div className="agent-icon">
          {icon}
        </div>

        <div className="agent-name">
          <strong>{name}</strong>

          <span>
            {description}
          </span>
        </div>

        <div className="agent-status">
          <span className="status-dot" />

          {status}
        </div>
      </div>

      {!result && !running && (
        <div className="agent-waiting">
          AWAITING INVESTIGATION
        </div>
      )}

      {running && (
        <div className="agent-waiting">
          ANALYZING...
        </div>
      )}

      {result && (
        <div className="agent-result">
          {result.summary && (
            <p>
              {result.summary}
            </p>
          )}

          {result.recommendation && (
            <strong>
              {result.recommendation}
            </strong>
          )}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [
    ticker,
    setTicker,
  ] = useState("RELIANCE");

  const [
    question,
    setQuestion,
  ] = useState(
    "Should I invest in this company?",
  );

  const [
    allocation,
    setAllocation,
  ] = useState("5");

  const [
    result,
    setResult,
  ] =
    useState<InvestigationResponse | null>(
      null,
    );

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const [
    activeTab,
    setActiveTab,
  ] = useState("Research");

  async function runInvestigation() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response =
        await fetch(
          `${API_BASE}/api/investigate`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              ticker:
                ticker
                  .toUpperCase()
                  .trim(),

              question,

              proposed_allocation_pct:
                Number(allocation) || 0,
            }),
          },
        );

      const text =
        await response.text();

      let data: InvestigationResponse;

      try {
        data = JSON.parse(text);
      } catch {
        throw new Error(
          `Backend returned invalid JSON: ${text.slice(
            0,
            300,
          )}`,
        );
      }

      if (!response.ok) {
        throw new Error(
          data.detail ??
            `Backend error ${response.status}`,
        );
      }

      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to connect to NEXUS backend.",
      );
    } finally {
      setLoading(false);
    }
  }

  function getDecision() {
    const synthesis =
      result?.synthesis;

    return (
      synthesis?.decision ??
      synthesis?.recommendation ??
      "AWAITING ANALYSIS"
    );
  }

  function getConfidence() {
    const confidence =
      result?.synthesis
        ?.confidence;

    if (
      typeof confidence !==
      "number"
    ) {
      return "—";
    }

    return confidence <= 1
      ? `${Math.round(
          confidence * 100,
        )}%`
      : `${Math.round(
          confidence,
        )}%`;
  }

  return (
    <div className="app">
      {/* ================================================= */}
      {/* TOP BAR */}
      {/* ================================================= */}

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            N
          </div>

          <div>
            <div className="brand-name">
              NEXUS
            </div>

            <div className="brand-sub">
              FINANCIAL INTELLIGENCE ENGINE
            </div>
          </div>
        </div>

        <div className="system-meta">
          <span>
            MARKET DATA
          </span>

          <span className="dot" />

          <span>
            API ONLINE
          </span>

          <span className="dot" />

          <span>
            5 AGENTS
          </span>
        </div>
      </header>

      {/* ================================================= */}
      {/* NAV */}
      {/* ================================================= */}

      <nav className="nav">
        {[
          "Overview",
          "Research",
          "Portfolio",
          "Evidence",
          "Agent Activity",
        ].map((tab) => (
          <button
            key={tab}
            type="button"
            className={
              activeTab === tab
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActiveTab(tab)
            }
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* ================================================= */}
      {/* MAIN */}
      {/* ================================================= */}

      <main className="content">
        {/* HERO */}

        <section className="hero">
          <div>
            <div className="eyebrow">
              NEXUS / RESEARCH DESK
            </div>

            <h1>
              Research. Reason.
              <br />
              Decide.
            </h1>

            <p>
              Five specialized agents.
              One auditable decision.
            </p>
          </div>

          <div className="hero-status">
            <div className="status-icon">
              ◈
            </div>

            <span>
              SYSTEM STATUS
            </span>

            <strong>
              OPERATIONAL
            </strong>
          </div>
        </section>

        {/* ================================================= */}
        {/* MARKET */}
        {/* ================================================= */}

        <section className="market-section">
          <div className="section-label">
            MARKET INTELLIGENCE
          </div>

          <h2>
            {ticker.toUpperCase()} Market Data
          </h2>

          <div className="market-controls">
            <select
              value={ticker}
              onChange={(event) =>
                setTicker(
                  event.target.value,
                )
              }
            >
              <option value="RELIANCE">
                RELIANCE
              </option>

              <option value="TCS">
                TCS
              </option>

              <option value="INFY">
                INFY
              </option>

              <option value="HDFCBANK">
                HDFCBANK
              </option>

              <option value="ICICIBANK">
                ICICIBANK
              </option>

              <option value="SBIN">
                SBIN
              </option>
            </select>

            <button
              type="button"
              onClick={() => {
                setTicker(
                  ticker,
                );

                window.dispatchEvent(
                  new Event(
                    "nexus-refresh-stock",
                  ),
                );
              }}
              className="small-action"
            >
              REFRESH DATA
            </button>
          </div>

          <StockChart
            ticker={ticker}
          />
        </section>

        {/* ================================================= */}
        {/* INVESTIGATION */}
        {/* ================================================= */}

        <section className="investigation-section">
          <div className="section-label">
            INTELLIGENCE OPERATION
          </div>

          <h2>
            Start an Investigation
          </h2>

          <div className="investigation-grid">
            {/* INPUT */}

            <div className="research-panel">
              <div className="panel-label">
                COMPANY / TICKER
              </div>

              <select
                value={ticker}
                onChange={(event) =>
                  setTicker(
                    event.target.value,
                  )
                }
                className="ticker-select"
              >
                <option value="RELIANCE">
                  RELIANCE — Reliance Industries
                </option>

                <option value="TCS">
                  TCS — Tata Consultancy Services
                </option>

                <option value="INFY">
                  INFY — Infosys
                </option>

                <option value="HDFCBANK">
                  HDFCBANK — HDFC Bank
                </option>

                <option value="ICICIBANK">
                  ICICIBANK — ICICI Bank
                </option>

                <option value="SBIN">
                  SBIN — State Bank of India
                </option>
              </select>

              <div className="panel-label">
                RESEARCH QUESTION
              </div>

              <textarea
                value={question}
                onChange={(event) =>
                  setQuestion(
                    event.target.value,
                  )
                }
                rows={4}
              />

              <div className="question-actions">
                <button
                  type="button"
                  onClick={() =>
                    setQuestion(
                      "Build an investment thesis for this company.",
                    )
                  }
                >
                  Investment thesis
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setQuestion(
                      "Is this company fairly valued?",
                    )
                  }
                >
                  Valuation
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setQuestion(
                      "What are the major risks of investing in this company?",
                    )
                  }
                >
                  Risk analysis
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setQuestion(
                      "Review the available evidence for this company.",
                    )
                  }
                >
                  Evidence review
                </button>
              </div>

              <div className="allocation-row">
                <div>
                  <div className="panel-label">
                    ALLOCATION %
                  </div>

                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={allocation}
                    onChange={(event) =>
                      setAllocation(
                        event.target.value,
                      )
                    }
                  />
                </div>
              </div>

              <button
                type="button"
                className="run-button"
                disabled={loading}
                onClick={
                  runInvestigation
                }
              >
                {loading
                  ? "RUNNING NEXUS..."
                  : "✦  DEPLOY AGENTS"}
              </button>

              {error && (
                <div className="error-box">
                  <strong>
                    INVESTIGATION FAILED
                  </strong>

                  <p>
                    {error}
                  </p>

                  <small>
                    Make sure FastAPI is
                    running on port 8000.
                  </small>
                </div>
              )}
            </div>

            {/* AGENTS */}

            <div className="agent-panel">
              <div className="agent-panel-title">
                MULTI-AGENT ANALYSIS
              </div>

              <div className="agent-layer">
                Intelligence Layer
              </div>

              <AgentCard
                number="01"
                name="TECHNICAL"
                description="Momentum / price structure"
                icon="↗"
                result={
                  result?.agents
                    ?.technical
                }
                running={loading}
              />

              <AgentCard
                number="02"
                name="FUNDAMENTAL"
                description="Financial strength / valuation"
                icon="▥"
                result={
                  result?.agents
                    ?.fundamental
                }
                running={loading}
              />

              <AgentCard
                number="03"
                name="SENTIMENT"
                description="News / market sentiment"
                icon="◎"
                result={
                  result?.agents
                    ?.sentiment
                }
                running={loading}
              />

              <AgentCard
                number="04"
                name="RISK"
                description="Portfolio suitability"
                icon="◇"
                result={
                  result?.agents?.risk
                }
                running={loading}
              />

              <AgentCard
                number="05"
                name="GOVERNANCE"
                description="Conflict / evidence review"
                icon="⌘"
                result={
                  result?.agents
                    ?.governance
                }
                running={loading}
              />
            </div>
          </div>
        </section>

        {/* ================================================= */}
        {/* RESULT */}
        {/* ================================================= */}

        {result && (
          <section className="result-section">
            <div className="section-label">
              GOVERNANCE → SYNTHESIS
            </div>

            <h2>
              Decision
            </h2>

            <div className="snapshot-grid">
              <div className="snapshot-card">
                <span>
                  DECISION
                </span>

                <strong>
                  {getDecision()}
                </strong>
              </div>

              <div className="snapshot-card">
                <span>
                  CONFIDENCE
                </span>

                <strong>
                  {getConfidence()}
                </strong>
              </div>

              <div className="snapshot-card">
                <span>
                  TICKER
                </span>

                <strong>
                  {result.ticker ??
                    ticker}
                </strong>
              </div>

              <div className="snapshot-card">
                <span>
                  RUNTIME
                </span>

                <strong>
                  {result.elapsed_ms
                    ? `${result.elapsed_ms} ms`
                    : "—"}
                </strong>
              </div>
            </div>

            {result.synthesis
              ?.summary && (
              <div className="decision-box">
                <div className="panel-label">
                  SYNTHESIS
                </div>

                <p>
                  {
                    result.synthesis
                      .summary
                  }
                </p>
              </div>
            )}

            {result.synthesis
              ?.rationale && (
              <div className="decision-box">
                <div className="panel-label">
                  RATIONALE
                </div>

                <p>
                  {
                    result.synthesis
                      .rationale
                  }
                </p>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}