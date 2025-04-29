import json
import logging
import math
import time

import numpy as np
import yfinance as yf
from tqdm import tqdm

from config import DATA_DIR, ASSUMPTIONS_LOG, TICKERS_FILE, UNAVAILABLE_TICKERS_FILE

# Configure logging
logging.basicConfig(
    filename=ASSUMPTIONS_LOG,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def log_assumption(ticker: str, field: str, assumed_value: float):
    logging.info(f"{ticker}: Assumed {field} = {assumed_value}")


def detect_outliers(intrinsic_values):
    if len(intrinsic_values) < 10:
        return None  # Not enough data

    median_value = np.median(intrinsic_values)
    std_dev = np.std(intrinsic_values)

    threshold = median_value + 3 * std_dev  # 3-sigma rule
    return threshold


def fetch_bond_yield(default_yield: float = 0.044) -> float:
    """Fetch 10-year US treasury bond yield"""
    try:
        bond_data = yf.Ticker("^TNX")
        history = bond_data.history(period="1d")
        latest_yield = history["Close"].iloc[-1] / 100  # Convert from % to decimal

        return max(0.01, min(latest_yield, 0.10))  # Ensure realistic range
    except Exception as e:
        logging.error(f"Error fetching bond yield: {e}. Using default yield of {default_yield * 100}%.")
        return default_yield


def calculate_cagr(initial: float, final: float, years: int) -> float:
    """Calculate Compound Annual Growth Rate (CAGR)"""
    if initial <= 0 or final <= 0 or years <= 0:
        logging.error(f"Invalid CAGR inputs: initial={initial}, final={final}, years={years}.")
        return None
    try:
        cagr = ((final / initial) ** (1 / years) - 1) * 100
        return cagr if np.isfinite(cagr) else None
    except (ZeroDivisionError, ValueError) as e:
        logging.error(f"Error calculating CAGR: {e}.")
        return None


def get_growth_rate(ticker: str, default_growth_rate: float = 0.03) -> float:
    """Estimate growth rate based on net income CAGR"""
    try:
        stock = yf.Ticker(ticker)
        financials = stock.financials

        if financials is None or "Net Income" not in financials.index:
            return default_growth_rate

        net_income = financials.loc["Net Income"].dropna()
        if len(net_income) < 3:
            return default_growth_rate

        net_income_values = net_income.values[::-1]
        smoothed_income = np.median(net_income_values[-3:])
        initial = np.median(net_income_values[:3])
        years = len(net_income_values) - 1

        cagr = calculate_cagr(initial, smoothed_income, years)
        return max(0, min(cagr, 10)) / 100 if cagr is not None else default_growth_rate
    except Exception as e:
        logging.error(f"Error calculating growth rate for {ticker}: {e}")
        return default_growth_rate


def calculate_intrinsic_value(eps: float, growth_rate: float, bond_yield: float) -> float:
    """Calculate intrinsic value using an adjusted Graham's formula"""
    if eps <= 0 or bond_yield <= 0:
        logging.warning("Invalid EPS or bond yield. Skipping intrinsic value calculation.")
        return 0

    adjusted_growth = 7 + 1.5 * min(math.log1p(growth_rate * 100), 2)
    intrinsic_value = eps * adjusted_growth * (4.4 / bond_yield)

    return intrinsic_value


def analyze_stock(ticker: str, bond_yield: float) -> tuple:
    """Analyze stock and determine buy/sell recommendation"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        current_price = info.get("currentPrice", 0.0)
        eps = info.get("trailingEps", None)
        if eps is None or eps <= 0:
            logging.warning(f"{ticker}: Invalid EPS ({eps}). Skipping stock.")
            return "Not Buy", [("EPS > 0", False, eps)]

        pe_ratio = info.get("trailingPE", 0.0)
        pb_ratio = info.get("priceToBook", 0.0)
        debt_to_equity = info.get("debtToEquity", 0.0)
        dividend_yield = info.get("dividendYield", 0.0) * 100

        growth_rate = get_growth_rate(ticker, default_growth_rate=0.03)
        intrinsic_value = calculate_intrinsic_value(eps, growth_rate, bond_yield)
        intrinsic_value = min(intrinsic_value, 5 * current_price)

        margin_of_safety = ((intrinsic_value - current_price) / current_price) * 100 if current_price else 0
        margin_of_safety = min(max(margin_of_safety, -50), 100)

        criteria = [
            ("EPS > 0", eps > 0, eps),
            ("P/E < 20", pe_ratio < 20, pe_ratio),
            ("P/B < 2", pb_ratio < 2, pb_ratio),
            ("Debt-to-Equity < 0.5", debt_to_equity < 0.5, debt_to_equity),
            ("Intrinsic Value > Current Price", intrinsic_value > current_price, intrinsic_value),
            ("Margin of Safety > 30%", margin_of_safety > 30, margin_of_safety),
            ("Dividend Yield > 0", dividend_yield > 0, dividend_yield),
        ]

        recommendation = "Buy" if all(result for _, result, _ in criteria) else "Not Buy"

        return recommendation, criteria
    except Exception as e:
        logging.error(f"Error analyzing stock {ticker}: {e}")
        return "Error", []


if __name__ == "__main__":
    bond_yield = fetch_bond_yield()
    try:
        with open(TICKERS_FILE, "r") as file:
            tickers = json.load(file)
    except FileNotFoundError:
        logging.error("tickers.json file not found. Exiting.")
        exit(1)

    buy_recommendations = []
    unavailable_tickers = []
    intrinsic_values = []

    for ticker in tqdm(tickers, desc="Analyzing tickers"):
        recommendation, criteria = analyze_stock(ticker, bond_yield)
        if recommendation == "Buy":
            buy_recommendations.append((ticker, criteria))
            for criterion, result, value in criteria:
                if criterion == "Intrinsic Value > Current Price" and result:
                    intrinsic_values.append(value)
        elif recommendation == "Error":
            unavailable_tickers.append(ticker)
        time.sleep(1)

    print("\nTickers with 'Buy' recommendation:")
    for ticker, criteria in buy_recommendations:
        print(f"{ticker}:")
        for criterion, result, value in criteria:
            print(f"  {criterion}: {'Pass' if result else 'Fail'} (Value: {value:.2f})")

    with open(UNAVAILABLE_TICKERS_FILE, "w") as file:
        json.dump(unavailable_tickers, file, indent=4)
