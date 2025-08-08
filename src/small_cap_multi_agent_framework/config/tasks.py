"""
Professional Tasks Implementation - Institutional Workflow Integration
======================================================================

Professional task implementations that orchestrate institutional-grade
investment analysis workflows using database-driven research processes.

Author: Small Cap Multi-Agent Framework
License: MIT
"""

from crewai import Task
from small_cap_multi_agent_framework.config.agents import (
    data_cleaner, data_enricher, news_scanner, alpha_analyst
)
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
        logger.info("Professional task factory initialized")
    
    def _load_task_config(self, config_path: Path) -> dict:
        """Load task configurations from YAML file."""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                logger.info(f"Loaded task configuration from {config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load task config: {str(e)}")
            raise
    
    def create_data_normalization_task(self, input_file: str) -> Task:
        """Create institutional data quality assurance task."""
        config = self.config['normalize_smallcap_data']
        
        return Task(
            description=f"""
            {config['description']}
            
            INPUT FILE: {input_file}
            
            SPECIFIC INSTRUCTIONS:
            1. Read the input CSV file and perform comprehensive data validation
            2. Apply institutional data quality standards (99%+ accuracy requirement)
            3. Cross-reference ticker symbols against major exchanges (NASDAQ, NYSE, NYSE American)
            4. Validate market cap calculations and flag discrepancies > 5%
            5. Standardize sector classifications to GICS Level 1 standards
            6. Remove duplicate entries and resolve corporate action issues
            7. Generate data quality scores (0-100) for each record
            8. Create audit trail documentation for compliance
            
            OUTPUT REQUIREMENTS:
            - Clean dataset with consistent formatting
            - Comprehensive audit trail of all cleaning decisions
            - Data quality assessment with scores for each security
            - Exception report for securities requiring manual review
            
            QUALITY STANDARDS:
            - Zero tolerance for ticker symbol errors
            - Market cap accuracy within 2% of calculated values
            - Complete sector classification for all records
            - Comprehensive documentation of all cleaning decisions
            """,
            expected_output=config['expected_output'],
            agent=data_cleaner,
            output_file="output/data_cleaning_report.md"
        )
    
    def create_fundamental_enrichment_task(self) -> Task:
        """Create institutional fundamental analysis task with database integration."""
        config = self.config['enrich_with_fundamentals']
        
        return Task(
            description=f"""
            {config['description']}
            
            DATABASE ACCESS INSTRUCTIONS:
            You have access to institutional-grade financial databases through the 
            query_institutional_database tool. Use the following approach for each security:
            
            1. FUNDAMENTAL ANALYSIS:
               - Use query_type="fundamental" for complete financial metrics
               - Extract P/E ratios, margins, ROE, debt ratios, growth rates
               - Assess financial quality using institutional standards
            
            2. CONTEXTUAL ANALYSIS:
               - Use query_type="news" for market sentiment context
               - Evaluate how news sentiment aligns with fundamentals
               - Identify potential catalysts affecting valuation
            
            ANALYTICAL FRAMEWORK:
            For each security in the cleaned dataset:
            1. Query institutional database for latest financial metrics
            2. Assess financial quality and identify any red flags
            3. Evaluate growth trajectories and margin trends
            4. Analyze balance sheet strength and liquidity position
            5. Generate comprehensive financial profiles with risk assessment
            6. Provide sector-relative positioning where possible
            
            OUTPUT REQUIREMENTS:
            - Comprehensive fundamental analysis for each security
            - Financial quality assessment with red flag identification
            - Growth and profitability trend analysis
            - Balance sheet strength evaluation
            - Risk assessment and quality scores
            """,
            expected_output=config['expected_output'],
            agent=data_enricher,
            context=[],  # Will be set dynamically
            output_file="output/fundamental_analysis_report.md"
        )
    
    def create_market_intelligence_task(self) -> Task:
        """Create institutional market intelligence and sentiment analysis task."""
        config = self.config['scan_news_and_sentiment']
        
        return Task(
            description=f"""
            {config['description']}
            
            DATABASE INTELLIGENCE GATHERING:
            You have access to institutional alternative data platforms through the 
            query_institutional_database tool. Use these approaches for each security:
            
            1. NEWS & SENTIMENT ANALYSIS:
               - Use query_type="news" for recent headlines and sentiment scores
               - Analyze narrative themes and media coverage patterns
               - Quantify sentiment momentum and identify trend changes
            
            2. FUNDAMENTAL CONTEXT:
               - Use query_type="fundamental" to understand business context
               - Correlate news sentiment with underlying business performance
               - Identify disconnect between sentiment and fundamentals
            
            INTELLIGENCE SYNTHESIS:
            For each security:
            1. Comprehensive news flow analysis with sentiment quantification
            2. Identification of key narrative themes and market perception
            3. Catalyst identification with probability and impact assessments
            4. Risk event monitoring and early warning indicators
            5. Market sentiment trend analysis and momentum assessment
            6. Correlation analysis between sentiment and fundamental performance
            
            OUTPUT REQUIREMENTS:
            - Detailed sentiment analysis with quantitative scores
            - Narrative theme identification and trend analysis
            - Catalyst calendar with probability and impact assessments
            - Risk monitoring alerts and early warning indicators
            - Market intelligence summary with actionable insights
            """,
            expected_output=config['expected_output'],
            agent=news_scanner,
            context=[],  # Will be set dynamically
            output_file="output/market_intelligence_report.md"
        )
    
    def create_alpha_generation_task(self) -> Task:
        """Create institutional investment recommendation task."""
        config = self.config['generate_alpha_report']
        
        return Task(
            description=f"""
            {config['description']}
            
            INSTITUTIONAL ANALYSIS SYNTHESIS:
            You have access to the complete institutional database through query_institutional_database.
            Synthesize ALL available data sources for comprehensive investment analysis:
            
            1. COMPREHENSIVE DATA INTEGRATION:
               - Use query_type="fundamental" for complete financial analysis
               - Use query_type="news" for sentiment and narrative evaluation
               - Integrate findings from data cleaning and enrichment phases
               - Cross-reference all data sources for consistency
            
            2. INVESTMENT RANKING METHODOLOGY:
               - Value Assessment: P/E, P/B, EV/Revenue relative to fundamentals
               - Quality Evaluation: ROE, margins, debt ratios, earnings stability
               - Growth Analysis: Revenue/earnings trends and sustainability
               - Sentiment Integration: News flow and market perception analysis
               - Risk Assessment: Balance sheet strength and business risk factors
            
            3. PORTFOLIO CONSTRUCTION CONSIDERATIONS:
               - Risk-adjusted return estimation with confidence intervals
               - Position sizing recommendations based on conviction levels
               - Correlation analysis for portfolio diversification
               - Liquidity assessment and trading considerations
               - Catalyst timing and probability weighting
            
            INVESTMENT THESIS DEVELOPMENT:
            For top-ranked securities:
            1. Comprehensive fundamental and sentiment analysis integration
            2. Bull/base/bear case scenario development
            3. Catalyst identification with timing and probability assessments
            4. Risk factor analysis and mitigation strategies
            5. Price target methodology and confidence intervals
            6. Position sizing and portfolio allocation recommendations
            
            OUTPUT REQUIREMENTS:
            - Executive summary with top investment recommendations
            - Detailed investment profiles with complete rationale
            - Risk-adjusted ranking with quantitative and qualitative factors
            - Portfolio construction guidance with allocation recommendations
            - Implementation strategy with specific entry/exit criteria
            - Ongoing monitoring framework with key performance indicators
            """,
            expected_output=config['expected_output'],
            agent=alpha_analyst,
            context=[],  # Will be set dynamically
            output_file="output/alpha_investment_report.md"
        )

def create_professional_task_workflow(input_file: str):
    """Create complete institutional investment analysis workflow."""
    
    try:
        factory = ProfessionalTaskFactory()
        
        # Create tasks in institutional workflow order
        data_normalization = factory.create_data_normalization_task(input_file)
        fundamental_enrichment = factory.create_fundamental_enrichment_task()
        market_intelligence = factory.create_market_intelligence_task()
        alpha_generation = factory.create_alpha_generation_task()
        
        # Set task dependencies for institutional workflow
        fundamental_enrichment.context = [data_normalization]
        market_intelligence.context = [data_normalization]
        alpha_generation.context = [fundamental_enrichment, market_intelligence]
        
        tasks = [
            data_normalization,
            fundamental_enrichment, 
            market_intelligence,
            alpha_generation
        ]
        
        logger.info("Professional task workflow created successfully")
        return tasks
        
    except Exception as e:
        logger.error(f"Failed to create professional task workflow: {str(e)}")
        raise

# Task instances for import
try:
    # Create default workflow with placeholder input
    _default_tasks = create_professional_task_workflow("data/small_caps_input.csv")
    
    normalize_smallcap_data = _default_tasks[0]
    enrich_with_fundamentals = _default_tasks[1]
    scan_news_and_sentiment = _default_tasks[2]
    generate_alpha_report = _default_tasks[3]
    
    logger.info("Professional tasks ready for deployment")
    
except Exception as e:
    logger.error(f"Task initialization failed: {str(e)}")
    # Create fallback basic tasks if configuration isn't available
    logger.warning("Creating fallback tasks with basic configuration")
    
    normalize_smallcap_data = Task(
        description="Clean and format the input dataset of small-cap stocks",
        expected_output="A clean CSV with consistent columns",
        agent=data_cleaner
    )
    
    enrich_with_fundamentals = Task(
        description="Fetch financial metrics for each stock using institutional database",
        expected_output="Dataset with comprehensive financial metrics",
        agent=data_enricher,
        context=[normalize_smallcap_data]
    )
    
    scan_news_and_sentiment = Task(
        description="Gather news and sentiment analysis for each stock",
        expected_output="Comprehensive sentiment analysis summary",
        agent=news_scanner,
        context=[normalize_smallcap_data]
    )
    
    generate_alpha_report = Task(
        description="Generate institutional-quality investment recommendations",
        expected_output="Professional investment report with rankings",
        agent=alpha_analyst,
        context=[enrich_with_fundamentals, scan_news_and_sentiment]
    )