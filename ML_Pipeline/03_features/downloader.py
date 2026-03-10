import os
import requests
import json
from datetime import datetime

# Konfigūracija
SYMBOL = "BTCUSDT"
YEAR = "2020"
METRICS = ["fundingRate", "openInterest", "liquidationOrder"]
BASE_URL = "https://data.binance.vision/data/futures/um"
DOWNLOAD_DIR = r"C:\Users\Mr. Perfect\tradingbot\ML_Pipeline\03_features\downloads"

def download_file(url, filename):
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        #print(f"Skipping {filename}, already exists.")
        return True
    
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        print(f"Successfully downloaded {filename}")
        return True
    return False

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    print(f"--- Starting Binance Historical Data Downloader for {SYMBOL} {YEAR} ---")
    
    results = {}

    for metric in METRICS:
        results[metric] = []
        print(f"\nChecking metric: {metric}")
        
        # Tikriname mėnesinius failus
        for month in range(1, 13):
            month_str = f"{month:02d}"
            filename = f"{SYMBOL}-{metric}-{YEAR}-{month_str}.zip"
            url = f"{BASE_URL}/monthly/{metric}/{SYMBOL}/{filename}"
            
            if download_file(url, filename):
                results[metric].append(f"{YEAR}-{month_str}")
                continue
            
            # Jei mėnesinio nėra, tikriname dieninius tiems patiems mėnesiams (bent jau pirmas kelias dienas)
            # Tikriname tik jei mėnesinio nėra, kad patvirtintume ar būtų galima surinkti iš dienų
            day_success = False
            for day in range(1, 32):
                day_str = f"{day:02d}"
                day_filename = f"{SYMBOL}-{metric}-{YEAR}-{month_str}-{day_str}.zip"
                day_url = f"{BASE_URL}/daily/{metric}/{SYMBOL}/{day_filename}"
                
                # Check head first to avoid slow 404 downloads
                # Check first day of month to see if metric folder even exists for 2020
                if day == 1:
                    res = requests.head(day_url)
                    if res.status_code != 200:
                        break # Skip this month day loop
                
                if download_file(day_url, day_filename):
                    day_success = True
            
            if day_success:
                results[metric].append(f"{YEAR}-{month_str} (Daily)")
    
    print("\n--- Download Summary ---")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
