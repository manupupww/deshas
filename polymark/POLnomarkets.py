#!/usr/bin/env python3
# NO MARKETS TRACKER - Aggregates NO volume per market

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
MIN_VOLUME_USD = 1000           # Minimum NO volume to show
REFRESH_INTERVAL_SECONDS = 5    
MAX_MARKETS_DISPLAY = 30         
SWEEPS_CSV_FILE = "data/sweeps_database.csv"
TIME_WINDOW_MINUTES = 60 * 24 * 7 # Look back 7 days for aggregate volume

def load_no_markets():
    """Load sweeps, filter for NO side, and aggregate by market"""
    if os.path.exists(SWEEPS_CSV_FILE):
        df = pd.read_csv(SWEEPS_CSV_FILE)

        # Filter by time window
        current_time_ts = datetime.now(pytz.UTC).timestamp()
        time_threshold = current_time_ts - (TIME_WINDOW_MINUTES * 60)
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            df = df[df['timestamp'] >= time_threshold]

        # Filter for NO outcome
        if 'outcome' in df.columns:
            df = df[df['outcome'].astype(str).str.upper() == 'NO']
        else:
            return pd.DataFrame() # Cannot filter without outcome

        # Calculate USD amount if it doesn't exist
        if 'usd_amount' not in df.columns:
            size = pd.to_numeric(df.get('size', 0), errors='coerce')
            price = pd.to_numeric(df.get('price', 0), errors='coerce')
            df['usd_amount'] = size * price
        else:
            df['usd_amount'] = pd.to_numeric(df['usd_amount'], errors='coerce')

        # Aggregate by Market Name
        market_col = 'title' if 'title' in df.columns else 'market_name' if 'market_name' in df.columns else None
        
        if not market_col:
            return pd.DataFrame()

        # Group by market and sum USD amount
        agg_df = df.groupby(market_col, as_index=False)['usd_amount'].sum()
        
        # Filter strictly by minimum aggregated volume
        agg_df = agg_df[agg_df['usd_amount'] >= MIN_VOLUME_USD]

        # Sort highest volume first
        agg_df = agg_df.sort_values('usd_amount', ascending=False)

        return agg_df.head(MAX_MARKETS_DISPLAY)
    else:
        return pd.DataFrame()

def display_no_markets(df):
    """Display aggregated NO markets clearly in terminal"""
    os.system('clear' if os.name == 'posix' else 'cls')

    # Header
    now = datetime.now(pytz.timezone('US/Eastern'))
    print(colored(f"🔴 NO MARKETS (Volume > ${MIN_VOLUME_USD:,})", "red", attrs=['bold']))
    print(colored(f"Last updated: {now.strftime('%H:%M:%S ET')}", "white"))
    print(colored("=" * 100, "white"))

    if df.empty:
        print(colored(f"\nNeturime NO rinkų duomenų...", "yellow"))
        return

    # Table Header
    print(colored(f"{'NO Volume':<15} | {'Market Name'}", "yellow", attrs=['bold']))
    print(colored("-" * 100, "white"))

    # Print each aggregated market
    for idx, row in df.iterrows():
        amount = float(row.get('usd_amount', 0))
        market = str(row.get('title', row.get('market_name', 'Unknown Market')))
        
        amount_str = f"${amount:,.0f}"

        # Assign prefixes based on size
        if amount >= 100000:
            prefix = "🔥 "
            color = 'green'
        elif amount >= 50000:
            prefix = "⚡ "
            color = 'green'
        else:
            prefix = "💰 "
            color = 'yellow'
            
        # Print Colors
        print(colored(f"{prefix}{amount_str:<12}", color, attrs=['bold']), end=" | ")
        print(colored(f"{market[:80]}", "white"))
        
    print(colored("=" * 100, "white"))

# Main Run Loop
if __name__ == "__main__":
    while True:
        try:
            no_df = load_no_markets()
            display_no_markets(no_df)
        except Exception as e:
            print(colored(f"Klaida nuskaitant failą: {e}", "red"))
        time.sleep(REFRESH_INTERVAL_SECONDS)
