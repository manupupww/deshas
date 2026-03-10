#!/usr/bin/env python3
# EDGE MARKETS TRACKER - Shows markets between 3% and 97%

import os
import time
import pandas as pd
from datetime import datetime
import pytz
from termcolor import colored
from colorama import init

# Initialize colors
init(autoreset=True)

# CONFIGURATION
REFRESH_INTERVAL_SECONDS = 5    
MAX_MARKETS_DISPLAY = 30         
SWEEPS_CSV_FILE = "data/sweeps_database.csv"
TIME_WINDOW_MINUTES = 60 * 24 * 3 # Look back 3 days 

def load_edge_markets():
    """Load sweeps and filter for edge markets (3% to 97%)"""
    if os.path.exists(SWEEPS_CSV_FILE):
        df = pd.read_csv(SWEEPS_CSV_FILE)

        # Filter by time window
        current_time_ts = datetime.now(pytz.UTC).timestamp()
        time_threshold = current_time_ts - (TIME_WINDOW_MINUTES * 60)
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            df = df[df['timestamp'] >= time_threshold]

        # Extract market name
        if 'title' in df.columns:
            df['market_name_clean'] = df['title']
        elif 'market_name' in df.columns:
            df['market_name_clean'] = df['market_name']
        else:
            return pd.DataFrame()

        # Extract price
        df['price_float'] = pd.to_numeric(df.get('price', df.get('avg_price', 0)), errors='coerce')
        
        # We only want the latest price for each market
        df = df.sort_values('timestamp', ascending=False)
        latest_prices = df.drop_duplicates(subset=['market_name_clean'], keep='first')
        
        # Filter for edge prices: 0.03 to 0.97
        edge_df = latest_prices[(latest_prices['price_float'] >= 0.03) & (latest_prices['price_float'] <= 0.97)].copy()

        # Sort by price (lowest to highest)
        edge_df = edge_df.sort_values('price_float', ascending=True)

        return edge_df.head(MAX_MARKETS_DISPLAY)
    else:
        return pd.DataFrame()

def display_edge_markets(df):
    """Display Edge markets clearly in terminal"""
    os.system('clear' if os.name == 'posix' else 'cls')

    # Header
    now = datetime.now(pytz.timezone('US/Eastern'))
    print(colored(f"💎 EDGE MARKETS (Unresolved 3% - 97%)", "cyan", attrs=['bold']))
    print(colored(f"Last updated: {now.strftime('%H:%M:%S ET')}", "white"))
    print(colored("=" * 100, "white"))

    if df.empty:
        print(colored(f"\nŠiuo metu rinka rami, nėra tinkančių rinkų...", "yellow"))
        return

    # Table Header
    print(colored(f"{'Current Price':<15} | {'Market Name'}", "yellow", attrs=['bold']))
    print(colored("-" * 100, "white"))

    # Print each market
    for idx, row in df.iterrows():
        price = row.get('price_float', 0)
        market = str(row.get('market_name_clean', 'Unknown Market'))
        
        price_str = f"{price * 100:.1f}%"

        # Print Colors
        print(colored(f"{price_str:<15}", 'green', attrs=['bold']), end=" | ")
        print(colored(f"{market[:90]}", "white"))
        
    print(colored("=" * 100, "white"))

# Main Run Loop
if __name__ == "__main__":
    while True:
        try:
            edge_df = load_edge_markets()
            display_edge_markets(edge_df)
        except Exception as e:
            print(colored(f"Klaida nuskaitant failą: {e}", "red"))
        time.sleep(REFRESH_INTERVAL_SECONDS)
