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
import threading
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from small_cap_multi_agent_framework.crew import InstitutionalAnalysisCrew

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


@app.get("/api/report/{execution_id}")
def get_report(execution_id: str):
    with _runs_lock:
        run = _runs.get(execution_id)
    if not run or run["status"] not in ("done", "error"):
        return JSONResponse({"error": "not ready"}, status_code=404)

    result = run["result"]
    if result.get("status") != "success":
        return JSONResponse({"error": result.get("error", "analysis failed")}, status_code=500)

    summary = result["summary"]
    report_text = ""
    if summary.get("output_files"):
        report_path = Path(summary["output_files"][0])
        if report_path.exists():
            report_text = report_path.read_text()

    return {"report": report_text, "summary": summary}


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
