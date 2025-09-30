"""
Multi-Agent Configuration - GPT-5-mini
=======================================

Practical implementation using OpenAI GPT-5-mini.
Clean, simple, and ready to run.
"""

from crewai import Agent, LLM
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
try:
    from small_cap_multi_agent_framework.tools.ticker_discovery_tool import ticker_discovery_tool
    logger.info("✅ Ticker discovery tool loaded")
except ImportError:
    ticker_discovery_tool = None
    logger.warning("⚠️  Ticker discovery tool not found")

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found. Please add it to your .env file")

logger.info("✅ OpenAI API configured")

# Detect which model to use
def detect_model():
    """Try gpt-5-mini first, fallback to gpt-4o-mini"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Try GPT-5-mini
        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return "gpt-5-mini"
        except:
            # Fallback to gpt-4o-mini
            return "gpt-4o-mini"
    except:
        return "gpt-4o-mini"

MODEL_NAME = detect_model()
logger.info(f"🚀 Using {MODEL_NAME} for all agents")

def create_llm(max_completion_tokens=1000, temperature=0.2):
    """Create LLM instance with correct parameters for new OpenAI API."""
    return LLM(
        model=MODEL_NAME,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,  # Changed from max_tokens
        api_key=os.getenv("OPENAI_API_KEY")
    )

class AgentFactory:
    """Factory for creating agents with correct API parameters."""
    
    def __init__(self):
        logger.info(f"Initializing agent factory with {MODEL_NAME}...")
        
        # Log configuration
        logger.info("\n" + "="*50)
        logger.info(f"MODEL CONFIGURATION: {MODEL_NAME}")
        logger.info("="*50)
        logger.info("Using max_completion_tokens (new API parameter)")
        logger.info("Expected cost: ~$0.002-0.003 per security")
        logger.info("Throughput: 50-100 securities per minute")
        logger.info("="*50)
        
        # Try to import tools if available
        self.tools = self._load_tools()
    
    def _load_tools(self):
        """Load tools if available."""
        try:
            from small_cap_multi_agent_framework.tools.hedge_fund_database import query_institutional_database
            logger.info("✅ Database tools loaded")
            
            loaded_tools = [query_institutional_database]
            if ticker_discovery_tool:
                loaded_tools.append(ticker_discovery_tool)
            return loaded_tools

        except ImportError:
            logger.warning("⚠️  Database tools not found - agents will work without them")
            return []

    # === NEW AGENT METHOD START ===
    def create_ticker_researcher(self):
        """Create a ticker research agent."""
        # This agent only gets the discovery tool to ensure it stays on task.
        discovery_tools = [tool for tool in self.tools if tool.name == "Ticker Discovery Tool"]
        if not discovery_tools:
            logger.error("Ticker Discovery Tool is required for the Ticker Research Specialist but was not found.")
            # Return a non-functional agent or raise an error
            return Agent(role="Ticker Research Specialist", goal="Discover tickers (Tool not found)", backstory="Tool missing", verbose=True)

        return Agent(
            role="Ticker Research Specialist",
            goal="Discover a list of relevant small-cap stock tickers for analysis",
            backstory="An expert at scanning the market to identify promising companies based on predefined criteria.",
            verbose=True,
            allow_delegation=False,
            max_iter=2,
            memory=True,
            tools=discovery_tools,
            llm=create_llm(max_completion_tokens=500, temperature=0.1),
            system_message="Your sole purpose is to use the 'Ticker Discovery Tool' to find stocks. Output only the list of tickers you find."
        )
    # === NEW AGENT METHOD END ===

    def create_data_cleaner(self):
        """Create data cleaning agent."""
        return Agent(
            role="Financial Data Quality Specialist",
            goal="Ensure data accuracy and standardization",
            backstory="Expert in financial data validation with focus on small-cap securities",
            verbose=True,
            allow_delegation=False,
            max_iter=2,
            memory=True,
            tools=[],
            llm=create_llm(max_completion_tokens=800, temperature=0.1),
            system_message="""Validate and clean financial data:
            1. Check ticker symbols and exchange listings
            2. Verify market cap calculations
            3. Standardize sector classifications to GICS
            4. Flag any data quality issues
            5. Ensure consistency across fields
            
            Output: Cleaned data with brief summary of issues found."""
        )
    
    def create_data_enricher(self):
        """Create data enrichment agent."""
        return Agent(
            role="Quantitative Financial Analyst",
            goal="Enrich securities with fundamental analysis",
            backstory="CFA charterholder specializing in small-cap equity research",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True,
            tools=self.tools,
            llm=create_llm(max_completion_tokens=1200, temperature=0.2),
            system_message="""Perform fundamental analysis for each security:
            1. Calculate key valuation metrics (P/E, P/B, EV/EBITDA)
            2. Analyze profitability (ROE, ROA, margins)
            3. Assess growth metrics (revenue and earnings growth)
            4. Evaluate financial health (debt ratios, liquidity)
            5. Generate quality score (1-10)
            
            Focus on metrics most relevant for small-cap investing.
            Output: Structured analysis with key metrics and scores."""
        )
    
    def create_news_scanner(self):
        """Create news scanning agent."""
        return Agent(
            role="Market Intelligence Analyst",
            goal="Extract insights from news and sentiment",
            backstory="Former hedge fund analyst specializing in event-driven strategies",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True,
            tools=self.tools,
            llm=create_llm(max_completion_tokens=1000, temperature=0.3),
            system_message="""Analyze news and sentiment for each security:
            1. Assess overall sentiment (-100 to +100)
            2. Identify key catalysts or events
            3. Evaluate news volume vs. historical average
            4. Flag any significant risks or opportunities
            5. Determine momentum (improving/stable/deteriorating)
            
            Output: Sentiment analysis with specific catalysts identified."""
        )
    
    def create_alpha_analyst(self):
        """Create alpha generation analyst."""
        # === START MODIFICATION ===
        # The manager should only have the delegation tool. Let's filter for it.
        # NOTE: CrewAI automatically provides the delegation tool if allow_delegation=True,
        # so setting tools=[] is the correct way to ensure it can ONLY delegate.
        manager_tools = []
        # ==========================
        return Agent(
            role="Senior Portfolio Manager",
            goal="Generate actionable investment recommendations",
            backstory="Experienced portfolio manager with track record in small-cap investing",
            verbose=True,
            allow_delegation=True,
            max_iter=4,
            memory=True,
            # === USE THE NEW EMPTY TOOL LIST ===
            tools=manager_tools,
            # ===================================
            llm=create_llm(max_completion_tokens=1500, temperature=0.2),
            system_message="""Generate investment recommendations based on all analysis:
            1. Investment thesis (3-5 key points)
            2. Price target and expected return
            3. Suggested position size (% of portfolio)
            4. Entry and exit strategy
            5. Key risks to monitor
            6. Conviction score (1-10)
            
            Provide clear BUY/HOLD/SELL recommendation with rationale.
            Output: Concise investment memo with specific action items."""
        )

def create_agents():
    """Create all agents."""
    try:
        factory = AgentFactory()
        
        logger.info("\nCreating agent team...")
        
        # === MODIFIED AGENT DICTIONARY ===
        agents = {
            'ticker_researcher': factory.create_ticker_researcher(),
            'data_cleaner': factory.create_data_cleaner(),
            'data_enricher': factory.create_data_enricher(),
            'news_scanner': factory.create_news_scanner(),
            'alpha_analyst': factory.create_alpha_analyst()
        }
        # ================================
        
        logger.info(f"✅ Created {len(agents)} agents successfully")
        
        # Cost estimate
        cost_per_security = 0.0025
        logger.info(f"💰 Estimated cost: ~${cost_per_security:.3f} per security")
        logger.info(f"📈 Expected throughput: 50-100 securities per minute")
        
        return agents
        
    except Exception as e:
        logger.error(f"Failed to create agents: {str(e)}")
        raise

# Test function
def test_setup():
    """Quick test to verify setup works."""
    try:
        logger.info("\n🧪 Testing setup...")
        
        # Test LLM creation with new parameter
        test_llm = create_llm(max_completion_tokens=50)
        
        # Create a simple test agent
        test_agent = Agent(
            role="Test Agent",
            goal="Verify setup",
            backstory="Testing the configuration",
            verbose=True,
            llm=test_llm
        )
        
        logger.info(f"✅ Setup test passed with {MODEL_NAME}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup test failed: {str(e)}")
        return False

# When imported as a module, create and export agents
try:
    agents = create_agents()
    # === EXPORT THE NEW AGENT ===
    ticker_researcher = agents['ticker_researcher']
    # ============================
    data_cleaner = agents['data_cleaner']
    data_enricher = agents['data_enricher']
    news_scanner = agents['news_scanner']
    alpha_analyst = agents['alpha_analyst']
except Exception as e:
    logger.error(f"Failed to initialize agents on import: {str(e)}")

if __name__ == "__main__":
    if test_setup():
        logger.info(f"\n✅ All {len(agents)} agents ready to use with {MODEL_NAME}!")
    else:
        logger.error("Please fix the setup issues before proceeding")