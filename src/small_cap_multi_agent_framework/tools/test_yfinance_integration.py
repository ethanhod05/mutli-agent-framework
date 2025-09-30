# test_yfinance_integration.py
from small_cap_multi_agent_framework.tools.hedge_fund_database import query_institutional_database

# Test with real tickers
print("Testing AAPL:")
print(query_institutional_database("AAPL", "fundamental"))
print("\n" + "="*50 + "\n")
print(query_institutional_database("AAPL", "news"))