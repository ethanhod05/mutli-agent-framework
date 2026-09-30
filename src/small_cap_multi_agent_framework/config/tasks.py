"""
Task Workflow
=============

Builds a task graph grounded in a real, fixed ticker universe - either loaded
from a CSV (batch mode) or passed directly as a list of tickers (ad-hoc mode,
e.g. from a future UI). Either way the universe is resolved deterministically
before any LLM runs, so it can never drift from what was actually requested.
Every downstream task is required to call the real database tool and is
explicitly wired via `context=` rather than relying on implicit delegation.
"""

from crewai import Task
from small_cap_multi_agent_framework.config.agents import (
    data_cleaner, data_enricher, news_scanner, alpha_analyst
)
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def load_ticker_universe(input_file: str) -> list[dict]:
    """Load the real small-cap universe from CSV. Deterministic, no LLM involved."""
    df = pd.read_csv(input_file)
    return df.to_dict(orient="records")


def tickers_to_universe(tickers: list[str]) -> list[dict]:
    """Build a universe from explicitly requested tickers - no metadata guessed.

    Company name, sector, and market cap for these come only from the real
    tool call in the fundamentals task, never invented here.
    """
    return [{"Ticker": t.strip().upper()} for t in tickers if t.strip()]


def create_data_quality_task(universe: list[dict]) -> Task:
    rows = "\n".join(
        f"- {r['Ticker']}: {r['Company Name']} | {r['Sector']} | Market Cap ${r['Market Cap']:,.0f}"
        for r in universe
    )
    return Task(
        description=f"""
        Review the following small-cap securities for data quality issues. This is the
        complete, fixed universe for this analysis run - do not add, remove, or substitute
        any tickers.

        {rows}

        Flag anything that looks wrong (implausible market cap, missing sector, malformed
        ticker). Do not invent facts about these companies beyond what's given here.
        """,
        expected_output="A short data quality note per ticker: OK, or a specific flag.",
        agent=data_cleaner,
    )


def create_fundamentals_task(ticker: str) -> Task:
    return Task(
        description=f"""
        Call the institutional database tool for ticker '{ticker}' with query_type='fundamental'.
        Report ONLY the numbers the tool returns. If the tool returns an error or missing
        data, state that explicitly - do not estimate or invent a value.
        """,
        expected_output=f"The tool's fundamental data for {ticker}, verbatim, or a clear note that data is unavailable.",
        agent=data_enricher,
    )


def create_news_task(ticker: str) -> Task:
    return Task(
        description=f"""
        Call the institutional database tool for ticker '{ticker}' with query_type='news'.
        Summarize ONLY what the tool returns. If no news is available, state that explicitly.
        """,
        expected_output=f"A short news/sentiment summary for {ticker} based only on tool output.",
        agent=news_scanner,
    )


def create_alpha_generation_task(
    universe: list[dict], context_tasks: list[Task], execution_id: str, correction: str = ""
) -> Task:
    tickers = ", ".join(str(r["Ticker"]) for r in universe)
    correction_block = f"\n{correction}\n" if correction else ""
    return Task(
        description=f"""
        {correction_block}Using ONLY the fundamental and news data gathered in context above, produce an
        investment report covering exactly these tickers and no others: {tickers}.

        Start each ticker's section with a markdown "##" heading containing the REAL
        ticker symbol followed by a colon and the company name - for example, if the
        ticker were XYZ and the company "Example Corp", the heading would be exactly
        "## XYZ: Example Corp". Substitute the actual ticker symbol you were given -
        never write the literal word "TICKER" or "XYZ" itself. Do this even if there
        is only one ticker, and do not use any other heading style for a ticker section.

        For each ticker:
        1. State the fundamental metrics and news sentiment exactly as reported above.
        2. Give a BUY/HOLD/SELL call with 2-3 sentence rationale tied to that actual data.
        3. If data was unavailable or limited for a ticker, say so explicitly rather than
           filling the gap with an invented number.

        Do not mention any ticker outside this list. Do not cite SEC filings, analyst
        reports, backtests, or any other source you were not given data for in context.
        """,
        expected_output=(
            "A markdown investment report with one '## TICKER: Company Name' section per "
            "ticker (this exact heading format, even for a single ticker), each containing "
            "the real metrics/news provided, a BUY/HOLD/SELL call, and rationale. "
            "No fabricated data, no tickers outside the given list."
        ),
        agent=alpha_analyst,
        context=context_tasks,
        output_file=f"output/alpha_investment_report_{execution_id}.md",
    )


def create_professional_task_workflow(input_file: str = None, tickers: list[str] = None, execution_id: str = "latest"):
    """Create the full task workflow.

    Pass either `input_file` (a CSV with Ticker/Company Name/Sector/Market Cap
    columns - runs the data-quality check too) or `tickers` (a bare list of
    ticker strings - skips the quality check since there's no pre-supplied
    metadata to validate, and goes straight to real per-ticker tool lookups).
    `execution_id` namespaces the output report file so concurrent/repeated
    runs (e.g. from a future UI) don't clobber each other's report.
    """
    if tickers:
        universe = tickers_to_universe(tickers)
        logger.info(f"Using {len(universe)} explicitly requested tickers (no CSV)")
        quality_tasks = []
    else:
        input_file = input_file or "data/small_caps_input.csv"
        universe = load_ticker_universe(input_file)
        logger.info(f"Loaded {len(universe)} real tickers from {input_file}")
        quality_tasks = [create_data_quality_task(universe)]

    fundamentals_tasks = [create_fundamentals_task(r["Ticker"]) for r in universe]
    news_tasks = [create_news_task(r["Ticker"]) for r in universe]

    context_tasks = quality_tasks + fundamentals_tasks + news_tasks
    alpha_task = create_alpha_generation_task(universe, context_tasks, execution_id)

    tasks = context_tasks + [alpha_task]
    logger.info(f"Created {len(tasks)} grounded tasks for {len(universe)} tickers")
    return tasks, universe
