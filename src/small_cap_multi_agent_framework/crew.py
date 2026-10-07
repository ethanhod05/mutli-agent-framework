"""
Institutional Crew System
=========================

Orchestrates the small-cap investment analysis workflow. All task data flows
through explicit `context=` wiring between Task objects rather than implicit
agent delegation, so the data path is inspectable and reproducible.
"""

from crewai import Crew, Process
from small_cap_multi_agent_framework.config.agents import (
    data_cleaner, data_enricher, news_scanner, alpha_analyst, MODEL_NAME
)
from small_cap_multi_agent_framework.config.tasks import (
    create_professional_task_workflow, create_alpha_generation_task
)
from small_cap_multi_agent_framework.tools.hedge_fund_database import hedge_fund_db
from small_cap_multi_agent_framework.utils.tracing import RunTracer
from small_cap_multi_agent_framework.evals.grounding import evaluate_grounding
from small_cap_multi_agent_framework.evals.thesis_consistency import evaluate_thesis_consistency
from small_cap_multi_agent_framework.evals.outcomes import extract_calls_for_logging, log_outcomes
from small_cap_multi_agent_framework.evals.trajectory import evaluate_trajectory
from small_cap_multi_agent_framework.evals.data_health import run_data_source_health_check
import json
import logging
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv

# Below this, a report is considered ungrounded enough to trigger a retry.
NUMERIC_GROUNDING_RETRY_THRESHOLD = 0.8

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hedge_fund_crew.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if not os.getenv("OPENAI_API_KEY"):
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("Please add OPENAI_API_KEY to your .env file")


class InstitutionalAnalysisCrew:
    """
    Small-cap investment analysis crew:
    1. Data Quality Assurance
    2. Fundamental Research (per ticker, real tool calls)
    3. Market Intelligence (per ticker, real tool calls)
    4. Investment Synthesis
    """

    def __init__(self, input_file: str = None, tickers: list = None, on_event=None):
        if not input_file and not tickers:
            input_file = "data/small_caps_input.csv"
        self.input_file = input_file
        self.tickers = tickers
        self.crew = None
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        self.model_name = MODEL_NAME
        self.on_event = on_event
        self.tracer = RunTracer(self.execution_id, on_event=on_event)
        self.universe = None

        logger.info(f"Institutional Analysis Crew initialized - Model: {self.model_name}")
        logger.info(f"Execution ID: {self.execution_id}")
        self._validate_system_health()

    def _validate_system_health(self):
        """Validate database and agent systems before running."""
        conn = hedge_fund_db._get_connection()
        conn.close()

        agents = [data_cleaner, data_enricher, news_scanner, alpha_analyst]
        for agent in agents:
            if not hasattr(agent, 'role'):
                raise Exception(f"Agent validation failed: {agent}")

        logger.info(f"System health check passed - Ready with {self.model_name}")
        self._check_data_source_health()

    def _check_data_source_health(self):
        """Live check that the real data sources are actually working right
        now, against a canary ticker - independent of whatever tickers this
        run is about to analyze. Non-blocking by design: a degraded source
        (primary down, fallback covering it) or even a fully failed one
        shouldn't stop an analysis the way a missing OPENAI_API_KEY would,
        but it SHOULD be loud and on the record, since this is exactly the
        kind of thing that otherwise only gets noticed days later as
        silence in the UI (the real 2026-09-28 Yahoo news outage)."""
        try:
            health = run_data_source_health_check()
        except Exception as e:
            logger.warning(f"Data-source health check itself failed to run: {e}")
            return

        if health["overall"] == "ok":
            logger.info("Data-source health check: OK - all sources responding")
        elif health["overall"] == "degraded":
            degraded = [name for name, cap in health["coverage"].items() if cap["status"] == "degraded"]
            logger.warning(f"Data-source health check: DEGRADED - covered by fallback for: {degraded}")
        else:
            failed = [name for name, cap in health["coverage"].items() if cap["status"] == "fail"]
            logger.error(f"Data-source health check: FAIL - no working source (primary or fallback) for: {failed}")

        health_path = self.output_dir / f"data_health_{self.execution_id}.json"
        health_path.write_text(json.dumps(health, indent=2))
        self._emit("data_health_result", **health)

    def create_institutional_crew(self) -> Crew:
        """Create the crew. Data flows via explicit task context, not delegation."""
        tasks, universe = create_professional_task_workflow(
            input_file=self.input_file, tickers=self.tickers, execution_id=self.execution_id
        )
        self.universe = universe

        # The four agents are module-level singletons reused across every run
        # (agents.py creates them once at import time). crewai's Crew only
        # attaches its step_callback to an agent if that agent doesn't already
        # have one - so without this reset, only the *first* crew execution in
        # a process ever gets its tool calls traced, and every run after that
        # silently routes tool_call events to the first run's stale tracer.
        # Resetting here forces crewai to re-attach this run's own tracer.
        for agent in (data_cleaner, data_enricher, news_scanner, alpha_analyst):
            agent.step_callback = None

        crew = Crew(
            agents=[data_cleaner, data_enricher, news_scanner, alpha_analyst],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            step_callback=self.tracer.on_step,
            task_callback=self.tracer.on_task_complete,
        )

        logger.info(f"Crew created with {len(tasks)} tasks for source {self._source_label()}")
        return crew

    def _source_label(self) -> str:
        """Human-readable description of where this run's tickers came from."""
        if self.tickers:
            return f"tickers:{','.join(self.tickers)}"
        return self.input_file

    def _emit(self, event_type: str, **data) -> None:
        """Push a high-level lifecycle event (distinct from tracer's tool/task events).

        Used by the web UI to drive things like "run started" / "retrying" /
        "done" states that aren't tied to a single tool call or task.
        """
        if self.on_event:
            self.on_event({"type": event_type, "timestamp": datetime.now().isoformat(), **data})

    def execute_institutional_analysis(self, inputs: dict = None) -> dict:
        """Execute the full investment analysis workflow."""

        if inputs is None:
            inputs = {
                'input_file': self._source_label(),
                'analysis_date': datetime.now().strftime("%Y-%m-%d"),
                'execution_id': self.execution_id
            }

        start_time = datetime.now()

        try:
            logger.info("=" * 80)
            logger.info("STARTING INSTITUTIONAL INVESTMENT ANALYSIS")
            logger.info(f"Model: {self.model_name}")
            logger.info(f"Input File: {inputs['input_file']}")
            logger.info(f"Execution ID: {inputs['execution_id']}")
            logger.info("=" * 80)

            self.crew = self.create_institutional_crew()
            self._emit("analysis_started", tickers=[str(r["Ticker"]) for r in self.universe])

            logger.info("Starting crew execution...")
            result = self.crew.kickoff(inputs=inputs)
            self._strip_leaked_thought_from_report()

            eval_result = self._run_grounding_eval()
            self._emit("grounding_result", **eval_result)

            thesis_result = self._run_thesis_eval()
            self._emit("thesis_result", **thesis_result)

            if self._grounding_failed(eval_result) or self._thesis_failed(thesis_result):
                logger.warning(
                    f"Quality check failed - ungrounded tickers: {eval_result['ungrounded_tickers']}, "
                    f"thesis-inconsistent tickers: {thesis_result['inconsistent_tickers']}. "
                    f"Retrying synthesis..."
                )
                self._emit(
                    "retry_started",
                    ungrounded_tickers=eval_result["ungrounded_tickers"],
                    inconsistent_tickers=thesis_result["inconsistent_tickers"],
                )
                eval_result, thesis_result = self._retry_synthesis_with_correction(eval_result, thesis_result)
                self._emit("grounding_result", **eval_result)
                self._emit("thesis_result", **thesis_result)

            # Computed after any retry so it reflects the complete, final
            # trace (a retry can only add a zero-tool-call synthesis segment,
            # so this can't flip pass/fail either way - but the saved record
            # should still describe everything that actually happened).
            trajectory_result = self._run_trajectory_eval()
            self._emit("trajectory_result", **trajectory_result)
            if not trajectory_result["trajectory_passed"]:
                logger.warning(
                    f"Trajectory check failed - {trajectory_result['severity']}: "
                    f"{trajectory_result['repeated_call_tickers']}"
                )

            if not self._grounding_failed(eval_result):
                self._log_call_outcomes()

            summary = self._generate_execution_summary(start_time, eval_result, thesis_result, trajectory_result)
            self._log_run_history(summary, eval_result, thesis_result)

            logger.info("=" * 80)
            logger.info("ANALYSIS COMPLETED")
            logger.info(f"Analysis Output: {summary['output_files']}")
            logger.info(f"Grounding: {'PASSED' if summary['grounding_passed'] else 'FAILED'}")
            logger.info("=" * 80)

            self._emit("analysis_complete", summary=summary)

            return {
                'status': 'success',
                'result': result,
                'summary': summary,
                'execution_id': self.execution_id,
                'model': self.model_name
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Analysis failed: {error_msg}")

            # Even on a hard failure (e.g. the max_execution_time timeout
            # that now bounds a repeated-tool-call loop), the trace saved so
            # far is real diagnostic data - best-effort check it for exactly
            # that failure mode, so the summary explains *why* it failed
            # instead of just that it did.
            trajectory_result = None
            try:
                trajectory_result = self._run_trajectory_eval()
                if not trajectory_result["trajectory_passed"]:
                    logger.error(
                        f"Trajectory check on the partial trace found: "
                        f"{trajectory_result['repeated_call_tickers']} - likely cause of the failure above"
                    )
            except Exception:
                pass

            self._emit("analysis_failed", error=error_msg, trajectory_result=trajectory_result)

            return {
                'status': 'failed',
                'error': error_msg,
                'execution_id': self.execution_id,
                'model': self.model_name,
                'trajectory_result': trajectory_result,
            }

    # Leaked ReAct "thought" preambles that weaker models sometimes emit before
    # their actual final answer, e.g. "I now can give a great answer". Purely
    # cosmetic prompt noise - stripping it doesn't touch any real data.
    _LEAKED_THOUGHT_PREFIXES = (
        "i now can give a great answer",
        "i now can provide a great answer",
        "i now know the final answer",
    )

    def _strip_leaked_thought_from_report(self) -> None:
        """Remove a leaked ReAct thought preamble from the top of the report file, if present."""
        report_path = self.output_dir / f"alpha_investment_report_{self.execution_id}.md"
        if not report_path.exists():
            return

        text = report_path.read_text()
        lines = text.lstrip().splitlines()
        while lines and lines[0].strip().lower().rstrip(".:") in self._LEAKED_THOUGHT_PREFIXES:
            lines.pop(0)
        cleaned = "\n".join(lines).lstrip("\n")

        if cleaned != text:
            report_path.write_text(cleaned)
            logger.info("Stripped leaked thought preamble from report output")

    def _run_grounding_eval(self) -> dict:
        """Run the grounding eval against this run's report and trace, save it, return it."""
        report_path = self.output_dir / f"alpha_investment_report_{self.execution_id}.md"
        report_text = report_path.read_text() if report_path.exists() else ""

        result = evaluate_grounding(report_text, self.tracer.events)

        eval_file = self.output_dir / f"grounding_eval_{self.execution_id}.json"
        with open(eval_file, 'w') as f:
            json.dump(result, f, indent=2)

        return result

    def _grounding_failed(self, eval_result: dict) -> bool:
        return (
            bool(eval_result.get("ungrounded_tickers"))
            or eval_result.get("numeric_grounding_rate", 1.0) < NUMERIC_GROUNDING_RETRY_THRESHOLD
        )

    def _run_thesis_eval(self) -> dict:
        """Check whether each ticker's call is directionally consistent with
        the real fundamentals it was given - a different question from
        grounding (are the numbers real)."""
        report_path = self.output_dir / f"alpha_investment_report_{self.execution_id}.md"
        report_text = report_path.read_text() if report_path.exists() else ""

        result = evaluate_thesis_consistency(report_text, self.tracer.events)

        thesis_file = self.output_dir / f"thesis_eval_{self.execution_id}.json"
        with open(thesis_file, 'w') as f:
            json.dump(result, f, indent=2)

        return result

    def _thesis_failed(self, thesis_result: dict) -> bool:
        return bool(thesis_result.get("inconsistent_tickers"))

    def _run_trajectory_eval(self) -> dict:
        """Grade the PATH the agents took - not the output, which grounding
        and thesis-consistency already cover, but whether an agent flailed
        (repeated the same tool call) or skipped its job entirely. Computed
        once from the full trace; unlike grounding/thesis this never needs
        recomputing after a retry, since a synthesis-only retry (tools=[])
        can't introduce a new tool-call violation.
        """
        result = evaluate_trajectory(self.tracer.events)

        trajectory_file = self.output_dir / f"trajectory_eval_{self.execution_id}.json"
        with open(trajectory_file, 'w') as f:
            json.dump(result, f, indent=2)

        return result

    def _build_correction_notes(self, failed_grounding: dict, failed_thesis: dict) -> str:
        notes = []
        if failed_grounding.get("ungrounded_tickers"):
            notes.append(
                f"Your previous attempt discussed tickers that were never provided to you: "
                f"{', '.join(failed_grounding['ungrounded_tickers'])}. Do not mention any ticker "
                f"outside the list below."
            )
        for t in failed_grounding.get("per_ticker", []):
            if t.get("unverified_numbers"):
                notes.append(
                    f"For {t['ticker']}, you previously stated numbers that don't appear in the "
                    f"data you were given ({t['unverified_numbers']}). Use only figures that "
                    f"literally appear in the context above."
                )
        for t in failed_thesis.get("per_ticker", []):
            if t.get("applicable") and not t.get("consistent"):
                notes.append(
                    f"For {t['ticker']}, your {t['call']} call doesn't match the fundamental "
                    f"signals you were given ({t['reason']}). Either change your call to match "
                    f"the data, or explicitly address why you're calling against the fundamentals."
                )
        return (
            "CORRECTION REQUIRED - your previous attempt failed an automated quality check:\n"
            + "\n".join(f"- {n}" for n in notes)
        )

    def _retry_synthesis_with_correction(self, failed_grounding: dict, failed_thesis: dict) -> tuple:
        """Re-run only the synthesis step with the specific failures named explicitly.

        Reuses the already-executed context tasks (fundamentals/news/quality) via
        crewai's context mechanism, which just reads their cached `.output` - so
        this makes no new tool calls and costs one extra LLM call, not a full re-run.
        """
        report_path = self.output_dir / f"alpha_investment_report_{self.execution_id}.md"
        if report_path.exists():
            report_path.rename(self.output_dir / f"alpha_investment_report_{self.execution_id}_attempt1.md")

        correction = self._build_correction_notes(failed_grounding, failed_thesis)

        context_tasks = self.crew.tasks[:-1]
        retry_task = create_alpha_generation_task(
            self.universe, context_tasks, self.execution_id, correction=correction
        )

        retry_crew = Crew(
            agents=[alpha_analyst],
            tasks=[retry_task],
            process=Process.sequential,
            verbose=True,
            step_callback=self.tracer.on_step,
            task_callback=self.tracer.on_task_complete,
        )
        retry_crew.kickoff()
        self._strip_leaked_thought_from_report()

        new_grounding = self._run_grounding_eval()
        new_grounding["retried"] = True
        new_grounding["pre_retry_eval"] = failed_grounding

        new_thesis = self._run_thesis_eval()
        new_thesis["retried"] = True

        fixed = not (self._grounding_failed(new_grounding) or self._thesis_failed(new_thesis))
        logger.info(f"Retry {'fixed' if fixed else 'did not fully fix'} the quality check failure")
        return new_grounding, new_thesis

    def _log_call_outcomes(self) -> None:
        """Log each real BUY/HOLD/SELL call with its real price-at-call, for
        later scoring once enough time has passed (scripts/score_outcomes.py).
        Only called for reports that passed grounding - an ungrounded report's
        price figures aren't trustworthy enough to anchor a track record to.
        """
        report_path = self.output_dir / f"alpha_investment_report_{self.execution_id}.md"
        if not report_path.exists():
            return
        report_text = report_path.read_text()
        records = extract_calls_for_logging(report_text, self.tracer.events, self.execution_id)
        log_outcomes(records, self.output_dir / "call_outcomes.jsonl")
        if records:
            logger.info(f"Logged {len(records)} call(s) for future outcome scoring")

    def _log_run_history(self, summary: dict, eval_result: dict, thesis_result: dict) -> None:
        """Append this run's outcome to a persistent history for trend analysis over time."""
        record = {
            'execution_id': self.execution_id,
            'timestamp': datetime.now().isoformat(),
            'source': self._source_label(),
            'model': self.model_name,
            'tool_calls_made': summary['tool_calls_made'],
            'elapsed_seconds': summary['elapsed_seconds'],
            'ticker_grounding_rate': eval_result.get('ticker_grounding_rate'),
            'numeric_grounding_rate': eval_result.get('numeric_grounding_rate'),
            'ungrounded_tickers': eval_result.get('ungrounded_tickers', []),
            'thesis_consistency_rate': thesis_result.get('thesis_consistency_rate'),
            'inconsistent_tickers': thesis_result.get('inconsistent_tickers', []),
            'trajectory_severity': summary.get('trajectory_severity'),
            'trajectory_passed': summary.get('trajectory_passed'),
            'repeated_call_tickers': summary.get('repeated_call_tickers', []),
            'retried': eval_result.get('retried', False),
            'grounding_passed': summary['grounding_passed'],
        }
        history_file = self.output_dir / "run_history.jsonl"
        with open(history_file, 'a') as f:
            f.write(json.dumps(record) + "\n")

    def _generate_execution_summary(
        self, start_time: datetime, eval_result: dict, thesis_result: dict, trajectory_result: dict
    ) -> dict:
        """Generate an execution summary containing only facts derived from this run."""

        output_files = [
            str(p) for p in self.output_dir.glob(f"*_{self.execution_id}.md")
        ]

        summary = {
            'execution_id': self.execution_id,
            'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'input_file': self.input_file,
            'tickers': self.tickers,
            'output_files': output_files,
            'agent_count': len(self.crew.agents) if self.crew else 0,
            'task_count': len(self.crew.tasks) if self.crew else 0,
            'model': self.model_name,
            'elapsed_seconds': round((datetime.now() - start_time).total_seconds(), 1),
            'tool_calls_made': len(self.tracer.tool_calls()),
            'trace_file': str(self.tracer.trace_file),
            'ticker_grounding_rate': eval_result.get('ticker_grounding_rate'),
            'numeric_grounding_rate': eval_result.get('numeric_grounding_rate'),
            'ungrounded_tickers': eval_result.get('ungrounded_tickers', []),
            'grounding_retried': eval_result.get('retried', False),
            'grounding_passed': not self._grounding_failed(eval_result),
            'thesis_consistency_rate': thesis_result.get('thesis_consistency_rate'),
            'inconsistent_tickers': thesis_result.get('inconsistent_tickers', []),
            'thesis_passed': not self._thesis_failed(thesis_result),
            'trajectory_severity': trajectory_result.get('severity'),
            'trajectory_passed': trajectory_result.get('trajectory_passed'),
            'repeated_call_tickers': trajectory_result.get('repeated_call_tickers', []),
            'total_tool_calls_in_trajectory': trajectory_result.get('total_tool_calls'),
        }

        summary_file = self.output_dir / f"execution_summary_{self.execution_id}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Execution summary saved: {summary_file}")
        return summary


def run_institutional_analysis(input_file: str = None, tickers: list = None, on_event=None):
    """Main entry point for institutional investment analysis.

    This is the stable API boundary for any caller - CLI, script, or the web
    UI - to trigger an analysis. Pass `tickers` for an ad-hoc lookup (e.g.
    from the UI form) or `input_file` for a batch CSV run. `on_event`, if
    given, receives every agent/tool/lifecycle event live as it happens.
    """

    logger.info("Initializing Institutional Analysis...")
    institutional_crew = InstitutionalAnalysisCrew(input_file=input_file, tickers=tickers, on_event=on_event)
    results = institutional_crew.execute_institutional_analysis()

    if results['status'] == 'success':
        summary = results['summary']
        print("\nANALYSIS COMPLETED")
        print(f"Model Used: {results['model']}")
        print(f"Execution ID: {results['execution_id']}")
        print(f"Output Files: {len(summary['output_files'])} reports generated")

        if summary['grounding_passed']:
            print(f"Grounding: PASSED (tickers {summary['ticker_grounding_rate'] * 100:.0f}%, "
                  f"numbers {summary['numeric_grounding_rate'] * 100:.0f}%"
                  f"{', after 1 retry' if summary['grounding_retried'] else ''})")
        else:
            print(f"Grounding: FAILED even after retry - ungrounded tickers: {summary['ungrounded_tickers']}")

        if summary['thesis_passed']:
            print(f"Thesis consistency: PASSED ({summary['thesis_consistency_rate'] * 100:.0f}%)")
        else:
            print(f"Thesis consistency: FAILED even after retry - inconsistent calls: {summary['inconsistent_tickers']}")

        if summary['trajectory_passed']:
            print(f"Trajectory: PASSED ({summary['trajectory_severity']}, "
                  f"{summary['total_tool_calls_in_trajectory']} tool calls)")
        else:
            print(f"Trajectory: FAILED - agent repeated/skipped a tool call for: {summary['repeated_call_tickers']}")

        print("\nGENERATED REPORTS:")
        for output_file in summary['output_files']:
            print(f"   {output_file}")

    else:
        print("\nANALYSIS FAILED")
        print(f"Error: {results['error']}")
        print(f"Model: {results['model']}")

    return results


if __name__ == "__main__":
    print("SMALL CAP MULTI-AGENT ANALYSIS SYSTEM")
    print("=" * 50)
    results = run_institutional_analysis()

    if results['status'] == 'success':
        print("\nDone.")
    else:
        print(f"\nFailed: {results.get('error', 'Unknown error')}")
