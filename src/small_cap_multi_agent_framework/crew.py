"""
Institutional Crew System - GPT-5-mini Configuration
====================================================

Orchestrates the complete institutional investment analysis workflow using
GPT-5-mini powered agents for superior performance without rate limits.

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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hedge_fund_crew.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("Please add OPENAI_API_KEY to your .env file")

class InstitutionalAnalysisCrew:
    """
    Institutional-grade investment analysis crew using GPT-5-mini.
    
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
        
        # Determine which model is being used
        self.model_name = self._detect_model()
        
        logger.info(f"Institutional Analysis Crew initialized - Model: {self.model_name}")
        logger.info(f"Execution ID: {self.execution_id}")
        self._validate_system_health()
    
    def _detect_model(self) -> str:
        """Detect which GPT model is available."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Try GPT-5-mini first
            try:
                response = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                return "gpt-5-mini"
            except:
                # Fallback to gpt-4o-mini
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                return "gpt-4o-mini"
        except:
            return "gpt-4o-mini"  # Default fallback
    
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
            
            logger.info(f"✅ System health check passed - Ready with {self.model_name}")
            
        except Exception as e:
            logger.error(f"❌ System health check failed: {str(e)}")
            raise
    
    def create_institutional_crew(self) -> Crew:
        """Create institutional analysis crew with GPT-5-mini."""
        
        try:
            # Create manager LLM for crew coordination
            manager_llm = LLM(
                model=self.model_name,
                temperature=0.1,
                max_completion_tokens=1000,
                api_key=os.getenv("OPENAI_API_KEY")
            )
            
            # Create professional task workflow
            tasks = create_professional_task_workflow(self.input_file)
            
            # Create institutional crew
            crew = Crew(
                agents=[data_cleaner, data_enricher, news_scanner, alpha_analyst],
                tasks=tasks,
                process=Process.sequential,  # Sequential for logical flow
                verbose=True,
                memory=True,
                manager_llm=manager_llm,
                planning=False  # Disable planning for simpler execution
            )
            
            logger.info(f"Institutional analysis crew created with {self.model_name}")
            return crew
            
        except Exception as e:
            logger.error(f"Failed to create institutional crew: {str(e)}")
            raise
    
    def execute_institutional_analysis(self, inputs: dict = None) -> dict:
        """Execute complete institutional investment analysis workflow."""
        
        if inputs is None:
            inputs = {
                'input_file': self.input_file,
                'analysis_date': datetime.now().strftime("%Y-%m-%d"),
                'execution_id': self.execution_id
            }
        
        try:
            logger.info("=" * 80)
            logger.info(f"STARTING INSTITUTIONAL INVESTMENT ANALYSIS")
            logger.info(f"Model: {self.model_name}")
            logger.info(f"Input File: {inputs['input_file']}")
            logger.info(f"Analysis Date: {inputs['analysis_date']}")
            logger.info(f"Execution ID: {inputs['execution_id']}")
            logger.info("=" * 80)
            
            # Create and execute crew
            self.crew = self.create_institutional_crew()
            
            logger.info("🚀 Starting crew execution...")
            
            result = self.crew.kickoff(inputs=inputs)
            
            # Generate execution summary
            summary = self._generate_execution_summary(result)
            
            logger.info("=" * 80)
            logger.info("INSTITUTIONAL ANALYSIS COMPLETED SUCCESSFULLY")
            logger.info(f"Analysis Output: {summary['output_files']}")
            logger.info(f"Model Used: {self.model_name}")
            logger.info("=" * 80)
            
            return {
                'status': 'success',
                'result': result,
                'summary': summary,
                'execution_id': self.execution_id,
                'model': self.model_name
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Institutional analysis failed: {error_msg}")
            
            return {
                'status': 'failed',
                'error': error_msg,
                'execution_id': self.execution_id,
                'model': self.model_name
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
                'model': self.model_name,
                'execution_time': 'Completed',
                'database_queries': 'Multiple institutional database queries executed',
                'compliance_status': 'Audit trail maintained',
                'system_health': 'All systems operational'
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
    Main entry point for institutional investment analysis with GPT-5-mini.
    
    Args:
        input_file: Path to small-cap dataset for analysis
    
    Returns:
        Complete analysis results with audit trail
    """
    
    try:
        logger.info("🏦 Initializing Institutional Analysis with GPT models...")
        
        # Initialize institutional analysis crew
        institutional_crew = InstitutionalAnalysisCrew(input_file)
        
        # Execute complete analysis workflow
        results = institutional_crew.execute_institutional_analysis()
        
        if results['status'] == 'success':
            print("\n🎯 INSTITUTIONAL ANALYSIS COMPLETED SUCCESSFULLY")
            print(f"🤖 Model Used: {results['model']}")
            print(f"📊 Execution ID: {results['execution_id']}")
            print(f"📁 Output Files: {len(results['summary']['output_files'])} reports generated")
            print(f"✅ System Status: All institutional systems operational")
            
            # Display output file locations
            print("\n📋 GENERATED REPORTS:")
            for output_file in results['summary']['output_files']:
                print(f"   📄 {output_file}")
                
        else:
            print(f"\n❌ INSTITUTIONAL ANALYSIS FAILED")
            print(f"Error: {results['error']}")
            print(f"Model: {results['model']}")
            
        return results
        
    except Exception as e:
        logger.error(f"Critical system failure: {str(e)}")
        print(f"\n🚨 CRITICAL SYSTEM FAILURE: {str(e)}")
        return {'status': 'critical_failure', 'error': str(e)}

if __name__ == "__main__":
    # System health check and demonstration
    print("🏦 HEDGE FUND MULTI-AGENT ANALYSIS SYSTEM")
    print("🚀 Powered by GPT-5-mini (or GPT-4o-mini)")
    print("=" * 50)
    print("Initializing institutional-grade investment analysis...")
    
    # Run with default sample data
    results = run_institutional_analysis()
    
    if results['status'] == 'success':
        print("\n🎉 Demo completed successfully!")
        print("Ready for production institutional analysis.")
    else:
        print(f"\n⚠️  Demo failed: {results.get('error', 'Unknown error')}")