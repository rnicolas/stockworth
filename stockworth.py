import yfinance as yf
import json
import logging
import numpy as np
import math
from tqdm import tqdm
import time

# -------- LOGGING --------
logging.basicConfig(
    filename="graham_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log(message):
    logging.info(message)

# -------- HELPERS --------
def fetch_bond_yield(default_yield=0.044):
    try:
        bond = yf.Ticker("^TNX")
        yield_value = bond.history("1d")["Close"].iloc[-1] / 100
        return max(0.01, min(yield_value, 0.10))
    except Exception as e:
        log(f"Bond yield fetch failed: {e}. Using default {default_yield}")
        return default_yield

def calculate_growth_rate(ticker, default_growth=0.03):
    try:
        stock = yf.Ticker(ticker)
        fin = stock.financials
        if fin is None or "Net Income" not in fin.index:
            return default_growth

        net_income = fin.loc["Net Income"].dropna()
        if len(net_income) < 3:
            return default_growth

        initial = np.median(net_income.values[-3:])
        final = np.median(net_income.values[:3])
        years = len(net_income) - 1
        if final <= 0 or initial <= 0 or years <= 0:
            return default_growth

        cagr = ((initial / final) ** (1 / years) - 1)
        return max(0, min(cagr, 0.10))  # Cap at 10%
    except Exception as e:
        log(f"Growth rate calculation failed for {ticker}: {e}")
        return default_growth


def graham_intrinsic_value(eps, growth_rate, bond_yield, price):
    if eps <= 0 or bond_yield <= 0:
        return 0

    growth = min(growth_rate * 100, 10)  # Cap growth effect to 10%
    multiplier = 8.5 + 2 * growth
    intrinsic = eps * multiplier * (4.4 / bond_yield)

    # Cap intrinsic value to avoid runaway results
    intrinsic = min(intrinsic, 5 * price)

    return intrinsic


# -------- ANALYSIS --------
def analyze_stock(ticker, bond_yield):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        price = info.get("currentPrice", 0)
        eps = info.get("trailingEps", 0)
        pe = info.get("trailingPE", 0)
        pb = info.get("priceToBook", 0)
        debt_to_equity = info.get("debtToEquity", 1)
        dividend_yield = info.get("dividendYield", 0) * 100

        growth = calculate_growth_rate(ticker)
        intrinsic = graham_intrinsic_value(eps, growth, bond_yield, price)
        margin = ((intrinsic - price) / price) * 100 if price else -100

        criteria = [
            ("EPS > 0", eps > 0),
            ("P/E < 20", pe < 20 if pe else False),
            ("P/B < 2", pb < 2 if pb else False),
            ("Debt/Equity < 0.5", debt_to_equity < 0.5),
            ("Intrinsic > Price", intrinsic > price),
            ("Margin > 30%", margin > 30),
            ("Dividend > 0", dividend_yield > 0)
        ]

        passes = all(cond for _, cond in criteria)
        recommendation = "Buy" if passes else "Not Buy"

        return recommendation, criteria, intrinsic, margin

    except Exception as e:
        log(f"Analysis failed for {ticker}: {e}")
        return "Error", [], 0, 0


# -------- MAIN --------
if __name__ == "__main__":
    bond_yield = fetch_bond_yield()

    with open("tickers.json") as f:
        tickers = json.load(f)

    buy_list = []
    errors = []

    for ticker in tqdm(tickers, desc="Analyzing stocks"):
        result, checks, intrinsic_value, margin = analyze_stock(ticker, bond_yield)
        if result == "Buy":
            buy_list.append({
                "ticker": ticker,
                "intrinsic": intrinsic_value,
                "margin": margin,
                "criteria": [{"rule": rule, "pass": bool(passed)} for rule, passed in checks]
            })
        elif result == "Error":
            errors.append(ticker)
        time.sleep(1)

    print("\nBuy Recommendations:")
    for stock in buy_list:
        print(f"{stock['ticker']}: Intrinsic = {stock['intrinsic']:.2f}, Margin = {stock['margin']:.1f}%")

    with open("unavailable_tickers.json", "w") as f:
        json.dump(errors, f, indent=4)

    with open("buy_recommendations.json", "w") as f:
        json.dump(buy_list, f, indent=4)

    print("\nAnalysis complete. Results saved to JSON files.")
