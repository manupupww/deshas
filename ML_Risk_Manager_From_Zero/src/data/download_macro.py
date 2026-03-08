import yfinance as yf
import pandas as pd
import os

def download_macro_data(start_date="2020-01-01", end_date="2023-01-01"):
    # Symbols: 
    # DX-Y.NYB = US Dollar Index
    # ^GSPC = S&P 500
    # ^VIX = Volatility Index
    # GC=F = Gold Futures
    # ^TNX = 10-Year Treasury Yield
    symbols = {
        "dxy": "DX-Y.NYB",
        "spx": "^GSPC",
        "vix": "^VIX",
        "gold": "GC=F",
        "us10y": "^TNX"
    }
    
    output_dir = "data/macro"
    os.makedirs(output_dir, exist_ok=True)
    
    for name, ticker in symbols.items():
        print(f"Downloading {name} ({ticker})...")
        data = yf.download(ticker, start=start_date, end=end_date)
        if not data.empty:
            # Shift timestamps to match crypto CSV format (UTC)
            data.index = data.index.tz_localize(None)
            file_path = os.path.join(output_dir, f"{name}.csv")
            data.to_csv(file_path)
            print(f"Saved to {file_path}")
        else:
            print(f"Failed to download {name}")

if __name__ == "__main__":
    download_macro_data()
