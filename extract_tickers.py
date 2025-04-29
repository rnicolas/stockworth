import json

def extract_tickers(file_path: str) -> list:
    """
    Extract tickers from the specified JSON file.

    Parameters:
    file_path (str): The path to the JSON file.

    Returns:
    list: A list of extracted tickers.
    """
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        
        tickers = [item['SymbolFull'] for item in data['InstrumentDisplayDatas'] if 'SymbolFull' in item]
        return tickers

    except Exception as e:
        print(f"Error extracting tickers: {e}")
        return []

if __name__ == "__main__":
    file_path = "etoro_info.json"
    tickers = extract_tickers(file_path)

    if tickers:
        with open("tickers.json", "w") as file:
            json.dump(tickers, file, indent=4)
        print(f"Extracted {len(tickers)} tickers and saved to 'tickers.json'")
    else:
        print("No tickers were extracted.")
