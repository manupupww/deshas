import os
import requests
import zipfile
import pandas as pd
from datetime import datetime

def download_file(url, target_path):
    print(f"Downloading {url}...")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    else:
        print(f"Failed to download: {url} (Status: {response.status_code})")
        return False

def fetch_binance_data(years=["2020", "2021", "2022"], symbol="BTCUSDT"):
    base_dir = r"C:\Users\Mr. Perfect\tradingbot\data\binance_vision"
    os.makedirs(base_dir, exist_ok=True)
    
    # Funding Rate URLs
    funding_base = "https://data.binance.vision/data/futures/um/monthly/fundingRate/"
    # Premium Index URLs (1h)
    premium_base = "https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/"
    
    for year in years:
        print(f"Fetching data for {year}...")
        for month in range(1, 13):
            # Skip future months in 2022 if requested target is 2022-12
            # But let's just try downloading all 12, if 12 fails, that's fine.
            m_str = f"{month:02d}"
            
            # 1. Funding Rate
            f_name = f"{symbol}-fundingRate-{year}-{m_str}.zip"
            f_url = f"{funding_base}{symbol}/{f_name}"
            f_path = os.path.join(base_dir, f_name)
            if not os.path.exists(f_path):
                download_file(f_url, f_path)
            
            # 2. Premium Index
            p_name = f"{symbol}-1h-{year}-{m_str}.zip"
            p_url = f"{premium_base}{symbol}/1h/{p_name}"
            p_path = os.path.join(base_dir, p_name)
            if not os.path.exists(p_path):
                download_file(p_url, p_path)

    # Extract all
    print("Extracting files...")
    for item in os.listdir(base_dir):
        if item.endswith(".zip"):
            try:
                zip_ref = zipfile.ZipFile(os.path.join(base_dir, item), 'r')
                zip_ref.extractall(base_dir)
                zip_ref.close()
            except Exception as e:
                print(f"Could not extract {item}: {e}")
    print("Done fetching.")

if __name__ == "__main__":
    fetch_binance_data()

