# Stockworth

## Installation

```bash
pip install -r requirements.txt
```

```bash
# Extract tickers from etoro file
python extract_tickers.py
# Generates tickers.json

# Run main analysis script
python stockworth.py
# Generates buytickers file

# Remove tickers in which there is a problem with the data (either unavailable or different SE)
python remove_unavailable.py
```