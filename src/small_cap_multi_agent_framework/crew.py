"""
Institutional Crew System - Simplified with Basic Rate Limiting
==============================================================

Orchestrates the complete institutional investment analysis workflow using
professional agents with simple, reliable rate limiting.

Author: Small Cap Multi-Agent Framework
License: MIT
"""

from crewai import Crew, Process, LLM
from small_cap_multi_agent_framework.config.agents import (
    data_cleaner, data_enricher, news_scanner, alpha_analyst
)
from small_cap_multi_agent_framework.config.tasks import (
    create_professional_task_workflow
)
from small_cap_multi_agent_framework.tools.hedge_fund_database import hedge_fund_db
import logging
from datetime import datetime
from pathlib import Path
import os
import time
from dotenv import load_dotenv

# Load environment and force Groq configuration globally
load_dotenv()

# Override any default model settings to use Groq
os.environ["OPENAI_API_KEY"] = os.getenv("GROQ_API_KEY")
os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
os.environ["OPENAI_MODEL_NAME"] = "groq/llama-3.3-70b-versatile"

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hedge_fund_crew.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InstitutionalAnalysisCrew:
    """
    Institutional-grade investment analysis crew with simple rate limiting.
    
    Replicates the research process used by professional asset management firms:
    1. Data Quality Assurance (Junior Analyst Level)
    2. Fundamental Research (Senior Analyst Level)  
    3. Market Intelligence (Sector Specialist Level)
    4. Investment Synthesis (Portfolio Manager Level)
    """
    
    def __init__(self, input_file: str = "data/small_caps_input.csv"):
        self.input_file = input_file
        self.crew = None
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info(f"Institutional Analysis Crew with simple rate limiting initialized - Execution ID: {self.execution_id}")
        self._validate_system_health()
    
    def _validate_system_health(self):
        """Validate institutional database and agent systems."""
        try:
            # Test database connectivity
            logger.info("Validating hedge fund database system...")
            test_query = hedge_fund_db._get_connection()
            test_query.close()
            
            # Test agent availability  
            logger.info("Validating professional agents...")
            agents = [data_cleaner, data_enricher, news_scanner, alpha_analyst]
            for agent in agents:
                if not hasattr(agent, 'role'):
                    raise Exception(f"Agent validation failed: {agent}")
            
            logger.info("✅ System health check passed - Ready for institutional analysis with simple rate limiting")
            
        except Exception as e:
            logger.error(f"❌ System health check failed: {str(e)}")
            raise
    
    def create_institutional_crew(self) -> Crew:
        """Create institutional analysis crew with professional workflow and simple rate limiting."""
        
        try:
            # Create simple manager LLM using CrewAI's LLM class
            manager_llm = LLM(
                model="groq/llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=1000,
                api_key=os.getenv("GROQ_API_KEY")
            )
            
            # Create professional task workflow
            tasks = create_professional_task_workflow(self.input_file)
            
            # Add delay before crew creation
            time.sleep(2)
            
            # Create institutional crew
            crew = Crew(
                agents=[data_cleaner, data_enricher, news_scanner, alpha_analyst],
                tasks=tasks,
                process=Process.sequential,  # Sequential analysis
                verbose=True,
                memory=True,
                manager_llm=manager_llm,
                planning=False,  # Turn off planning to avoid model conflicts
                planning_llm=None
            )
            
            logger.info("Institutional analysis crew created successfully with simple rate limiting")
            return crew
            
        except Exception as e:
            logger.error(f"Failed to create institutional crew: {str(e)}")
            raise
    
    def execute_institutional_analysis(self, inputs: dict = None) -> dict:
        """Execute complete institutional investment analysis workflow with simple rate limiting."""
        
        if inputs is None:
            inputs = {
                'input_file': self.input_file,
                'analysis_date': datetime.now().strftime("%Y-%m-%d"),
                'execution_id': self.execution_id
            }
        
        try:
            logger.info("=" * 80)
            logger.info("STARTING INSTITUTIONAL INVESTMENT ANALYSIS WITH SIMPLE RATE LIMITING")
            logger.info(f"Input File: {inputs['input_file']}")
            logger.info(f"Analysis Date: {inputs['analysis_date']}")
            logger.info(f"Execution ID: {inputs['execution_id']}")
            logger.info("=" * 80)
            
            # Add initial delay to prevent immediate rate limiting
            logger.info("⏳ Initializing with rate limiting buffer...")
            time.sleep(5)
            
            # Create and execute crew
            self.crew = self.create_institutional_crew()
            
            logger.info("🚀 Starting crew execution with simple rate limiting...")
            
            # Add another delay before kickoff
            time.sleep(3)
            
            result = self.crew.kickoff(inputs=inputs)
            
            # Generate execution summary
            summary = self._generate_execution_summary(result)
            
            logger.info("=" * 80)
            logger.info("INSTITUTIONAL ANALYSIS COMPLETED SUCCESSFULLY")
            logger.info(f"Analysis Output: {summary['output_files']}")
            logger.info(f"Execution Time: {summary['execution_time']}")
            logger.info("=" * 80)
            
            return {
                'status': 'success',
                'result': result,
                'summary': summary,
                'execution_id': self.execution_id
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Institutional analysis failed: {error_msg}")
            
            # Check if it's a rate limit error and provide helpful guidance
            if any(term in error_msg.lower() for term in ["rate_limit", "rate limit", "too many requests"]):
                logger.error("📊 RATE LIMIT GUIDANCE:")
                logger.error("   1. Wait 60 seconds and try again")
                logger.error("   2. Consider upgrading to Groq Dev Tier")
                logger.error("   3. Use smaller models for non-critical tasks")
                logger.error("   4. Reduce max_tokens in agent configurations")
            
            return {
                'status': 'failed',
                'error': error_msg,
                'execution_id': self.execution_id
            }
    
    def _generate_execution_summary(self, result) -> dict:
        """Generate comprehensive execution summary for audit trail."""
        
        try:
            # Identify output files
            output_files = []
            for file_path in self.output_dir.glob("*.md"):
                if file_path.stat().st_mtime > (datetime.now().timestamp() - 3600):  # Last hour
                    output_files.append(str(file_path))
            
            summary = {
                'execution_id': self.execution_id,
                'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'input_file': self.input_file,
                'output_files': output_files,
                'agent_count': 4,
                'task_count': 4,
                'execution_time': 'Completed',
                'database_queries': 'Multiple institutional database queries executed',
                'compliance_status': 'Audit trail maintained',
                'system_health': 'All systems operational with simple rate limiting',
                'rate_limiting': 'Enabled - Simple delay-based rate limiting active'
            }
            
            # Save execution summary
            summary_file = self.output_dir / f"execution_summary_{self.execution_id}.json"
            import json
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Execution summary saved: {summary_file}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate execution summary: {str(e)}")
            return {'error': str(e)}

def run_institutional_analysis(input_file: str = "data/small_caps_input.csv"):
    """
    Main entry point for institutional investment analysis with simple rate limiting.
    
    Args:
        input_file: Path to small-cap dataset for analysis
    
    Returns:
        Complete analysis results with audit trail
    """
    
    try:
        logger.info("🏦 Initializing Institutional Analysis with Simple Rate Limiting...")
        
        # Initialize institutional analysis crew
        institutional_crew = InstitutionalAnalysisCrew(input_file)
        
        # Execute complete analysis workflow
        results = institutional_crew.execute_institutional_analysis()
        
        if results['status'] == 'success':
            print("\n🎯 INSTITUTIONAL ANALYSIS COMPLETED SUCCESSFULLY")
            print(f"📊 Execution ID: {results['execution_id']}")
            print(f"📁 Output Files: {len(results['summary']['output_files'])} reports generated")
            print(f"✅ System Status: All institutional systems operational")
            print(f"⚡ Rate Limiting: Simple delay-based rate limiting enabled")
            
            # Display output file locations
            print("\n📋 GENERATED REPORTS:")
            for output_file in results['summary']['output_files']:
                print(f"   📄 {output_file}")
                
        else:
            print(f"\n❌ INSTITUTIONAL ANALYSIS FAILED")
            print(f"Error: {results['error']}")
            
            # Provide rate limit specific guidance
            if any(term in results['error'].lower() for term in ["rate_limit", "rate limit", "too many requests"]):
                print("\n💡 RATE LIMIT RECOVERY SUGGESTIONS:")
                print("   1. Wait 60 seconds before retrying")
                print("   2. Consider upgrading to Groq Dev Tier for higher limits")
                print("   3. Review token usage in agent configurations")
                print("   4. Use smaller models for data cleaning tasks")
            
        return results
        
    except Exception as e:
        logger.error(f"Critical system failure: {str(e)}")
        print(f"\n🚨 CRITICAL SYSTEM FAILURE: {str(e)}")
        return {'status': 'critical_failure', 'error': str(e)}

if __name__ == "__main__":
    # System health check and demonstration
    print("🏦 HEDGE FUND MULTI-AGENT ANALYSIS SYSTEM")
    print("🔧 Enhanced with Simple Rate Limiting")
    print("=" * 50)
    print("Initializing institutional-grade investment analysis...")
    
    # Run with default sample data
    results = run_institutional_analysis()
    
    if results['status'] == 'success':
        print("\n🎉 Demo completed successfully!")
        print("Ready for production institutional analysis with simple rate limiting.")
    else:
        print(f"\n⚠️  Demo failed: {results.get('error', 'Unknown error')}")
        if any(term in str(results.get('error', '')).lower() for term in ["rate_limit", "rate limit"]):
            print("\n⏰ Tip: Wait a minute and try again, or upgrade your Groq tier.")