# create_real_stocks.py
import pandas as pd

# Define the stock data
stock_data = {
    'Ticker': [
        'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META',
        'TSLA', 'AMZN', 'BRK-B', 'JPM', 'V',
        'UNH', 'JNJ', 'LLY', 'PG', 'XOM',
        'COST', 'WMT', 'MA', 'HD', 'PFE',
        'DIS', 'NFLX', 'ADBE', 'CRM', 'ORCL',
        'AMD', 'INTC', 'BA', 'CAT', 'GE'
    ],
    'Company Name': [
        'Apple Inc', 'Microsoft Corp', 'NVIDIA Corp', 'Alphabet Inc', 'Meta Platforms',
        'Tesla Inc', 'Amazon.com Inc', 'Berkshire Hathaway', 'JPMorgan Chase', 'Visa Inc',
        'UnitedHealth Group', 'Johnson & Johnson', 'Eli Lilly', 'Procter & Gamble', 'Exxon Mobil',
        'Costco Wholesale', 'Walmart Inc', 'Mastercard', 'Home Depot', 'Pfizer Inc',
        'Walt Disney', 'Netflix Inc', 'Adobe Inc', 'Salesforce Inc', 'Oracle Corp',
        'Advanced Micro Devices', 'Intel Corp', 'Boeing Co', 'Caterpillar Inc', 'General Electric'
    ],
    'Sector': [
        'Technology', 'Technology', 'Technology', 'Communication Services', 'Communication Services',
        'Consumer Discretionary', 'Consumer Discretionary', 'Financials', 'Financials', 'Financials',
        'Healthcare', 'Healthcare', 'Healthcare', 'Consumer Staples', 'Energy',
        'Consumer Staples', 'Consumer Staples', 'Financials', 'Consumer Discretionary', 'Healthcare',
        'Communication Services', 'Communication Services', 'Technology', 'Technology', 'Technology',
        'Technology', 'Technology', 'Industrials', 'Industrials', 'Industrials'
    ],
    'Market Cap': [0] * 30
}

# Create the DataFrame
df = pd.DataFrame(stock_data)

# Save to CSV
df.to_csv('data/real_stocks.csv', index=False)

print(f"✅ Created real_stocks.csv with {len(df)} stocks")
print("\nFirst 5 stocks:")
print(df.head())
print("\nFile saved to: data/real_stocks.csv")