import json

from config import DATA_DIR, ETORO_INFO, TICKERS_FILE


def extract_tickers(file_name: str) -> list:
    """
    Extract tickers from the specified JSON file in DATA_DIR.

    Parameters:
    file_path (str): The path to the JSON file.

    Returns:
    list: A list of extracted tickers.
    """
    try:
        with open(f"{DATA_DIR}/{file_name}", "r") as file:
            data = json.load(file)
        tickers = [item['SymbolFull'] for item in data['InstrumentDisplayDatas'] if 'SymbolFull' in item]
        return tickers

    except Exception as e:
        print(f"Error extracting tickers: {e}")
        return []

if __name__ == "__main__":
    tickers = extract_tickers(ETORO_INFO)

    if tickers:
        with open(TICKERS_FILE, "w") as file:
            json.dump(tickers, file, indent=4)
        print(f"Extracted {len(tickers)} tickers and saved to 'tickers.json'")
    else:
        print("No tickers were extracted.")
