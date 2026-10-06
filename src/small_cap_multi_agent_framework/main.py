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
        self.version = "2.1.0"
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        logger.info(f"Small Cap Multi-Agent Framework v{self.version} initialized")
        logger.info(f"Using model: {self.model}")
    
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
            
            print(f"   🤖 Model: {self.model}")
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
    
    def run_analysis(self, input_file: str = None, tickers: list = None, verbose: bool = True) -> dict:
        """Execute complete institutional analysis workflow.

        Pass `tickers` for an ad-hoc lookup on specific tickers (bypasses the
        CSV entirely), or `input_file` for a batch CSV run. Defaults to the
        sample CSV if neither is given.
        """

        if verbose:
            self.display_system_banner()

        # Environment validation
        if not self.validate_environment():
            return {'status': 'failed', 'error': 'Environment validation failed'}

        if tickers:
            print(f"🎯 TICKERS: {', '.join(tickers)}")
            print()
        else:
            if input_file is None:
                input_file = "data/small_caps_input.csv"

            if not Path(input_file).exists():
                error_msg = f"Input file not found: {input_file}"
                print(f"❌ {error_msg}")
                return {'status': 'failed', 'error': error_msg}

            print(f"📁 INPUT FILE: {input_file}")

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
            results = run_institutional_analysis(input_file=input_file, tickers=tickers)

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
        summary = results.get('summary', {})
        grounding_passed = summary.get('grounding_passed', True)
        thesis_passed = summary.get('thesis_passed', True)
        trajectory_passed = summary.get('trajectory_passed', True)

        print("=" * 80)
        if grounding_passed and thesis_passed and trajectory_passed:
            print("🎯 INSTITUTIONAL ANALYSIS COMPLETED - ALL QUALITY CHECKS PASSED")
        else:
            print("⚠️  ANALYSIS COMPLETED BUT A QUALITY CHECK FAILED EVEN AFTER RETRY - REVIEW BEFORE TRUSTING")
        print("=" * 80)

        print(f"🤖 Model Used: {results.get('model', self.model)}")
        print(f"📊 Analysis Date: {summary.get('analysis_date', 'N/A')}")
        print(f"🆔 Execution ID: {summary.get('execution_id', 'N/A')}")
        print(f"⚡ Processing: {summary.get('agent_count', 4)} agents, {summary.get('task_count', 4)} tasks")
        print(f"📁 Output Files: {len(summary.get('output_files', []))} reports generated")

        if 'ticker_grounding_rate' in summary:
            print(f"✅ Ticker grounding: {summary['ticker_grounding_rate'] * 100:.0f}%")
            print(f"✅ Numeric grounding: {summary['numeric_grounding_rate'] * 100:.0f}%"
                  f"{' (after 1 retry)' if summary.get('grounding_retried') else ''}")
            if summary.get('ungrounded_tickers'):
                print(f"⚠️  Ungrounded tickers: {summary['ungrounded_tickers']}")
        if 'thesis_consistency_rate' in summary:
            print(f"✅ Thesis consistency: {summary['thesis_consistency_rate'] * 100:.0f}%")
            if summary.get('inconsistent_tickers'):
                print(f"⚠️  Calls that don't match their own fundamentals: {summary['inconsistent_tickers']}")
        if 'trajectory_severity' in summary:
            print(f"✅ Trajectory: {summary['trajectory_severity']} "
                  f"({summary.get('total_tool_calls_in_trajectory', 0)} tool calls)")
            if summary.get('repeated_call_tickers'):
                print(f"⚠️  Agent repeated/skipped a tool call for: {summary['repeated_call_tickers']}")
        print()

        print("📋 GENERATED REPORTS:")
        for output_file in summary.get('output_files', []):
            file_size = Path(output_file).stat().st_size if Path(output_file).exists() else 0
            print(f"   📄 {output_file} ({file_size:,} bytes)")

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
  python main.py --input data/custom_stocks.csv     # Run with custom dataset
  python main.py --tickers AAPL,TSLA,SMLR           # Analyze specific tickers directly
  python main.py --quiet                            # Run with minimal output
        """
    )

    parser.add_argument(
        '--input', '-i',
        type=str,
        default=None,
        help='Path to input CSV file containing small-cap stocks (default: data/small_caps_input.csv)'
    )

    parser.add_argument(
        '--tickers', '-t',
        type=str,
        default=None,
        help='Comma-separated tickers to analyze directly, e.g. AAPL,TSLA (bypasses --input)'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Run in quiet mode with minimal output'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Small Cap Multi-Agent Framework v2.1.0'
    )

    args = parser.parse_args()

    if args.tickers and args.input:
        parser.error("--input and --tickers are mutually exclusive")

    tickers = [t.strip().upper() for t in args.tickers.split(',') if t.strip()] if args.tickers else None

    # Initialize and run analysis system
    system = SmallCapAnalysisSystem()
    results = system.run_analysis(
        input_file=args.input,
        tickers=tickers,
        verbose=not args.quiet
    )
    
    # Exit with appropriate code
    exit_code = 0 if results['status'] == 'success' else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()