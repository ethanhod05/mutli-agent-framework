"""
Real Market Data Tool using yfinance
====================================

Provides real-time market data from Yahoo Finance for the multi-agent framework.
Free to use with no API limits.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YFinanceMarketData:
    """Real market data from Yahoo Finance"""
    
    def __init__(self):
        logger.info("YFinance Market Data Tool initialized")
    
    def query_institutional_database(self, ticker: str, query_type: str):
        """
        Main query function that matches your existing interface.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            query_type: 'fundamental', 'news', or 'market'
        """
        try:
            ticker = ticker.upper().strip()
            stock = yf.Ticker(ticker)
            
            if query_type == "fundamental":
                return self._get_fundamentals(stock, ticker)
            elif query_type == "news":
                return self._get_news(stock, ticker)
            elif query_type == "market":
                return self._get_market_data(stock, ticker)
            else:
                return f"Unknown query type: {query_type}"
                
        except Exception as e:
            logger.error(f"Error fetching {query_type} data for {ticker}: {str(e)}")
            return f"Error fetching data for {ticker}: {str(e)}"
    
    def _get_fundamentals(self, stock, ticker):
        """Get fundamental financial metrics"""
        try:
            info = stock.info
            
            # Get financial statements
            income_stmt = stock.income_stmt
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cash_flow
            
            # Calculate additional metrics if available
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            
            fundamentals = {
                "ticker": ticker,
                "company_name": info.get('longName', 'N/A'),
                "sector": info.get('sector', 'N/A'),
                "industry": info.get('industry', 'N/A'),
                "market_cap": info.get('marketCap', 0),
                "enterprise_value": info.get('enterpriseValue', 0),
                
                # Valuation Metrics
                "pe_ratio": info.get('trailingPE', 0),
                "forward_pe": info.get('forwardPE', 0),
                "peg_ratio": info.get('pegRatio', 0),
                "pb_ratio": info.get('priceToBook', 0),
                "ps_ratio": info.get('priceToSalesTrailing12Months', 0),
                "ev_to_revenue": info.get('enterpriseToRevenue', 0),
                "ev_to_ebitda": info.get('enterpriseToEbitda', 0),
                
                # Profitability Metrics
                "profit_margins": info.get('profitMargins', 0),
                "gross_margins": info.get('grossMargins', 0),
                "operating_margins": info.get('operatingMargins', 0),
                "roe": info.get('returnOnEquity', 0),
                "roa": info.get('returnOnAssets', 0),
                
                # Growth Metrics
                "revenue_growth": info.get('revenueGrowth', 0),
                "earnings_growth": info.get('earningsGrowth', 0),
                "revenue_per_share": info.get('revenuePerShare', 0),
                
                # Financial Health
                "current_ratio": info.get('currentRatio', 0),
                "quick_ratio": info.get('quickRatio', 0),
                "debt_to_equity": info.get('debtToEquity', 0),
                "total_cash": info.get('totalCash', 0),
                "total_debt": info.get('totalDebt', 0),
                "free_cash_flow": info.get('freeCashflow', 0),
                
                # Dividend Info
                "dividend_yield": info.get('dividendYield', 0),
                "dividend_rate": info.get('dividendRate', 0),
                "payout_ratio": info.get('payoutRatio', 0),
                
                # Share Statistics
                "shares_outstanding": info.get('sharesOutstanding', 0),
                "float_shares": info.get('floatShares', 0),
                "shares_short": info.get('sharesShort', 0),
                "short_ratio": info.get('shortRatio', 0),
                "short_percent_of_float": info.get('shortPercentOfFloat', 0),
                
                # Analyst Recommendations
                "target_mean_price": info.get('targetMeanPrice', 0),
                "recommendation_mean": info.get('recommendationMean', 0),
                "number_of_analysts": info.get('numberOfAnalystOpinions', 0),
                
                # Current Price Info
                "current_price": current_price,
                "52_week_high": info.get('fiftyTwoWeekHigh', 0),
                "52_week_low": info.get('fiftyTwoWeekLow', 0),
                "50_day_average": info.get('fiftyDayAverage', 0),
                "200_day_average": info.get('twoHundredDayAverage', 0),
                
                "data_date": datetime.now().strftime("%Y-%m-%d"),
                "data_source": "Yahoo Finance"
            }
            
            # Format the response for the agents
            formatted_response = f"""
Fundamental Analysis for {ticker} - {fundamentals['company_name']}
====================================================================

COMPANY OVERVIEW:
- Sector: {fundamentals['sector']}
- Industry: {fundamentals['industry']}
- Market Cap: ${fundamentals['market_cap']:,.0f}
- Enterprise Value: ${fundamentals['enterprise_value']:,.0f}

VALUATION METRICS:
- P/E Ratio: {fundamentals['pe_ratio']:.2f}
- Forward P/E: {fundamentals['forward_pe']:.2f}
- P/B Ratio: {fundamentals['pb_ratio']:.2f}
- EV/EBITDA: {fundamentals['ev_to_ebitda']:.2f}
- Price/Sales: {fundamentals['ps_ratio']:.2f}

PROFITABILITY:
- Gross Margins: {fundamentals['gross_margins']*100:.1f}%
- Operating Margins: {fundamentals['operating_margins']*100:.1f}%
- Net Margins: {fundamentals['profit_margins']*100:.1f}%
- ROE: {fundamentals['roe']*100:.1f}%
- ROA: {fundamentals['roa']*100:.1f}%

GROWTH METRICS:
- Revenue Growth: {fundamentals['revenue_growth']*100:.1f}%
- Earnings Growth: {fundamentals['earnings_growth']*100:.1f}%

FINANCIAL HEALTH:
- Current Ratio: {fundamentals['current_ratio']:.2f}
- Debt/Equity: {fundamentals['debt_to_equity']:.2f}
- Total Cash: ${fundamentals['total_cash']:,.0f}
- Total Debt: ${fundamentals['total_debt']:,.0f}
- Free Cash Flow: ${fundamentals['free_cash_flow']:,.0f}

ANALYST SENTIMENT:
- Target Price: ${fundamentals['target_mean_price']:.2f}
- Current Price: ${fundamentals['current_price']:.2f}
- Upside Potential: {((fundamentals['target_mean_price']/fundamentals['current_price']-1)*100 if fundamentals['current_price'] > 0 else 0):.1f}%
- Number of Analysts: {fundamentals['number_of_analysts']}
"""
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error getting fundamentals for {ticker}: {str(e)}")
            return f"Limited fundamental data available for {ticker}"
    
    def _get_news(self, stock, ticker):
        """Get recent news and sentiment"""
        try:
            news_items = stock.news
            
            if not news_items:
                return f"No recent news available for {ticker}"
            
            news_summary = f"Recent News for {ticker}\n" + "="*50 + "\n\n"
            
            for i, item in enumerate(news_items[:10], 1):  # Get up to 10 news items
                title = item.get('title', 'No title')
                publisher = item.get('publisher', 'Unknown')
                link = item.get('link', '')
                
                # Simple sentiment analysis based on keywords
                sentiment = self._analyze_sentiment(title)
                
                news_summary += f"{i}. {title}\n"
                news_summary += f"   Publisher: {publisher}\n"
                news_summary += f"   Sentiment: {sentiment}\n"
                news_summary += f"   Link: {link}\n\n"
            
            # Add overall sentiment assessment
            avg_sentiment = self._calculate_average_sentiment(news_items[:10])
            news_summary += f"\nOVERALL SENTIMENT: {avg_sentiment}"
            
            return news_summary
            
        except Exception as e:
            logger.error(f"Error getting news for {ticker}: {str(e)}")
            return f"No recent news available for {ticker}"
    
    def _get_market_data(self, stock, ticker):
        """Get current market data and price history"""
        try:
            info = stock.info
            
            # Get recent price history
            history = stock.history(period="1mo")
            
            if history.empty:
                return f"No market data available for {ticker}"
            
            # Calculate price changes
            current_price = history['Close'].iloc[-1]
            week_ago_price = history['Close'].iloc[-5] if len(history) >= 5 else history['Close'].iloc[0]
            month_ago_price = history['Close'].iloc[0]
            
            week_change = ((current_price - week_ago_price) / week_ago_price * 100) if week_ago_price > 0 else 0
            month_change = ((current_price - month_ago_price) / month_ago_price * 100) if month_ago_price > 0 else 0
            
            # Volume analysis
            avg_volume = history['Volume'].mean()
            recent_volume = history['Volume'].iloc[-1]
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            market_data = f"""
Market Data for {ticker}
====================================

PRICE INFORMATION:
- Current Price: ${current_price:.2f}
- Week Change: {week_change:.2f}%
- Month Change: {month_change:.2f}%
- 52-Week High: ${info.get('fiftyTwoWeekHigh', 0):.2f}
- 52-Week Low: ${info.get('fiftyTwoWeekLow', 0):.2f}

VOLUME ANALYSIS:
- Recent Volume: {recent_volume:,.0f}
- Average Volume (30d): {avg_volume:,.0f}
- Volume Ratio: {volume_ratio:.2f}x

TRADING METRICS:
- Beta: {info.get('beta', 'N/A')}
- Bid: ${info.get('bid', 0):.2f}
- Ask: ${info.get('ask', 0):.2f}
- Bid Size: {info.get('bidSize', 0)}
- Ask Size: {info.get('askSize', 0)}

TECHNICAL INDICATORS:
- 50-Day MA: ${info.get('fiftyDayAverage', 0):.2f}
- 200-Day MA: ${info.get('twoHundredDayAverage', 0):.2f}
- Above 50-Day MA: {'Yes' if current_price > info.get('fiftyDayAverage', 0) else 'No'}
- Above 200-Day MA: {'Yes' if current_price > info.get('twoHundredDayAverage', 0) else 'No'}
"""
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data for {ticker}: {str(e)}")
            return f"Limited market data available for {ticker}"
    
    def _analyze_sentiment(self, text):
        """Simple sentiment analysis based on keywords"""
        positive_words = ['upgrade', 'buy', 'outperform', 'positive', 'growth', 'strong', 
                         'beat', 'exceed', 'record', 'surge', 'rally', 'gain']
        negative_words = ['downgrade', 'sell', 'underperform', 'negative', 'decline', 
                         'weak', 'miss', 'fall', 'drop', 'loss', 'cut', 'concern']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "POSITIVE"
        elif negative_count > positive_count:
            return "NEGATIVE"
        else:
            return "NEUTRAL"
    
    def _calculate_average_sentiment(self, news_items):
        """Calculate overall sentiment from news items"""
        sentiments = []
        for item in news_items:
            title = item.get('title', '')
            sentiment = self._analyze_sentiment(title)
            if sentiment == "POSITIVE":
                sentiments.append(1)
            elif sentiment == "NEGATIVE":
                sentiments.append(-1)
            else:
                sentiments.append(0)
        
        if not sentiments:
            return "NEUTRAL"
        
        avg = sum(sentiments) / len(sentiments)
        
        if avg > 0.3:
            return "BULLISH"
        elif avg < -0.3:
            return "BEARISH"
        else:
            return "NEUTRAL"

# Create an instance for import
yfinance_tool = YFinanceMarketData()

# Make it compatible with your existing code
query_institutional_database = yfinance_tool.query_institutional_database

if __name__ == "__main__":
    # Test the tool
    tool = YFinanceMarketData()
    
    # Test with a real ticker
    print("Testing with AAPL:")
    print("\nFundamentals:")
    print(tool.query_institutional_database("AAPL", "fundamental"))
    
    print("\nNews:")
    print(tool.query_institutional_database("AAPL", "news"))
    
    print("\nMarket Data:")
    print(tool.query_institutional_database("AAPL", "market"))