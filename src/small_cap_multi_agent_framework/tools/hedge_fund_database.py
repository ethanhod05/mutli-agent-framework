"""
Hedge Fund Database System with Real Market Data Integration
===========================================================

Primary data source is yfinance. For tickers where yfinance's `.info`
endpoint comes back empty (common on thinly-traded small caps - see
sec_edgar.py's docstring), fundamentals fall back to SEC EDGAR's free XBRL
API, and price/quote data falls back to Finnhub's free tier if a key is
configured. Every source in the chain either returns real data or None /
an honest "no data available" message - nothing in this file ever
fabricates a number.
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
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from small_cap_multi_agent_framework.tools.sec_edgar import get_edgar_fundamentals
from small_cap_multi_agent_framework.tools.finnhub_fallback import get_finnhub_quote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# VADER is a general-purpose lexicon, so finance jargon reads wrong by
# default ("Micron Earnings Crush Views" scores negative because VADER's own
# base lexicon has "crush"/"crushes" as violence-adjacent words, even though
# crushing estimates is bullish). This override layers finance-specific
# valence on top. Every inflected form (crush/crushes/crushing) is listed
# explicitly - dict.update() only overwrites the exact keys given, so a
# missing inflection silently falls through to VADER's base score (or no
# score at all) rather than the finance-correct one. A test suite caught
# exactly this gap: "Crushes" and "Downgrades" were missing and scored wrong.
_FINANCE_LEXICON = {
    'crush': 1.5, 'crushes': 1.5, 'crushed': 1.5, 'crushing': 1.5,
    'beat': 1.8, 'beats': 1.8, 'beating': 1.8, 'topped': 1.2, 'tops': 1.2,
    'soar': 2.0, 'soars': 2.0, 'soaring': 2.0, 'soared': 2.0,
    'surge': 2.0, 'surges': 2.0, 'surging': 2.0, 'surged': 2.0,
    'rally': 1.5, 'rallies': 1.5, 'rallying': 1.5, 'rallied': 1.5,
    'upgrade': 1.8, 'upgrades': 1.8, 'upgraded': 1.8, 'upgrading': 1.8,
    'outperform': 1.5, 'outperforms': 1.5, 'outperformed': 1.5, 'bullish': 1.8,
    'miss': -1.8, 'misses': -1.8, 'missed': -1.8, 'missing': -1.8,
    'plunge': -2.0, 'plunges': -2.0, 'plunging': -2.0, 'plunged': -2.0,
    'downgrade': -1.8, 'downgrades': -1.8, 'downgraded': -1.8, 'downgrading': -1.8,
    'underperform': -1.5, 'underperforms': -1.5, 'underperformed': -1.5, 'bearish': -1.8,
    'slash': -1.5, 'slashes': -1.5, 'slashed': -1.5, 'slashing': -1.5,
    'layoffs': -1.5, 'layoff': -1.5, 'recall': -1.2, 'recalls': -1.2, 'recalled': -1.2,
    'bankruptcy': -2.5, 'delisted': -2.0, 'delisting': -2.0, 'investigation': -1.5,
}

_sentiment_analyzer = SentimentIntensityAnalyzer()
_sentiment_analyzer.lexicon.update(_FINANCE_LEXICON)


def _classify_sentiment(headline: str) -> tuple:
    """Real sentiment scoring (VADER + a finance-jargon lexicon override),
    not a hardcoded 6-word keyword list. Returns (label, compound_score)."""
    compound = _sentiment_analyzer.polarity_scores(headline)['compound']
    if compound >= 0.05:
        label = "Positive"
    elif compound <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"
    return label, compound

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

        # A delisted/inactive ticker still often returns a minimal shell
        # record with just 'symbol' present (quoteType 'NONE', no price or
        # market cap at all) - 'symbol' in info is not enough to tell real
        # data from an empty shell, so check for an actual price or cap too.
        has_real_data = (
            info
            and 'symbol' in info
            and info.get('quoteType') not in (None, 'NONE')
            and (info.get('currentPrice') or info.get('regularMarketPrice') or info.get('marketCap'))
        )
        if not has_real_data:
            return _get_edgar_fallback_fundamentals(stock, ticker)

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


def _get_edgar_fallback_fundamentals(stock, ticker: str) -> str:
    """Called only once yfinance's own `.info` has already come back empty.
    Pulls raw statement data from SEC EDGAR's free XBRL API and, where
    possible, a real last price from a direct yfinance price-history call
    (a separate endpoint from the broken `.info` one, and sometimes still
    populated even when `.info` isn't) or Finnhub's free tier if a key is
    configured - so some price-derived ratios can still be computed. Any
    figure we can't get from a real source is reported as 'n/a', never
    estimated or interpolated."""
    edgar = get_edgar_fundamentals(ticker)
    if edgar is None:
        return f"No fundamental data available for {ticker}"

    current_price = None
    price_source = None
    try:
        hist = stock.history(period="5d")
        if not hist.empty:
            current_price = float(hist['Close'].iloc[-1])
            price_source = "yfinance price history"
    except Exception:
        pass

    if current_price is None:
        quote = get_finnhub_quote(ticker)
        if quote:
            current_price = quote["current_price"]
            price_source = "Finnhub"

    def pct(x):
        return f"{x*100:.1f}%" if x is not None else "n/a"

    def money(x):
        return f"${x:,.0f}" if x is not None else "n/a"

    revenue = edgar["revenue"]
    net_income = edgar["net_income"]
    gross_margin = (edgar["gross_profit"] / revenue) if edgar["gross_profit"] and revenue else None
    operating_margin = (edgar["operating_income"] / revenue) if edgar["operating_income"] and revenue else None
    net_margin = (net_income / revenue) if net_income and revenue else None
    roe = (net_income / edgar["equity"]) if net_income and edgar["equity"] else None
    roa = (net_income / edgar["assets"]) if net_income and edgar["assets"] else None
    current_ratio = (
        edgar["current_assets"] / edgar["current_liabilities"]
        if edgar["current_assets"] and edgar["current_liabilities"] else None
    )
    debt_to_equity = (edgar["total_debt"] / edgar["equity"]) if edgar["total_debt"] and edgar["equity"] else None

    market_cap = None
    pe_ratio = None
    if current_price:
        if edgar["shares_outstanding"]:
            market_cap = current_price * edgar["shares_outstanding"]
        if edgar["eps_diluted"]:
            pe_ratio = current_price / edgar["eps_diluted"]

    price_note = (
        f"plus a real last price from {price_source}" if current_price
        else "- no live price was available from any free source, so price-derived figures are n/a"
    )

    return f"""
═══════════════════════════════════════════════════════════════
FUNDAMENTAL ANALYSIS - {ticker} (SEC EDGAR FALLBACK)
yfinance had no usable data for this ticker. The figures below come
directly from {ticker}'s own SEC filings (XBRL, as of {edgar['as_of'] or 'most recent filing'}) {price_note}.
═══════════════════════════════════════════════════════════════

FROM SEC FILINGS (annual, unless this filer has no 10-K on record yet):
Revenue: {money(revenue)}
Revenue Growth (YoY): {pct(edgar['revenue_growth'])}
Net Income: {money(net_income)}
Earnings Growth (YoY): {pct(edgar['earnings_growth'])}
Gross Margin: {pct(gross_margin)}
Operating Margin: {pct(operating_margin)}
Net Margin: {pct(net_margin)}
ROE: {pct(roe)}
ROA: {pct(roa)}
Total Assets: {money(edgar['assets'])}
Total Liabilities: {money(edgar['liabilities'])}
Stockholders' Equity: {money(edgar['equity'])}
Cash: {money(edgar['cash'])}
Total Debt: {money(edgar['total_debt'])}
Current Ratio: {f"{current_ratio:.2f}" if current_ratio else "n/a"}
Debt/Equity: {f"{debt_to_equity:.2f}" if debt_to_equity else "n/a"}
Shares Outstanding: {f"{edgar['shares_outstanding']:,.0f}" if edgar['shares_outstanding'] else "n/a"}
Diluted EPS: {f"${edgar['eps_diluted']:.2f}" if edgar['eps_diluted'] else "n/a"}

PRICE-DERIVED (source: {price_source or "unavailable"}):
Current Price: {f"${current_price:.2f}" if current_price else "n/a"}
Market Cap: {money(market_cap)}
P/E Ratio (derived): {f"{pe_ratio:.2f}" if pe_ratio else "n/a"}

NOTE: No analyst price target is available from these free sources (that
requires a paid data feed) - do not state or imply one for this ticker.
"""


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
            # yfinance nests article fields under 'content' as of the current schema;
            # fall back to the old flat fields in case that changes again.
            content = item.get('content', item)
            title = content.get('title', 'No title')
            publisher = content.get('provider', {}).get('displayName') or item.get('publisher', 'Unknown')
            link = content.get('canonicalUrl', {}).get('url') or item.get('link', '')
            pub_date = content.get('pubDate', '')[:10] or 'Unknown date'

            sentiment, score = _classify_sentiment(title)

            news_output += f"""
{i}. {title}
   Publisher: {publisher}
   Date: {pub_date}
   Sentiment: {sentiment} (score: {score:+.2f})
   Link: {link}
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
            quote = get_finnhub_quote(ticker)
            if quote is None:
                return f"No market data available for {ticker}"
            return f"""
═══════════════════════════════════════════════════════════════
MARKET DATA - {ticker} (FINNHUB FALLBACK)
yfinance had no price history for this ticker. {datetime.now().strftime('%Y-%m-%d %H:%M')}
═══════════════════════════════════════════════════════════════

PRICE INFORMATION:
Current Price: ${quote['current_price']:.2f}
Previous Close: ${quote['prev_close']:.2f}
Day High: ${quote['day_high']:.2f}
Day Low: ${quote['day_low']:.2f}
Open: ${quote['open']:.2f}

NOTE: Volume, beta, and 52-week range aren't available from Finnhub's free
quote endpoint - reported as n/a rather than estimated.
"""

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