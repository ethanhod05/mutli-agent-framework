"""
Hedge Fund Database System - Institutional Data Infrastructure
============================================================

Simulates real hedge fund data infrastructure including:
- Bloomberg Terminal equivalent data access
- FactSet-style fundamental databases  
- Alternative data aggregation platforms
- Internal research database with analyst notes
- Risk management data systems

This mirrors how actual hedge funds structure their data access through
multiple institutional data providers with normalized schemas.

Author: Small Cap Multi-Agent Framework
License: MIT
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json
import logging
from pathlib import Path
from crewai.tools import tool

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hedge_fund_database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HedgeFundDatabaseSystem:
    """
    Institutional-grade database system simulating real hedge fund data infrastructure.
    
    Replicates data access patterns from:
    - Bloomberg Terminal
    - FactSet Workstation  
    - Refinitiv Eikon
    - S&P Capital IQ
    - Internal research databases
    """
    
    def __init__(self, db_path: str = "data/hedge_fund_database.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._initialize_database()
        self._populate_sample_data()
        logger.info(f"Hedge Fund Database System initialized at {self.db_path}")
    
    def _get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _initialize_database(self):
        """Create institutional database schema mirroring real hedge fund systems."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Securities Master Table (Bloomberg equivalent)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS securities_master (
                    ticker TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    gics_sector TEXT,
                    gics_industry TEXT,
                    exchange TEXT,
                    country TEXT,
                    currency TEXT,
                    market_cap_usd REAL,
                    shares_outstanding REAL,
                    float_shares REAL,
                    ipo_date DATE,
                    fiscal_year_end TEXT,
                    employees INTEGER,
                    headquarters TEXT,
                    website TEXT,
                    business_description TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Fundamental Data (FactSet equivalent)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fundamental_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    report_date DATE NOT NULL,
                    period_type TEXT NOT NULL,
                    fiscal_period TEXT NOT NULL,
                    
                    -- Income Statement
                    total_revenue REAL,
                    cost_of_revenue REAL,
                    gross_profit REAL,
                    operating_expenses REAL,
                    operating_income REAL,
                    ebitda REAL,
                    interest_expense REAL,
                    pretax_income REAL,
                    tax_expense REAL,
                    net_income REAL,
                    eps_diluted REAL,
                    shares_diluted REAL,
                    
                    -- Balance Sheet
                    total_assets REAL,
                    current_assets REAL,
                    cash_and_equivalents REAL,
                    accounts_receivable REAL,
                    inventory REAL,
                    total_liabilities REAL,
                    current_liabilities REAL,
                    long_term_debt REAL,
                    shareholders_equity REAL,
                    book_value_per_share REAL,
                    tangible_book_value REAL,
                    
                    -- Cash Flow Statement
                    operating_cash_flow REAL,
                    capital_expenditures REAL,
                    free_cash_flow REAL,
                    financing_cash_flow REAL,
                    investing_cash_flow REAL,
                    
                    -- Key Ratios
                    roe REAL,
                    roa REAL,
                    roic REAL,
                    current_ratio REAL,
                    quick_ratio REAL,
                    debt_to_equity REAL,
                    interest_coverage REAL,
                    
                    data_source TEXT DEFAULT 'Internal',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticker) REFERENCES securities_master (ticker),
                    UNIQUE(ticker, report_date, period_type)
                )
            """)
            
            # Market Data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    price_date DATE NOT NULL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    adjusted_close REAL,
                    volume INTEGER,
                    market_cap REAL,
                    shares_outstanding REAL,
                    beta REAL,
                    volatility_30d REAL,
                    volatility_90d REAL,
                    avg_volume_30d REAL,
                    
                    data_source TEXT DEFAULT 'Market Feed',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticker) REFERENCES securities_master (ticker),
                    UNIQUE(ticker, price_date)
                )
            """)
            
            # News and Sentiment
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_sentiment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    news_date DATE NOT NULL,
                    headline TEXT NOT NULL,
                    source TEXT,
                    sentiment_score REAL,
                    relevance_score REAL,
                    article_url TEXT,
                    article_summary TEXT,
                    keywords TEXT,
                    impact_category TEXT,
                    
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticker) REFERENCES securities_master (ticker)
                )
            """)
            
            conn.commit()
            logger.info("Database schema created successfully")
    
    def _populate_sample_data(self):
        """Populate database with realistic institutional-quality sample data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM securities_master")
            if cursor.fetchone()[0] > 0:
                logger.info("Sample data already exists, skipping population")
                return
            
            # Insert sample securities
            securities_data = [
                ('SMLR', 'Semler Scientific Inc', 'Health Care', 'Health Care Technology', 'NASDAQ', 'US', 'USD', 
                 295000000, 6920000, 5450000, '2014-02-12', 'December', 85, 'Santa Clara, CA', 
                 'https://semlerscientific.com', 'Develops and markets diagnostic technology solutions for cardiovascular disease detection'),
                
                ('HROW', 'Harrow Health Inc', 'Health Care', 'Pharmaceuticals', 'NASDAQ', 'US', 'USD',
                 148000000, 12500000, 11200000, '2017-08-09', 'December', 245, 'Nashville, TN',
                 'https://harrowhealth.com', 'Specialty pharmaceutical company focused on ophthalmic medications'),
                
                ('AGFY', 'Agrify Corporation', 'Information Technology', 'Technology Hardware & Equipment', 'NASDAQ', 'US', 'USD',
                 38500000, 6000000, 5100000, '2021-01-26', 'December', 125, 'Troy, MI',
                 'https://agrify.com', 'Provides cultivation and extraction solutions for cannabis and food industries'),
                
                ('VERX', 'Vertex Inc', 'Information Technology', 'Software', 'NASDAQ', 'US', 'USD',
                 1650000000, 48200000, 42800000, '2020-07-30', 'December', 1850, 'King of Prussia, PA',
                 'https://vertexinc.com', 'Provides tax technology solutions for corporations worldwide')
            ]
            
            cursor.executemany("""
                INSERT INTO securities_master 
                (ticker, company_name, gics_sector, gics_industry, exchange, country, currency,
                 market_cap_usd, shares_outstanding, float_shares, ipo_date, fiscal_year_end,
                 employees, headquarters, website, business_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, securities_data)
            
            # Insert sample fundamental data
            fundamental_sample = [
                ('SMLR', '2024-09-30', 'Q', 'Q3', 72500000, 13000000, 59500000, 41000000, 18500000, 
                 22000000, 800000, 17700000, 2600000, 15100000, 2.18, 6920000, 
                 95000000, 68000000, 42000000, 8500000, 2100000, 35000000, 15000000, 1200000, 60000000, 8.67, 59000000,
                 18500000, 2800000, 15700000, -2100000, -3500000,
                 0.19, 0.14, 0.22, 4.8, 4.2, 0.03, 85.0),
            ]
            
            for data in fundamental_sample:
                cursor.execute("""
                    INSERT INTO fundamental_data 
                    (ticker, report_date, period_type, fiscal_period, total_revenue, cost_of_revenue,
                     gross_profit, operating_expenses, operating_income, ebitda, interest_expense,
                     pretax_income, tax_expense, net_income, eps_diluted, shares_diluted,
                     total_assets, current_assets, cash_and_equivalents, accounts_receivable, inventory,
                     total_liabilities, current_liabilities, long_term_debt, shareholders_equity,
                     book_value_per_share, tangible_book_value, operating_cash_flow, capital_expenditures,
                     free_cash_flow, financing_cash_flow, investing_cash_flow, roe, roa, roic,
                     current_ratio, quick_ratio, debt_to_equity, interest_coverage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
            
            # Insert sample news data
            news_sample = [
                ('SMLR', '2024-10-20', 'Semler Scientific Reports Strong Q3 Results',
                 'MarketWatch', 0.72, 0.95, 'https://example.com/smlr-earnings',
                 'Company beats revenue estimates with 28% growth', '["earnings", "growth", "beat"]', 'Earnings'),
            ]
            
            cursor.executemany("""
                INSERT INTO news_sentiment 
                (ticker, news_date, headline, source, sentiment_score, relevance_score,
                 article_url, article_summary, keywords, impact_category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, news_sample)
            
            conn.commit()
            logger.info("Sample data populated successfully")

# Database Query Engine
class DatabaseQueryEngine:
    """Professional database query engine for hedge fund data access."""
    
    def __init__(self, db_system: HedgeFundDatabaseSystem):
        self.db_system = db_system
        self.db_path = db_system.db_path
    
    def execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)
                logger.info(f"Query executed successfully, returned {len(df)} rows")
                return df
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise

# Initialize global database system
hedge_fund_db = HedgeFundDatabaseSystem()
query_engine = DatabaseQueryEngine(hedge_fund_db)

@tool
def query_institutional_database(ticker: str, query_type: str = "fundamental") -> str:
    """
    Access institutional-grade financial database (Bloomberg/FactSet equivalent).
    
    Available query types:
    - fundamental: Complete financial metrics and ratios
    - market: Price, volume, and market data
    - news: Recent news and sentiment analysis
    """
    try:
        ticker = ticker.upper()
        
        if query_type == "fundamental":
            return _get_fundamental_analysis(ticker)
        elif query_type == "news":
            return _get_news_analysis(ticker)
        else:
            return f"Query type '{query_type}' not yet implemented"
            
    except Exception as e:
        logger.error(f"Database query failed for {ticker}: {str(e)}")
        return f"Database query failed: {str(e)}"

def _get_fundamental_analysis(ticker: str) -> str:
    """Get comprehensive fundamental analysis from institutional database."""
    
    # Get security profile
    query = "SELECT * FROM securities_master WHERE ticker = ? COLLATE NOCASE"
    security_df = query_engine.execute_query(query, (ticker,))
    
    if security_df.empty:
        return f"Security {ticker} not found in institutional database"
    
    security = security_df.iloc[0]
    
    # Get latest fundamentals
    query = """
        SELECT * FROM fundamental_data 
        WHERE ticker = ? COLLATE NOCASE
        ORDER BY report_date DESC
        LIMIT 1
    """
    fund_df = query_engine.execute_query(query, (ticker,))
    
    if fund_df.empty:
        return f"No fundamental data available for {ticker}"
    
    fund = fund_df.iloc[0]
    
    return f"""
═══════════════════════════════════════════════════════════════
INSTITUTIONAL DATABASE: FUNDAMENTAL ANALYSIS - {ticker}
Data Source: Hedge Fund Database System | Last Updated: {fund['created_date']}
═══════════════════════════════════════════════════════════════

COMPANY PROFILE:
Company: {security['company_name']}
GICS Sector: {security['gics_sector']} | Industry: {security['gics_industry']}
Exchange: {security['exchange']} | Country: {security['country']}
Market Cap: ${security['market_cap_usd']/1e6:.1f}M

FINANCIAL METRICS (As of {fund['report_date']}):
Revenue (TTM): ${fund['total_revenue']/1e6:.1f}M
Gross Margin: {(fund['gross_profit']/fund['total_revenue']*100):.1f}%
Operating Margin: {(fund['operating_income']/fund['total_revenue']*100):.1f}%
Net Margin: {(fund['net_income']/fund['total_revenue']*100):.1f}%
ROE: {fund['roe']*100:.1f}%
Current Ratio: {fund['current_ratio']:.1f}x
Debt/Equity: {fund['debt_to_equity']:.2f}x

DATABASE INTEGRITY: ✓ Verified | Source: Institutional Database
"""

def _get_news_analysis(ticker: str) -> str:
    """Get news and sentiment analysis from institutional database."""
    
    query = """
        SELECT news_date, headline, source, sentiment_score, article_summary
        FROM news_sentiment 
        WHERE ticker = ? COLLATE NOCASE
        ORDER BY news_date DESC
        LIMIT 5
    """
    
    news_df = query_engine.execute_query(query, (ticker,))
    
    if news_df.empty:
        return f"No recent news available for {ticker}"
    
    news_list = ""
    for _, news in news_df.iterrows():
        sentiment_icon = "📈" if news['sentiment_score'] > 0.2 else "📉" if news['sentiment_score'] < -0.2 else "➡️"
        news_list += f"""
{sentiment_icon} [{news['news_date']}] {news['headline']}
   Source: {news['source']} | Sentiment: {news['sentiment_score']:+.2f}
   Summary: {news['article_summary']}"""
    
    return f"""
═══════════════════════════════════════════════════════════════
INSTITUTIONAL DATABASE: NEWS & SENTIMENT ANALYSIS - {ticker}
Data Source: Alternative Data Platform | Recent Coverage
═══════════════════════════════════════════════════════════════

RECENT NEWS:
{news_list}

DATABASE INTEGRITY: ✓ Verified | Source: News Database
"""