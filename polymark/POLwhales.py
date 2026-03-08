#!/usr/bin/env python3
# WHALES TRACKER (Sweeps > $5K) - Text Based

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
MIN_WHALE_AMOUNT_USD = 5000     
REFRESH_INTERVAL_SECONDS = 5    
MAX_WHALES_DISPLAY = 30         
SWEEPS_CSV_FILE = "data/sweeps_database.csv"
TIME_WINDOW_MINUTES = 60 * 24   # Show from last 24 hours

def load_whales():
    """Load sweeps from CSV and filter for whales"""
    if os.path.exists(SWEEPS_CSV_FILE):
        df = pd.read_csv(SWEEPS_CSV_FILE)

        # Filter by time window
        current_time_ts = datetime.now(pytz.UTC).timestamp()
        time_threshold = current_time_ts - (TIME_WINDOW_MINUTES * 60)
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            df = df[df['timestamp'] >= time_threshold]

        # Calculate USD amount if it doesn't exist
        if 'usd_amount' not in df.columns:
            # Need sizes and prices to be float
            size = pd.to_numeric(df.get('size', 0), errors='coerce')
            price = pd.to_numeric(df.get('price', 0), errors='coerce')
            df['usd_amount'] = size * price
        else:
            df['usd_amount'] = pd.to_numeric(df['usd_amount'], errors='coerce')

        # Filter strictly by whale threshold
        df = df[df['usd_amount'] >= MIN_WHALE_AMOUNT_USD]

        # Sort newest first
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp', ascending=False)

        return df.head(MAX_WHALES_DISPLAY)
    else:
        return pd.DataFrame()

def format_time_ago(ts):
    """Format Unix timestamp into a human-readable 'time ago'"""
    try:
        now = datetime.now(pytz.UTC).timestamp()
        diff = now - float(ts)
        
        if pd.isna(ts) or diff < 0:
            return "---"
            
        if diff < 60:
            return f"{int(diff)}s ago"
        elif diff < 3600:
            return f"{int(diff // 60)}m ago"
        elif diff < 86400:
            return f"{int(diff // 3600)}h ago"
        else:
            return f"{int(diff // 86400)}d ago"
    except (ValueError, TypeError):
        return "---"


def display_whales(df):
    """Display whales clearly in terminal"""
    os.system('clear' if os.name == 'posix' else 'cls')

    # Header
    now = datetime.now(pytz.timezone('US/Eastern'))
    print(colored(f"🐋 WHALES TRACKER (+${MIN_WHALE_AMOUNT_USD:,})", "cyan", "on_black", attrs=['bold']))
    print(colored(f"Last updated: {now.strftime('%H:%M:%S ET')}", "white"))
    print(colored("=" * 60, "white"))

    if df.empty:
        print(colored(f"\n🌊 Ramus vandenynas... Nėra banginių (>${MIN_WHALE_AMOUNT_USD:,}).", "yellow"))
        return

    # Print each whale event
    for idx, row in df.iterrows():
        amount = float(row.get('usd_amount', 0))
        if amount < MIN_WHALE_AMOUNT_USD:
            continue
            
        amount_str = f"${amount:,.0f}"
        
        market = row.get('title', row.get('market_name', 'Unknown Market'))
        
        outcome = str(row.get('outcome', 'Unknown')).upper()
        side_text = 'YES' if outcome == 'YES' else 'NO' if outcome == 'NO' else outcome[:3]
        
        price = row.get('price', row.get('avg_price', 0))
        try:
            price_pc = f"{float(price)*100:.1f}%" if pd.notna(price) and float(price) > 0 else "-"
        except (ValueError, TypeError):
            price_pc = "-"

        time_ago = format_time_ago(row.get('timestamp'))

        # Print Colors
        print(colored(f"🔥 {amount_str:<12}", 'green', attrs=['bold']), end="")
        
        # Color the side text based on Yes/No
        if side_text == 'YES':
            print(colored(f"{side_text:<5}", 'green'), end="")
        elif side_text == 'NO':
            print(colored(f"{side_text:<5}", 'red'), end="")
        else:
            print(colored(f"{side_text:<5}", 'yellow'), end="")
        
        print(colored(f" @ {price_pc:<6}", 'cyan'), end="")
        print(colored(f" | {time_ago:<8}", 'white'), end="")
        print(f" | {market[:60]}...")
        
    print(colored("=" * 60, "white"))

# Main Run Loop
if __name__ == "__main__":
    while True:
        try:
            whales_df = load_whales()
            display_whales(whales_df)
        except Exception as e:
            print(colored(f"Klaida nuskaitant failą: {e}", "red"))
        time.sleep(REFRESH_INTERVAL_SECONDS)
