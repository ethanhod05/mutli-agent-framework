"""
Professional Agents Implementation - Hedge Fund Database Integration
===================================================================

Professional agent implementations that access institutional-grade database
systems, mirroring real hedge fund research workflows.

Author: Small Cap Multi-Agent Framework
License: MIT
"""

from crewai import Agent
from small_cap_multi_agent_framework.tools.hedge_fund_database import query_institutional_database
import yaml
import os
from pathlib import Path
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables and configure Groq
load_dotenv()

# Configure Groq API
if os.getenv("GROQ_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.getenv("GROQ_API_KEY")
    os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
    os.environ["OPENAI_MODEL_NAME"] = "groq/llama-3.3-70b-versatile"
    
    print("✅ Configured to use free Groq API")
    print("🚀 Model: Llama 3.3 70B (high performance)")
    print("💰 Cost: $0.00 (free tier)")

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProfessionalAgentFactory:
    """Factory for creating professional hedge fund agents with database access."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / 'agents.yaml'
        
        self.config = self._load_agent_config(config_path)
        logger.info("Professional agent factory initialized")
    
    def _load_agent_config(self, config_path: Path) -> dict:
        """Load agent configurations from YAML file."""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                logger.info(f"Loaded agent configuration from {config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load agent config: {str(e)}")
            raise
    
    def create_data_cleaner(self) -> Agent:
        """Create the Senior Financial Data Quality Specialist agent."""
        config = self.config['data_cleaner']
        
        groq_llm = ChatGroq(
            model="groq/llama-3.3-70b-versatile",
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        return Agent(
            role=config['role'],
            goal=config['goal'],
            backstory=config['backstory'],
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True,
            tools=[],  # Data cleaner works with raw CSV files
            llm=groq_llm,
            system_message="""You are a Senior Financial Data Quality Specialist with 8+ years of 
            experience at Bloomberg and FactSet. You understand the critical importance of data 
            integrity in institutional investment decision-making. Every dataset you clean must 
            meet the standards used by portfolio managers managing billions in assets.
            
            Key responsibilities:
            1. Validate ticker symbols against major exchanges
            2. Verify market capitalization calculations
            3. Standardize sector classifications using GICS standards
            4. Flag any data quality issues for manual review
            5. Maintain detailed audit trails for compliance
            
            Always document your cleaning decisions and provide data quality scores."""
        )
    
    def create_data_enricher(self) -> Agent:
        """Create the Quantitative Research Analyst agent with database access."""
        config = self.config['data_enricher']
        
        groq_llm = ChatGroq(
            model="groq/llama-3.3-70b-versatile",
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        return Agent(
            role=config['role'],
            goal=config['goal'],
            backstory=config['backstory'],
            verbose=True,
            allow_delegation=False,
            max_iter=4,
            memory=True,
            tools=[query_institutional_database],
            llm=groq_llm,
            system_message="""You are a CFA charterholder and quantitative research analyst 
            specializing in small-cap equity analysis. You have direct access to institutional-grade 
            financial databases equivalent to Bloomberg Terminal and FactSet Workstation.
            
            Your analysis must include:
            1. Comprehensive fundamental metrics using database queries
            2. Sector-relative positioning and percentile rankings
            3. Financial quality assessment and red flag identification
            4. Growth trajectory analysis with 3-year historical context
            5. Balance sheet strength and liquidity analysis
            
            Use the query_institutional_database tool with these query types:
            - "fundamental" for complete financial analysis
            - "news" for sentiment context
            
            Always provide institutional-quality analysis that portfolio managers can trust."""
        )
    
    def create_news_scanner(self) -> Agent:
        """Create the Market Intelligence Analyst agent with alternative data access."""
        config = self.config['news_scanner']
        
        groq_llm = ChatGroq(
            model="groq/llama-3.3-70b-versatile",
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        return Agent(
            role=config['role'],
            goal=config['goal'],
            backstory=config['backstory'],
            verbose=True,
            allow_delegation=False,
            max_iter=5,
            memory=True,
            tools=[query_institutional_database],
            llm=groq_llm,
            system_message="""You are a Market Intelligence Analyst with hedge fund experience 
            in event-driven strategies and alternative data analysis. You have access to institutional-grade 
            news databases, sentiment analysis platforms, and insider trading monitoring systems.
            
            Your analysis must include:
            1. Comprehensive news flow analysis with sentiment quantification
            2. Catalyst identification and probability assessment
            3. Market narrative analysis and theme identification
            4. Risk event monitoring and impact assessment
            
            Use the query_institutional_database tool with:
            - "news" for sentiment analysis and recent headlines
            - "fundamental" for context on financial health
            
            Focus on actionable intelligence that can impact investment decisions."""
        )
    
    def create_alpha_analyst(self) -> Agent:
        """Create the Senior Portfolio Manager agent for investment recommendations."""
        config = self.config['alpha_analyst']
        
        groq_llm = ChatGroq(
            model="groq/llama-3.3-70b-versatile",
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        return Agent(
            role=config['role'],
            goal=config['goal'],
            backstory=config['backstory'],
            verbose=True,
            allow_delegation=True,
            max_iter=6,
            memory=True,
            tools=[query_institutional_database],
            llm=groq_llm,
            system_message="""You are a Senior Portfolio Manager with 12+ years of experience 
            managing small-cap strategies at institutional asset management firms. You have a 
            proven track record of generating alpha and beating benchmarks through rigorous 
            fundamental analysis combined with precise timing.
            
            Your investment recommendations must include:
            1. Comprehensive synthesis of fundamental and sentiment analysis
            2. Risk-adjusted return calculations with confidence intervals
            3. Position sizing recommendations based on conviction and risk
            4. Specific entry/exit strategies with price targets
            5. Catalyst-driven investment thesis with timing considerations
            
            Use ALL available database query types to build complete investment profiles:
            - "fundamental" for financial analysis
            - "news" for sentiment and narrative analysis
            
            Your output must be institutional-quality investment research that investment 
            committees can use for fiduciary decision-making."""
        )

# Create global agent instances
def create_professional_agents():
    """Create all professional agents with database access."""
    try:
        factory = ProfessionalAgentFactory()
        
        agents = {
            'data_cleaner': factory.create_data_cleaner(),
            'data_enricher': factory.create_data_enricher(), 
            'news_scanner': factory.create_news_scanner(),
            'alpha_analyst': factory.create_alpha_analyst()
        }
        
        logger.info("All professional agents created successfully")
        return agents
        
    except Exception as e:
        logger.error(f"Failed to create professional agents: {str(e)}")
        raise

# Agent instances for import
try:
    _agents = create_professional_agents()
    data_cleaner = _agents['data_cleaner']
    data_enricher = _agents['data_enricher']
    news_scanner = _agents['news_scanner']
    alpha_analyst = _agents['alpha_analyst']
    
    logger.info("Professional agents ready for deployment")
    
except Exception as e:
    logger.error(f"Agent initialization failed: {str(e)}")
    # Create fallback basic agents if database isn't available
    logger.warning("Creating fallback agents without database access")
    
    data_cleaner = Agent(
        role="Financial Data Normalizer",
        goal="Clean and standardize small-cap datasets",
        backstory="You specialize in data quality assurance",
        verbose=True
    )
    
    data_enricher = Agent(
        role="Fundamentals Enricher", 
        goal="Gather financial metrics and analysis",
        backstory="You are skilled at financial analysis",
        verbose=True,
        tools=[query_institutional_database]
    )
    
    news_scanner = Agent(
        role="Market Narrative Watcher",
        goal="Monitor news and sentiment", 
        backstory="You track market intelligence",
        verbose=True,
        tools=[query_institutional_database]
    )
    
    alpha_analyst = Agent(
        role="Investment Alpha Generator",
        goal="Generate investment recommendations",
        backstory="You create actionable investment ideas",
        verbose=True,
        tools=[query_institutional_database]
    )