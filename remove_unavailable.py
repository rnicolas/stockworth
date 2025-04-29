import json

from config import TICKERS_FILE, UNAVAILABLE_TICKERS_FILE


def remove_unavailable_tickers(tickers_file, unavailable_file):
    # Load the list of tickers
    with open(tickers_file, 'r') as tf:
        tickers = json.load(tf)

    # Load the list of unavailable tickers
    with open(unavailable_file, 'r') as uf:
        unavailable_tickers = json.load(uf)

    # Remove unavailable tickers from the tickers list
    filtered_tickers = [ticker for ticker in tickers if ticker not in unavailable_tickers]

    # Overwrite the original tickers file with the updated list
    with open(tickers_file, 'w') as tf:
        json.dump(filtered_tickers, tf, indent=4)

    print(f"Updated tickers saved back to {tickers_file}")


def main():
    print(f"Cleaning tickers in {TICKERS_FILE} using {UNAVAILABLE_TICKERS_FILE}...")
    remove_unavailable_tickers(TICKERS_FILE, UNAVAILABLE_TICKERS_FILE)
    print("Tickers cleaned successfully!")


if __name__ == "__main__":
    main()
