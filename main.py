import yfinance as yf
import json
from tqdm import tqdm  # Ensure tqdm is imported
import time
import requests

def analyze_stock(ticker: str) -> str:
    """
    Analyze a stock using a combination of Graham's intrinsic value and criteria checks.

    Parameters:
    ticker (str): The stock ticker symbol.

    Returns:
    str: The recommendation ("Buy" or "Not Buy").
    """
    try:
        # Fetch stock data
        stock = yf.Ticker(ticker)
        info = stock.info
        balance_sheet = stock.balance_sheet if hasattr(stock, "balance_sheet") else None
        
        # Extract necessary data
        current_price = info.get("currentPrice", 0)
        pe_ratio = info.get("trailingPE", 0)
        pb_ratio = info.get("priceToBook", 0)
        dividend_yield = info.get("dividendYield", 0) * 100
        debt_to_equity = info.get("debtToEquity", 0)
        earnings_growth = info.get("earningsGrowth", 0) * 100
        eps = info.get("trailingEps", 0)
        book_value_per_share = info.get("bookValue", 0)
        sector = info.get("sector", "N/A")
        
        # Ensure values are valid floats
        current_price = float(current_price) if isinstance(current_price, (int, float)) else 0
        pe_ratio = float(pe_ratio) if isinstance(pe_ratio, (int, float)) else 0
        pb_ratio = float(pb_ratio) if isinstance(pb_ratio, (int, float)) else 0
        dividend_yield = float(dividend_yield) if isinstance(dividend_yield, (int, float)) else 0
        debt_to_equity = float(debt_to_equity) if isinstance(debt_to_equity, (int, float)) else 0
        earnings_growth = float(earnings_growth) if isinstance(earnings_growth, (int, float)) else 0
        eps = float(eps) if isinstance(eps, (int, float)) else 0
        book_value_per_share = float(book_value_per_share) if isinstance(book_value_per_share, (int, float)) else 0
        
        # Calculate current ratio if balance sheet data is available
        current_ratio = (
            balance_sheet.loc["Total Current Assets"].iloc[0] /
            balance_sheet.loc["Total Current Liabilities"].iloc[0]
            if balance_sheet is not None and "Total Current Assets" in balance_sheet.index and "Total Current Liabilities" in balance_sheet.index
            else 0
        )

        # Graham's intrinsic value formula: V = EPS * (8.5 + 2g) * (4.4 / Y)
        # where Y is the current yield of AAA corporate bonds
        growth_rate = 5  # Assuming 5% growth rate
        bond_yield = 4.4  # Assuming a fixed bond yield, you might want to fetch the current yield
        intrinsic_value = eps * (8.5 + 2 * growth_rate) * (4.4 / bond_yield)
        
        # Margin of Safety
        margin_of_safety = ((intrinsic_value - current_price) / current_price) * 100 if current_price else 0
        
        # Criteria checks
        criteria = [
            ("P/E < 20", pe_ratio < 20 if pe_ratio else False),
            ("P/B < 2", pb_ratio < 2 if pb_ratio else False),
            ("Debt-to-Equity < 0.5", debt_to_equity < 0.5 if debt_to_equity else False),
            ("Current Ratio > 1.5", current_ratio > 1.5 if current_ratio else False),
            ("Earnings Growth > 5%", earnings_growth > 5 if earnings_growth else False),
            ("Dividend Yield > 0", dividend_yield > 0 if dividend_yield else False),
            ("Earnings Stability", eps > 0),  # Simplified check for earnings stability
            ("Dividend Record", dividend_yield > 0),  # Simplified check for dividend record
        ]

        # Count the number of "Pass" results
        pass_count = sum(result for _, result in criteria)
        total_criteria = len(criteria)
        
        # Make recommendation
        recommendation = "Buy" if all(result for _, result in criteria) and margin_of_safety > 30 else "Not Buy"

        return recommendation

    except requests.exceptions.RequestException as e:
        print(f"Error analyzing stock {ticker}: {e}")
        return "Error"
    except Exception as e:
        print(f"Error analyzing stock {ticker}: {e}")
        return "Error"

if __name__ == "__main__":
    with open("tickers.json", "r") as file:
        tickers = json.load(file)  # Load ticker symbols from JSON file

    buy_recommendations = []
    unavailable_tickers = []

    for ticker in tqdm(tickers, desc="Analyzing tickers"):
        recommendation = analyze_stock(ticker)
        if recommendation == "Buy":
            buy_recommendations.append(ticker)
        elif recommendation == "Error":
            unavailable_tickers.append(ticker)
        time.sleep(1)  # Introduce a 1-second delay between requests

    print("\nTickers with 'Buy' recommendation:")
    for ticker in buy_recommendations:
        print(ticker)

    # Save unavailable tickers to a JSON file
    with open("unavailable_tickers.json", "w") as file:
        json.dump(unavailable_tickers, file, indent=4)
