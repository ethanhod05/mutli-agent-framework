# Small-Cap Multi-Agent Framework

A crew of LLM agents that researches small-cap stocks and writes a BUY / HOLD / SELL report, built to answer one question: **how do you know the agents aren't making things up?**

I started this as a stock-analysis pipeline. It turned into a project about making agent output trustworthy: grounding every claim in a real tool call, grading how the agents got to an answer, and feeding failures back in as regression tests.

## What it does

Four [CrewAI](https://github.com/crewAIInc/crewAI) agents run in sequence for each ticker:

| Agent | Job |
|---|---|
| `data_cleaner` | Validates the input universe |
| `data_enricher` | Pulls real fundamentals (yfinance, with SEC EDGAR and Finnhub fallbacks for tickers yfinance can't cover) |
| `news_scanner` | Pulls recent headlines, ranks them by relevance and materiality, and scores sentiment |
| `alpha_analyst` | Writes the thesis and rating from **only** the data above |

## The part I care about: evals

Every run is traced and then graded automatically:

- **Grounding** – every ticker and number in the report must trace back to a real tool call.
- **Thesis consistency** – does BUY/HOLD/SELL agree with the fundamentals the agent was given?
- **Trajectory** – grades the *path* (tool calls, retries, loops), not just the final text.
- **Data-source health** – live check that yfinance / EDGAR / Finnhub are returning real data.
- **Outcome scoring** – compares old calls against what the price actually did.

If a check fails, the crew retries once with a correction. Bad runs can be turned into permanent regression tests:

```bash
python scripts/promote_trace.py   # saves a real trace as a fixture replayed by pytest
```

This came from real failures: an early version fabricated whole reports because a tool import was silently broken, and one agent got stuck in an infinite loop. Both are now fixtures in [tests/fixtures/promoted_traces](tests/fixtures/promoted_traces).

### News ranking

Finnhub returns a chronological feed padded with listicles and loosely tagged articles, so "newest 5" can miss the real story. The scanner now ranks the full 14-day window by company relevance, materiality terms, story volume (how many outlets cover the same event) and recency, then de-duplicates. No ticker-specific logic.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your OpenAI + Finnhub keys

python src/small_cap_multi_agent_framework/main.py                      # sample universe in data/
python src/small_cap_multi_agent_framework/main.py --tickers SMLR,HROW  # specific tickers
```

Dashboard (reports, traces, cost and run trends):

```bash
cd src && python -m small_cap_multi_agent_framework.webapp   # http://localhost:8000
```

Tests and eval CLIs:

```bash
pytest
python scripts/run_history.py       # grounding outcome over time
python scripts/eval_grounding.py    # grade the latest run
```

## Layout

```
src/small_cap_multi_agent_framework/
  config/     agent and task definitions
  tools/      yfinance, SEC EDGAR, Finnhub data access
  evals/      grounding, thesis, trajectory, data health, outcomes, trends
  utils/      tracing and cost tracking
  webapp.py   dashboard (FastAPI) + webapp_static/
scripts/      CLIs for the evals
tests/        pytest suite + promoted regression traces
```

## Status

Works end to end. Roadmap: more evals, and a tighter loop where failures automatically improve prompts. Not investment advice.
