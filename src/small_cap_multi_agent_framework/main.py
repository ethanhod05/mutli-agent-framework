"""
Small Cap Multi-Agent Framework - Main Execution Script
======================================================

Professional entry point for institutional-grade small-cap investment analysis
using GPT-5-mini powered agents.

Author: Small Cap Multi-Agent Framework
License: MIT
"""

import argparse
import sys
from pathlib import Path
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from small_cap_multi_agent_framework.crew import run_institutional_analysis
from small_cap_multi_agent_framework.tools.hedge_fund_database import hedge_fund_db
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('small_cap_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SmallCapAnalysisSystem:
    """
    Main system orchestrator for institutional small-cap investment analysis.
    
    Provides complete workflow management from data validation through
    final investment recommendations with audit trail and compliance.
    """
    
    def __init__(self):
        self.system_start_time = datetime.now()
        self.version = "2.0.0"  # Updated for GPT-5-mini
        self.model = self._detect_model()
        logger.info(f"Small Cap Multi-Agent Framework v{self.version} initialized")
        logger.info(f"Using model: {self.model}")
    
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
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=1
                    )
                    return "gpt-4o-mini"
                except:
                    return "Model detection failed"
        except:
            return "OpenAI API not configured"
    
    def validate_environment(self) -> bool:
        """Validate system environment and dependencies."""
        try:
            print("🔍 VALIDATING SYSTEM ENVIRONMENT...")
            
            # Check API key
            if not os.getenv("OPENAI_API_KEY"):
                print("   ❌ OPENAI_API_KEY not found in .env file")
                print("   Please add: OPENAI_API_KEY=sk-your-key-here")
                return False
            print("   ✅ OpenAI API key found")
            
            # Check required directories
            required_dirs = ['data', 'output', 'scripts']
            for dir_name in required_dirs:
                if not Path(dir_name).exists():
                    Path(dir_name).mkdir(exist_ok=True)
                    print(f"   ✅ Created directory: {dir_name}/")
                else:
                    print(f"   ✅ Directory exists: {dir_name}/")
            
            # Check database system
            print("   🗄️  Testing hedge fund database connection...")
            try:
                test_conn = hedge_fund_db._get_connection()
                test_conn.close()
                print("   ✅ Database system operational")
            except Exception as e:
                print(f"   ⚠️  Database warning: {str(e)}")
                print("   Analysis will continue without database tools")
            
            # Check sample data availability
            sample_files = list(Path('data').glob('*.csv'))
            if sample_files:
                print(f"   ✅ Found {len(sample_files)} data files")
            else:
                print("   ⚠️  No CSV files found in data/ directory")
                self.create_sample_data()
            
            # Check model availability
            print(f"   🤖 Model: {self.model}")
            if self.model == "gpt-5-mini":
                print("   ✅ Using latest GPT-5-mini model")
            elif self.model == "gpt-4o-mini":
                print("   ✅ Using GPT-4o-mini (GPT-5 not available yet)")
            else:
                print(f"   ⚠️  Model status: {self.model}")
            
            print("✅ ENVIRONMENT VALIDATION COMPLETED\n")
            return True
            
        except Exception as e:
            print(f"❌ ENVIRONMENT VALIDATION FAILED: {str(e)}")
            logger.error(f"Environment validation failed: {str(e)}")
            return False
    
    def create_sample_data(self):
        """Create sample dataset for demonstration."""
        print("   📊 Creating sample dataset...")
        
        sample_data = {
            'Ticker': ['SMLR', 'HROW', 'AGFY', 'VERX', 'MDXG'],
            'Company Name': [
                'Semler Scientific Inc',
                'Harrow Health Inc', 
                'Agrify Corporation',
                'Vertex Inc',
                'MiMedx Group Inc'
            ],
            'Sector': [
                'Health Care',
                'Health Care',
                'Information Technology', 
                'Information Technology',
                'Health Care'
            ],
            'Market Cap': [295000000, 148000000, 38500000, 1650000000, 245000000]
        }
        
        df = pd.DataFrame(sample_data)
        sample_file = Path('data/small_caps_input.csv')
        df.to_csv(sample_file, index=False)
        
        print(f"   ✅ Sample data created: {sample_file}")
    
    def display_system_banner(self):
        """Display professional system banner."""
        print("=" * 80)
        print("🏦 SMALL CAP MULTI-AGENT FRAMEWORK")
        print("   Institutional-Grade Investment Analysis System")
        print("=" * 80)
        print(f"Version: {self.version}")
        print(f"Model: {self.model}")
        print(f"Session: {self.system_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: Professional Hedge Fund Analysis")
        print("=" * 80)
        print()
    
    def run_analysis(self, input_file: str = None, verbose: bool = True) -> dict:
        """Execute complete institutional analysis workflow."""
        
        if verbose:
            self.display_system_banner()
        
        # Environment validation
        if not self.validate_environment():
            return {'status': 'failed', 'error': 'Environment validation failed'}
        
        # Determine input file
        if input_file is None:
            input_file = "data/small_caps_input.csv"
        
        if not Path(input_file).exists():
            error_msg = f"Input file not found: {input_file}"
            print(f"❌ {error_msg}")
            return {'status': 'failed', 'error': error_msg}
        
        print(f"📁 INPUT FILE: {input_file}")
        
        # Validate input data
        try:
            df = pd.read_csv(input_file)
            print(f"📊 DATASET: {len(df)} securities loaded for analysis")
            print(f"📋 COLUMNS: {list(df.columns)}")
            print()
        except Exception as e:
            error_msg = f"Failed to read input file: {str(e)}"
            print(f"❌ {error_msg}")
            return {'status': 'failed', 'error': error_msg}
        
        # Execute institutional analysis
        print("🚀 LAUNCHING INSTITUTIONAL ANALYSIS WORKFLOW...")
        print("   → Data Quality Assurance Agent")
        print("   → Fundamental Research Agent") 
        print("   → Market Intelligence Agent")
        print("   → Alpha Generation Agent")
        print()
        
        try:
            results = run_institutional_analysis(input_file)
            
            if results['status'] == 'success':
                self.display_success_summary(results)
            else:
                self.display_failure_summary(results)
            
            return results
            
        except Exception as e:
            error_msg = f"Analysis execution failed: {str(e)}"
            print(f"❌ CRITICAL FAILURE: {error_msg}")
            logger.error(error_msg)
            return {'status': 'failed', 'error': error_msg}
    
    def display_success_summary(self, results: dict):
        """Display professional success summary."""
        print("=" * 80)
        print("🎯 INSTITUTIONAL ANALYSIS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        summary = results.get('summary', {})
        
        print(f"🤖 Model Used: {results.get('model', self.model)}")
        print(f"📊 Analysis Date: {summary.get('analysis_date', 'N/A')}")
        print(f"🆔 Execution ID: {summary.get('execution_id', 'N/A')}")
        print(f"⚡ Processing: {summary.get('agent_count', 4)} agents, {summary.get('task_count', 4)} tasks")
        print(f"📁 Output Files: {len(summary.get('output_files', []))} reports generated")
        print()
        
        print("📋 GENERATED REPORTS:")
        for output_file in summary.get('output_files', []):
            file_size = Path(output_file).stat().st_size if Path(output_file).exists() else 0
            print(f"   📄 {output_file} ({file_size:,} bytes)")
        
        print()
        print("✅ SYSTEM STATUS: All institutional systems operational")
        print("🔒 COMPLIANCE: Audit trail maintained") 
        print("📈 READY: Investment recommendations available for review")
        print("=" * 80)
    
    def display_failure_summary(self, results: dict):
        """Display professional failure summary."""
        print("=" * 80)
        print("❌ INSTITUTIONAL ANALYSIS FAILED")
        print("=" * 80)
        print(f"Error: {results.get('error', 'Unknown error')}")
        print(f"Model: {results.get('model', self.model)}")
        print(f"Execution ID: {results.get('execution_id', 'N/A')}")
        print()
        print("🔧 TROUBLESHOOTING STEPS:")
        print("   1. Check your OpenAI API key is valid")
        print("   2. Verify you have credits in your OpenAI account")
        print("   3. Check system logs for detailed error information")
        print("   4. Validate input file format and content")
        print("=" * 80)

def main():
    """Main entry point with command-line interface."""
    
    parser = argparse.ArgumentParser(
        description="Small Cap Multi-Agent Framework - Institutional Investment Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Run with default sample data
  python main.py --input data/custom_stocks.csv    # Run with custom dataset
  python main.py --quiet                           # Run with minimal output
  
Powered by GPT-5-mini (or GPT-4o-mini fallback)
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        default=None,
        help='Path to input CSV file containing small-cap stocks (default: data/small_caps_input.csv)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Run in quiet mode with minimal output'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Small Cap Multi-Agent Framework v2.0.0 (GPT-5-mini)'
    )
    
    args = parser.parse_args()
    
    # Initialize and run analysis system
    system = SmallCapAnalysisSystem()
    results = system.run_analysis(
        input_file=args.input,
        verbose=not args.quiet
    )
    
    # Exit with appropriate code
    exit_code = 0 if results['status'] == 'success' else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()