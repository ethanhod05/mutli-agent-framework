"""
Professional Tasks Implementation - GPT-5-mini Optimized
=========================================================

Professional task implementations that orchestrate institutional-grade
investment analysis workflows using GPT-5-mini powered agents.

Author: Small Cap Multi-Agent Framework
License: MIT
"""

from crewai import Task
# === MODIFIED IMPORTS ===
from small_cap_multi_agent_framework.config.agents import (
    data_cleaner, data_enricher, news_scanner, alpha_analyst,
    ticker_researcher # Import the new agent
)
# ========================
import yaml
import os
from pathlib import Path
import logging

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProfessionalTaskFactory:
    """Factory for creating institutional-grade investment analysis tasks."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / 'tasks.yaml'
        
        self.config = self._load_task_config(config_path)
        logger.info("Professional task factory initialized with GPT-5-mini agents")
    
    def _load_task_config(self, config_path: Path) -> dict:
        """Load task configurations from YAML file."""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                logger.info(f"Loaded task configuration from {config_path}")
                return config
        except Exception as e:
            logger.warning(f"Could not load task config from {config_path}: {str(e)}")
            logger.info("Using default task configuration")
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """Get default task configuration if YAML is not available."""
        return {
            'discover_tickers': {
                'description': 'Discover promising small-cap stock tickers',
                'expected_output': 'A Python list of ticker symbols'
            },
            'generate_alpha_report': {
                'description': 'Generate investment recommendations from a list of tickers',
                'expected_output': 'Professional investment report with rankings'
            }
        }
    
    # === NEW TASK METHOD START ===
    def create_discovery_task(self) -> Task:
        """Create a task to discover tickers."""
        config = self.config.get('discover_tickers', {})
        return Task(
            description=config.get('description', "Use the 'Ticker Discovery Tool' to get a list of small-cap stocks for analysis. Your final output must be just the Python list of ticker symbols."),
            expected_output=config.get('expected_output', "A Python list of stock ticker strings, for example ['TICKER1', 'TICKER2', 'TICKER3']"),
            agent=ticker_researcher
        )
    # === NEW TASK METHOD END ===

    # Note: The data_normalization, fundamental_enrichment, and market_intelligence tasks are no longer
    # needed for the main workflow but can be kept for other purposes or removed.
    # We will focus on modifying the alpha_generation_task.
    
    def create_alpha_generation_task(self) -> Task:
        """Create investment recommendation task."""
        config = self.config.get('generate_alpha_report', {})
        
        # === MODIFIED TASK DESCRIPTION ===
        return Task(
            description=f"""
            {config.get('description', 'Synthesize all available data to create actionable recommendations for the provided list of tickers.')}

            CONTEXT: You have received a list of tickers from the Ticker Research Specialist.

            YOUR PROCESS:
            1. For EACH ticker in the list, delegate the fundamental analysis to the 'Quantitative Financial Analyst' and the market intelligence analysis to the 'Market Intelligence Analyst'.
            2. Once the analyses are complete, synthesize all the data.
            3. Rank all securities using a clear methodology (Value, Quality, Growth, Sentiment).
            4. Develop a detailed investment thesis and price target for the top-ranked securities.
            5. Provide a final report with clear BUY/HOLD/SELL ratings.
            """,
            expected_output=config.get('expected_output', 'Professional investment report with rankings'),
            agent=alpha_analyst,
            context=[],  # This will be set dynamically in the workflow function
            output_file="output/alpha_investment_report.md"
        )
    
# === COMPLETELY REWRITTEN WORKFLOW FUNCTION ===
def create_professional_task_workflow(input_file: str = None):
    """Create complete investment analysis workflow optimized for GPT-5-mini."""
    try:
        factory = ProfessionalTaskFactory()
        
        logger.info(f"Creating a dynamic, multi-step task workflow...")
        
        # Step 1: Create the task that discovers the tickers.
        discovery_task = factory.create_discovery_task()
        
        # Step 2: Create the main analysis task.
        alpha_generation_task = factory.create_alpha_generation_task()

        # Step 3: Set the dependency. The output of discovery_task will be
        # automatically passed as context to the alpha_generation_task.
        alpha_generation_task.context = [discovery_task]
        
        tasks = [discovery_task, alpha_generation_task]
        
        logger.info(f"✅ Created dynamic workflow with {len(tasks)} tasks.")
        logger.info("Task order: Discover Tickers -> Generate Alpha Report")
        
        return tasks
        
    except Exception as e:
        logger.error(f"Failed to create task workflow: {str(e)}")
        raise

# Initialize tasks when module is imported
try:
    # We no longer need to pass a default file, as the workflow is dynamic
    _default_tasks = create_professional_task_workflow()
    
    # Export individual tasks
    discover_tickers_task = _default_tasks[0]
    generate_alpha_report_task = _default_tasks[1]
    
    logger.info("✅ Professional dynamic tasks ready for deployment with GPT-5-mini")
    
except Exception as e:
    logger.error(f"Critical error during task initialization: {str(e)}")
    raise