"""
Multi-Agent Configuration
==========================

Agent definitions for the small-cap analysis crew. All agents that touch
per-security data are given the real yfinance-backed database tool so their
output is grounded in actual tool calls rather than invented from the LLM's
training data.
"""

from crewai import Agent, LLM
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found. Please add it to your .env file")

# Configurable via env var instead of probing the API on every import.
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
logger.info(f"Using {MODEL_NAME} for all agents")


def create_llm(max_completion_tokens=1000, temperature=0.2):
    """Create LLM instance with correct parameters for the OpenAI API."""
    return LLM(
        model=MODEL_NAME,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        api_key=os.getenv("OPENAI_API_KEY")
    )


class AgentFactory:
    """Factory for creating agents wired to the real database tool."""

    def __init__(self):
        self.tools = self._load_tools()

    def _load_tools(self):
        """Load the real yfinance-backed database tool."""
        try:
            from small_cap_multi_agent_framework.tools.hedge_fund_database import query_institutional_database
            logger.info("Database tools loaded")
            return [query_institutional_database]
        except ImportError as e:
            logger.warning(f"Database tools not found - agents will work without them: {e}")
            return []

    def create_data_cleaner(self):
        """Create data cleaning agent. Works only from data it's given - no tools needed."""
        return Agent(
            role="Financial Data Quality Specialist",
            goal="Flag data quality issues in the provided securities list",
            backstory="Expert in financial data validation with focus on small-cap securities",
            verbose=True,
            allow_delegation=False,
            max_iter=2,
            max_execution_time=45,
            memory=True,
            tools=[],
            llm=create_llm(max_completion_tokens=600, temperature=0.1),
            system_message="""You will be given a fixed list of securities with ticker,
            company name, sector, and market cap. Review only what you are given:
            1. Flag any implausible market cap, missing field, or malformed ticker
            2. Do not add, remove, or invent securities
            3. Do not invent facts about companies beyond the fields provided

            Output: One line per ticker - either "OK" or a specific flag."""
        )

    def create_data_enricher(self):
        """Create data enrichment agent. Must ground every number in a real tool call."""
        return Agent(
            role="Quantitative Financial Analyst",
            goal="Report real fundamental metrics for a security by calling the database tool",
            backstory="CFA charterholder specializing in small-cap equity research",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            max_execution_time=60,
            memory=True,
            tools=self.tools,
            llm=create_llm(max_completion_tokens=800, temperature=0.1),
            system_message="""Call the institutional database tool for the given ticker
            EXACTLY ONCE, then immediately give your final answer from that one result.
            Do not call the tool again with the same ticker, even if the result looks
            incomplete - report what it gave you and move on. Report ONLY the values the
            tool returns. If the tool errors or a field is missing, say so explicitly -
            never estimate or invent a number to fill a gap, and never retry the call to
            try to get a different answer.

            Output: The tool's fundamental metrics, verbatim, with brief notes on any
            missing data."""
        )

    def create_news_scanner(self):
        """Create news scanning agent. Must ground sentiment in real tool output."""
        return Agent(
            role="Market Intelligence Analyst",
            goal="Report real news and sentiment for a security by calling the database tool",
            backstory="Former hedge fund analyst specializing in event-driven strategies",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            max_execution_time=60,
            memory=True,
            tools=self.tools,
            llm=create_llm(max_completion_tokens=700, temperature=0.2),
            system_message="""Call the institutional database tool (query_type='news') for
            the given ticker EXACTLY ONCE, then immediately give your final answer from
            that one result. Do not call the tool again with the same ticker, even if the
            result looks incomplete - report what it gave you and move on. Summarize ONLY
            what the tool returns. If no news is available, say so explicitly - never
            invent a headline or catalyst, and never retry the call to try to get a
            different answer.

            Output: A short summary of the real news items and sentiment returned."""
        )

    def create_alpha_analyst(self):
        """Create alpha generation analyst. Synthesizes only the grounded data it is given."""
        return Agent(
            role="Senior Portfolio Manager",
            goal="Generate investment recommendations strictly from the data provided",
            backstory="Experienced portfolio manager with a track record in small-cap investing",
            verbose=True,
            allow_delegation=False,
            max_iter=4,
            max_execution_time=90,
            memory=True,
            tools=[],
            llm=create_llm(max_completion_tokens=1500, temperature=0.2),
            system_message="""Generate investment recommendations using ONLY the fundamental
            and news data you are given in context - never data from outside sources or
            your own training knowledge:
            1. Investment thesis grounded in the actual metrics/news provided
            2. BUY/HOLD/SELL recommendation with rationale tied to that data
            3. Key risks, explicitly including any data gaps noted by the analysts
            4. Conviction score (1-10)

            Never discuss a ticker that was not in the provided universe.
            Never cite a metric, source, or catalyst that was not in your context."""
        )


def create_agents():
    """Create all agents."""
    factory = AgentFactory()
    agents = {
        'data_cleaner': factory.create_data_cleaner(),
        'data_enricher': factory.create_data_enricher(),
        'news_scanner': factory.create_news_scanner(),
        'alpha_analyst': factory.create_alpha_analyst()
    }
    logger.info(f"Created {len(agents)} agents")
    return agents


agents = create_agents()
data_cleaner = agents['data_cleaner']
data_enricher = agents['data_enricher']
news_scanner = agents['news_scanner']
alpha_analyst = agents['alpha_analyst']
