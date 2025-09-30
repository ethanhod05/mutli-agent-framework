"""
Hedge Fund Database System with Real Market Data Integration
===========================================================

Combines real-time market data from yfinance with local database fallback.
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
import yfinance as yf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HedgeFundDatabaseSystem:
    """
    Hybrid database system combining real market data with local storage.
    Primary: YFinance for real-time data
    Fallback: SQLite for offline/testing
    """
    
    def __init__(self, db_path: str = "data/hedge_fund_database.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._initialize_database()
        logger.info(f"Hedge Fund Database System initialized with YFinance integration")
    
    def _get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _initialize_database(self):
        """Create minimal database schema for fallback."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Simplified schema for fallback
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS securities (
                    ticker TEXT PRIMARY KEY,
                    company_name TEXT,
                    sector TEXT,
                    market_cap REAL,
                    exchange TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fundamentals (
                    ticker TEXT PRIMARY KEY,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    roe REAL,
                    debt_to_equity REAL,
                    current_ratio REAL,
                    gross_margin REAL,
                    operating_margin REAL,
                    net_margin REAL,
                    revenue_growth REAL,
                    earnings_growth REAL,
                    data_date DATE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    ticker TEXT PRIMARY KEY,
                    price REAL,
                    volume INTEGER,
                    day_change REAL,
                    week_change REAL,
                    month_change REAL,
                    year_change REAL,
                    beta REAL,
                    data_date DATE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT,
                    headline TEXT,
                    content TEXT,
                    source TEXT,
                    sentiment_score REAL,
                    publish_date DATE
                )
            """)
            
            conn.commit()
            logger.info("Database schema created successfully")
    
    def _populate_sample_data(self):
        """Add sample data if database is empty."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM securities")
            if cursor.fetchone()[0] == 0:
                # Add a few sample records
                sample_data = [
                    ('AAPL', 'Apple Inc', 'Technology', 3000000000000, 'NASDAQ'),
                    ('MSFT', 'Microsoft Corp', 'Technology', 2800000000000, 'NASDAQ'),
                ]
                cursor.executemany(
                    "INSERT OR IGNORE INTO securities VALUES (?, ?, ?, ?, ?)",
                    sample_data
                )
                conn.commit()

# Initialize global database system
hedge_fund_db = HedgeFundDatabaseSystem()

@tool
def query_institutional_database(ticker: str, query_type: str = "fundamental") -> str:
    """
    Access institutional-grade financial database with real-time data.
    
    Available query types:
    - fundamental: Complete financial metrics and ratios
    - market: Price, volume, and market data
    - news: Recent news and sentiment analysis
    """
    try:
        ticker = ticker.upper().strip()
        logger.info(f"Querying {query_type} data for {ticker}")
        
        # ALWAYS try YFinance first for real data
        try:
            stock = yf.Ticker(ticker)
            
            if query_type == "fundamental":
                return _get_yfinance_fundamentals(stock, ticker)
            elif query_type == "news":
                return _get_yfinance_news(stock, ticker)
            elif query_type == "market":
                return _get_yfinance_market(stock, ticker)
            else:
                return f"Unknown query type: {query_type}"
                
        except Exception as yf_error:
            logger.warning(f"YFinance failed for {ticker}: {yf_error}")
            # Fallback to local database
            return _get_local_data(ticker, query_type)
            
    except Exception as e:
        logger.error(f"Database query failed for {ticker}: {str(e)}")
        return f"Error fetching data for {ticker}: {str(e)}"

def _get_yfinance_fundamentals(stock, ticker: str) -> str:
    """Get fundamental data from YFinance."""
    try:
        info = stock.info
        
        # Check if we got valid data
        if not info or 'symbol' not in info:
            return f"No fundamental data available for {ticker}"
        
        # Extract key metrics with defaults
        company_name = info.get('longName', ticker)
        sector = info.get('sector', 'Unknown')
        market_cap = info.get('marketCap', 0)
        
        # Valuation metrics
        pe_ratio = info.get('trailingPE', 0)
        forward_pe = info.get('forwardPE', 0)
        pb_ratio = info.get('priceToBook', 0)
        ps_ratio = info.get('priceToSalesTrailing12Months', 0)
        peg_ratio = info.get('pegRatio', 0)
        
        # Profitability metrics
        profit_margins = info.get('profitMargins', 0)
        gross_margins = info.get('grossMargins', 0)
        operating_margins = info.get('operatingMargins', 0)
        roe = info.get('returnOnEquity', 0)
        roa = info.get('returnOnAssets', 0)
        
        # Growth metrics
        revenue_growth = info.get('revenueGrowth', 0)
        earnings_growth = info.get('earningsGrowth', 0)
        
        # Financial health
        current_ratio = info.get('currentRatio', 0)
        debt_to_equity = info.get('debtToEquity', 0)
        total_cash = info.get('totalCash', 0)
        total_debt = info.get('totalDebt', 0)
        free_cash_flow = info.get('freeCashflow', 0)
        
        # Price info
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        target_price = info.get('targetMeanPrice', 0)
        
        return f"""
═══════════════════════════════════════════════════════════════
FUNDAMENTAL ANALYSIS - {ticker} (REAL-TIME DATA)
Data Source: Yahoo Finance | {datetime.now().strftime('%Y-%m-%d %H:%M')}
═══════════════════════════════════════════════════════════════

COMPANY PROFILE:
Company: {company_name}
Sector: {sector}
Market Cap: ${market_cap:,.0f}

VALUATION METRICS:
P/E Ratio (TTM): {pe_ratio:.2f}
Forward P/E: {forward_pe:.2f}
P/B Ratio: {pb_ratio:.2f}
P/S Ratio: {ps_ratio:.2f}
PEG Ratio: {peg_ratio:.2f}

PROFITABILITY:
Gross Margins: {gross_margins*100:.1f}%
Operating Margins: {operating_margins*100:.1f}%
Net Margins: {profit_margins*100:.1f}%
ROE: {roe*100:.1f}%
ROA: {roa*100:.1f}%

GROWTH:
Revenue Growth: {revenue_growth*100:.1f}%
Earnings Growth: {earnings_growth*100:.1f}%

FINANCIAL HEALTH:
Current Ratio: {current_ratio:.2f}
Debt/Equity: {debt_to_equity:.2f}
Total Cash: ${total_cash:,.0f}
Total Debt: ${total_debt:,.0f}
Free Cash Flow: ${free_cash_flow:,.0f}

PRICE TARGETS:
Current Price: ${current_price:.2f}
Analyst Target: ${target_price:.2f}
Upside Potential: {((target_price/current_price - 1)*100 if current_price > 0 else 0):.1f}%
"""
    except Exception as e:
        logger.error(f"Error processing fundamentals for {ticker}: {e}")
        return f"Limited fundamental data available for {ticker}"

def _get_yfinance_news(stock, ticker: str) -> str:
    """Get news data from YFinance."""
    try:
        news = stock.news
        
        if not news:
            return f"No recent news available for {ticker}"
        
        news_output = f"""
═══════════════════════════════════════════════════════════════
NEWS & SENTIMENT - {ticker} (REAL-TIME)
Data Source: Yahoo Finance | {datetime.now().strftime('%Y-%m-%d %H:%M')}
═══════════════════════════════════════════════════════════════

RECENT NEWS:
"""
        
        for i, item in enumerate(news[:5], 1):
            title = item.get('title', 'No title')
            publisher = item.get('publisher', 'Unknown')
            link = item.get('link', '')
            
            # Simple sentiment based on keywords
            sentiment = "Neutral"
            positive_words = ['beat', 'exceed', 'upgrade', 'growth', 'profit', 'gain']
            negative_words = ['miss', 'downgrade', 'loss', 'decline', 'cut', 'weak']
            
            title_lower = title.lower()
            if any(word in title_lower for word in positive_words):
                sentiment = "Positive 📈"
            elif any(word in title_lower for word in negative_words):
                sentiment = "Negative 📉"
            
            news_output += f"""
{i}. {title}
   Publisher: {publisher}
   Sentiment: {sentiment}
   Link: {link[:50]}...
"""
        
        return news_output
        
    except Exception as e:
        logger.error(f"Error getting news for {ticker}: {e}")
        return f"No recent news available for {ticker}"

def _get_yfinance_market(stock, ticker: str) -> str:
    """Get market data from YFinance."""
    try:
        info = stock.info
        history = stock.history(period="1mo")
        
        if history.empty:
            return f"No market data available for {ticker}"
        
        current_price = history['Close'].iloc[-1]
        volume = history['Volume'].iloc[-1]
        
        # Calculate changes
        week_ago = history['Close'].iloc[-5] if len(history) >= 5 else history['Close'].iloc[0]
        month_ago = history['Close'].iloc[0]
        
        week_change = ((current_price - week_ago) / week_ago * 100) if week_ago > 0 else 0
        month_change = ((current_price - month_ago) / month_ago * 100) if month_ago > 0 else 0
        
        # Get additional info
        beta = info.get('beta', 0)
        avg_volume = info.get('averageVolume', 0)
        fifty_two_high = info.get('fiftyTwoWeekHigh', 0)
        fifty_two_low = info.get('fiftyTwoWeekLow', 0)
        
        return f"""
═══════════════════════════════════════════════════════════════
MARKET DATA - {ticker} (REAL-TIME)
Data Source: Yahoo Finance | {datetime.now().strftime('%Y-%m-%d %H:%M')}
═══════════════════════════════════════════════════════════════

PRICE INFORMATION:
Current Price: ${current_price:.2f}
Week Change: {week_change:.2f}%
Month Change: {month_change:.2f}%
52-Week High: ${fifty_two_high:.2f}
52-Week Low: ${fifty_two_low:.2f}

VOLUME:
Today's Volume: {volume:,.0f}
Average Volume: {avg_volume:,.0f}
Volume vs Avg: {(volume/avg_volume*100 if avg_volume > 0 else 0):.0f}%

RISK METRICS:
Beta: {beta:.2f}
Volatility: {history['Close'].pct_change().std() * 100:.1f}% (30-day)
"""
        
    except Exception as e:
        logger.error(f"Error getting market data for {ticker}: {e}")
        return f"Limited market data available for {ticker}"

def _get_local_data(ticker: str, query_type: str) -> str:
    """Fallback to local database if YFinance fails."""
    try:
        conn = hedge_fund_db._get_connection()
        cursor = conn.cursor()
        
        if query_type == "fundamental":
            cursor.execute("SELECT * FROM fundamentals WHERE ticker = ?", (ticker,))
            result = cursor.fetchone()
            if result:
                return f"Fallback data for {ticker}: Limited fundamental data available"
        
        return f"No local data available for {ticker}"
        
    except Exception as e:
        logger.error(f"Local database query failed: {e}")
        return f"No data available for {ticker}"
    finally:
        conn.close()

# Create tool instance for export
query_institutional_database_tool = query_institutional_database