"""
Web UI Backend
==============

A thin FastAPI layer over the real crewai pipeline. Runs each analysis in a
background thread and streams the live trace/lifecycle events over
Server-Sent Events, so the frontend can show agents actually working instead
of a fake canned animation - every event on screen corresponds to a real
tool call, task completion, or grounding check.

Run with:
    python -m small_cap_multi_agent_framework.webapp
Then open http://localhost:8000
"""

import json
import queue
import re
import threading
from pathlib import Path
from typing import List, Optional

import yfinance as yf
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from small_cap_multi_agent_framework.crew import InstitutionalAnalysisCrew
from small_cap_multi_agent_framework.evals.outcomes import score_outcomes

VALID_PERIODS = {"6mo", "1y", "2y", "5y"}

# Matches the exact format hedge_fund_database.py's _get_yfinance_news writes -
# keep the two in sync. This parses the real, saved tool output (what the news
# agent actually saw in this run), not a fresh live query, so clicking through
# shows the exact source a report's sentiment claim was based on.
NEWS_ARTICLE_RE = re.compile(
    r"^\d+\.\s+(?P<title>.+?)\n"
    r"\s*Publisher:\s*(?P<publisher>.+?)\n"
    r"\s*Date:\s*(?P<date>.+?)\n"
    r"\s*Sentiment:\s*(?P<sentiment>\w+)\s*\(score:\s*(?P<score>[+-]?[\d.]+)\)\n"
    r"\s*Link:\s*(?P<link>\S+)",
    re.MULTILINE,
)


def parse_news_articles(news_text: str) -> list:
    articles = []
    for m in NEWS_ARTICLE_RE.finditer(news_text):
        articles.append({
            "title": m.group("title").strip(),
            "publisher": m.group("publisher").strip(),
            "date": m.group("date").strip(),
            "sentiment": m.group("sentiment").strip(),
            "score": float(m.group("score")),
            "link": m.group("link").strip(),
        })
    return articles

app = FastAPI(title="Small Cap Multi-Agent Framework")

STATIC_DIR = Path(__file__).parent / "webapp_static"
OUTPUT_DIR = Path("output")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory run registry - fine for a local single-user demo, not meant to
# survive a server restart (the real artifacts on disk do, via output/).
_runs: dict = {}
_runs_lock = threading.Lock()


class AnalyzeRequest(BaseModel):
    tickers: Optional[List[str]] = None


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/analyze")
def start_analysis(req: AnalyzeRequest):
    event_queue: queue.Queue = queue.Queue()

    def on_event(event: dict):
        event_queue.put(event)

    try:
        if req.tickers:
            crew = InstitutionalAnalysisCrew(tickers=req.tickers, on_event=on_event)
        else:
            crew = InstitutionalAnalysisCrew(on_event=on_event)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    execution_id = crew.execution_id
    with _runs_lock:
        _runs[execution_id] = {"queue": event_queue, "status": "running", "result": None}

    def run():
        try:
            result = crew.execute_institutional_analysis()
            with _runs_lock:
                _runs[execution_id]["status"] = "done"
                _runs[execution_id]["result"] = result
        except Exception as e:
            with _runs_lock:
                _runs[execution_id]["status"] = "error"
                _runs[execution_id]["result"] = {"status": "failed", "error": str(e)}
            event_queue.put({"type": "analysis_failed", "error": str(e)})
        finally:
            event_queue.put({"type": "stream_end"})

    threading.Thread(target=run, daemon=True).start()

    return {"execution_id": execution_id}


@app.get("/api/stream/{execution_id}")
def stream(execution_id: str):
    with _runs_lock:
        run = _runs.get(execution_id)
    if not run:
        return JSONResponse({"error": "unknown execution_id"}, status_code=404)

    def event_generator():
        q = run["queue"]
        while True:
            try:
                event = q.get(timeout=30)
            except queue.Empty:
                yield ": heartbeat\n\n"
                continue
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "stream_end":
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _load_summary(execution_id: str):
    """Summary for a run, from the live in-memory registry if present,
    otherwise straight from disk - so historical runs (including ones from a
    previous server session) are just as servable as the current one."""
    with _runs_lock:
        run = _runs.get(execution_id)
    if run and run["status"] in ("done", "error"):
        result = run["result"]
        if result.get("status") != "success":
            return None, result.get("error", "analysis failed")
        return result["summary"], None

    summary_path = OUTPUT_DIR / f"execution_summary_{execution_id}.json"
    if not summary_path.exists():
        return None, "not found"
    return json.loads(summary_path.read_text()), None


@app.get("/api/report/{execution_id}")
def get_report(execution_id: str):
    summary, error = _load_summary(execution_id)
    if summary is None:
        status = 404 if error in ("not found", "not ready") else 500
        return JSONResponse({"error": error}, status_code=status)

    report_text = ""
    if summary.get("output_files"):
        report_path = Path(summary["output_files"][0])
        if report_path.exists():
            report_text = report_path.read_text()

    return {"report": report_text, "summary": summary}


@app.get("/api/price-history/{ticker}")
def price_history(ticker: str, period: str = "2y"):
    """Real weekly close-price history for a ticker, for the UI chart only -
    deterministic, no LLM involved, same yfinance source the agents use."""
    if period not in VALID_PERIODS:
        return JSONResponse({"error": f"period must be one of {sorted(VALID_PERIODS)}"}, status_code=400)

    ticker = ticker.upper().strip()
    try:
        hist = yf.Ticker(ticker).history(period=period, interval="1wk")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)

    if hist.empty:
        return JSONResponse({"error": f"No price history available for {ticker}"}, status_code=404)

    return {
        "ticker": ticker,
        "period": period,
        "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
        "closes": [round(float(c), 2) for c in hist["Close"]],
    }


@app.get("/api/news/{execution_id}/{ticker}")
def get_news(execution_id: str, ticker: str):
    """Real headlines the news agent actually analyzed for this ticker in
    this run - parsed from the saved trace, not a fresh live query, so this
    shows exactly what a report's sentiment claim was based on. Click
    through and verify it yourself; nothing here is paraphrased.
    """
    trace_path = OUTPUT_DIR / "traces" / f"trace_{execution_id}.json"
    if not trace_path.exists():
        return JSONResponse({"error": "no saved trace for this execution_id"}, status_code=404)

    ticker = ticker.upper().strip()
    trace_events = json.loads(trace_path.read_text()).get("events", [])

    for event in trace_events:
        if event.get("type") != "tool_call":
            continue
        tool_input = event.get("tool_input") or ""
        if "news" not in tool_input:
            continue
        m = re.search(r'"ticker"\s*:\s*"([A-Z.\-]+)"', tool_input)
        if m and m.group(1) == ticker:
            return {"ticker": ticker, "articles": parse_news_articles(event.get("result", ""))}

    return {"ticker": ticker, "articles": []}


@app.get("/api/replay/{execution_id}")
def get_replay(execution_id: str):
    """Reconstruct a full event timeline for a past run from what's actually
    saved on disk, so the UI can replay it through the real battle-screen
    animation without spending a new OpenAI/yfinance call.

    Every field in every returned event is either read verbatim from a saved
    file or is one of two honest structural markers: a reconstructed
    'analysis_started' (ticker list derived from the trace's own real tool
    calls) and a bare 'retry_started' with no fabricated numbers, emitted
    only when we can prove a retry happened (the attempt1 report still
    exists). We do not fabricate the pre-retry failure's exact numbers,
    since those were never persisted - only the real final outcome is shown.
    """
    trace_path = OUTPUT_DIR / "traces" / f"trace_{execution_id}.json"
    if not trace_path.exists():
        return JSONResponse({"error": "no saved trace for this execution_id"}, status_code=404)

    summary, error = _load_summary(execution_id)
    if summary is None:
        return JSONResponse({"error": error}, status_code=404)

    trace_events = json.loads(trace_path.read_text()).get("events", [])

    eval_path = OUTPUT_DIR / f"grounding_eval_{execution_id}.json"
    eval_result = json.loads(eval_path.read_text()) if eval_path.exists() else {}

    thesis_path = OUTPUT_DIR / f"thesis_eval_{execution_id}.json"
    thesis_result = json.loads(thesis_path.read_text()) if thesis_path.exists() else {}

    trajectory_path = OUTPUT_DIR / f"trajectory_eval_{execution_id}.json"
    trajectory_result = json.loads(trajectory_path.read_text()) if trajectory_path.exists() else {}

    attempt1_exists = (OUTPUT_DIR / f"alpha_investment_report_{execution_id}_attempt1.md").exists()

    tickers = []
    for e in trace_events:
        if e.get("type") == "tool_call":
            m = re.search(r'"ticker"\s*:\s*"([A-Z.\-]+)"', e.get("tool_input") or "")
            if m and m.group(1) not in tickers:
                tickers.append(m.group(1))

    replay = [{
        "type": "analysis_started",
        "timestamp": trace_events[0]["timestamp"] if trace_events else "",
        "tickers": tickers,
    }]

    pm_indices = [
        i for i, e in enumerate(trace_events)
        if e.get("type") == "task_complete" and e.get("agent") == "Senior Portfolio Manager"
    ]

    for i, e in enumerate(trace_events):
        if attempt1_exists and len(pm_indices) >= 2 and i == pm_indices[1]:
            replay.append({"type": "retry_started", "timestamp": e["timestamp"]})
        replay.append(e)

    replay.append({
        "type": "grounding_result",
        "timestamp": summary.get("analysis_date", ""),
        "retried": summary.get("grounding_retried", False),
        **eval_result,
    })
    if thesis_result:
        replay.append({
            "type": "thesis_result",
            "timestamp": summary.get("analysis_date", ""),
            **thesis_result,
        })
    if trajectory_result:
        replay.append({
            "type": "trajectory_result",
            "timestamp": summary.get("analysis_date", ""),
            **trajectory_result,
        })
    replay.append({
        "type": "analysis_complete",
        "timestamp": summary.get("analysis_date", ""),
        "summary": summary,
    })

    return {"execution_id": execution_id, "events": replay}


@app.get("/api/outcomes")
def get_outcomes():
    """The real track record: scores every logged BUY/HOLD/SELL call that's
    old enough (>= MIN_HOLD_DAYS) against a real current price lookup. This
    is the one check that answers "is it actually good at picking stocks" -
    grounding and thesis-consistency only answer "is it honest" and
    "is it coherent". Always does a live price check for scoreable calls, so
    this is slower than the other endpoints but never stale.
    """
    result = score_outcomes(OUTPUT_DIR / "call_outcomes.jsonl")
    result["results"] = list(reversed(result["results"]))[:50]
    return result


@app.get("/api/history")
def get_history(limit: int = 20):
    history_file = OUTPUT_DIR / "run_history.jsonl"
    if not history_file.exists():
        return []
    lines = [l for l in history_file.read_text().splitlines() if l.strip()]
    records = [json.loads(l) for l in lines[-limit:]]
    return list(reversed(records))


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
