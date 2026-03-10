#!/usr/bin/env python3
# DR. DATA DAWG's Mini Sweeper Dashboard – Optimized for Narrow Terminals! 🧹

import sys
import os
import time
import pandas as pd
from datetime import datetime
import pytz
from termcolor import colored
from colorama import init

# Initialize colorama for terminal colors
init(autoreset=True)

# ============================================================
# MINI DASHBOARD CONFIGURATION
# ============================================================

MIN_SWEEP_AMOUNT_USD = 3000     # Minimum sweep size in USD
REFRESH_INTERVAL_SECONDS = 5    # How often to refresh
MAX_SWEEPS_DISPLAY = 50         # Maximum sweeps to display
SWEEPS_CSV_FILE = "data/sweeps_database.csv"  # Read from same database
TIME_WINDOW_MINUTES = 30        # Show sweeps from last X minutes
HIGHLIGHT_MULTIPLIER = 3        # Highlight if sweep is Xx bigger than minimum

def load_sweeps_from_csv():
    """Load sweeps from existing CSV database"""
    if os.path.exists(SWEEPS_CSV_FILE):
        df = pd.read_csv(SWEEPS_CSV_FILE)

        # Filter by time window
        current_time = datetime.now(pytz.UTC).timestamp()
        time_threshold = current_time - (TIME_WINDOW_MINUTES * 60)
        df['timestamp'] = df['timestamp'].astype(float)
        df = df[df['timestamp'] >= time_threshold]

        # Filter by minimum amount
        if 'usd_amount' not in df.columns:
            df['usd_amount'] = df['size'].astype(float) * df['price'].astype(float)
        df = df[df['usd_amount'] >= MIN_SWEEP_AMOUNT_USD]

        # Sort newest first
        df = df.sort_values('timestamp', ascending=False)

        return df.head(MAX_SWEEPS_DISPLAY)
    else:
        return pd.DataFrame()

def get_usd_amount(row):
    """Calculate USD amount from size and price"""
    if 'usd_amount' in row.index and pd.notna(row['usd_amount']):
        return float(row['usd_amount'])
    size = float(row.get('size', 0))
    price = float(row.get('price', 0))
    return size * price

def format_time_ago(timestamp):
    """Format timestamp into a human-readable 'time ago' string"""
    try:
        if not timestamp:
            return "---"
        
        # Ensure timestamp is a float
        ts_float = float(timestamp)
        now = datetime.now(pytz.UTC).timestamp()
        diff = now - ts_float
        
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

def display_mini_dashboard(df):
    """Display compact vertical dashboard for narrow terminals"""
    os.system('clear' if os.name == 'posix' else 'cls')

    # Simple header
    now = datetime.now(pytz.timezone('US/Eastern'))
    print(colored(f"🧹 SWEEPS ${MIN_SWEEP_AMOUNT_USD:,}+", "cyan", attrs=['bold']))
    print(colored(f"{now.strftime('%H:%M:%S ET')}", "yellow"))
    print(colored("=" * 40, "white"))

    if df.empty:
        print(colored("\n🧼 No sweeps yet...", "yellow"))
        return

    # Display each sweep as a vertical card
    for idx, row in df.iterrows():
        amount = get_usd_amount(row)
        highlight_threshold = MIN_SWEEP_AMOUNT_USD * HIGHLIGHT_MULTIPLIER
        should_highlight = amount >= highlight_threshold

        # Time ago
        time_ago = format_time_ago(row.get('timestamp', ''))

        # Market title
        market = row.get('title', row.get('market_name', 'Unknown Market'))

        # Side (YES/NO)
        outcome = str(row.get('outcome', 'Unknown'))
        side_text = 'YES' if outcome.upper() == 'YES' else 'NO' if outcome.upper() == 'NO' else outcome[:3].upper()

        # Amount
        amount_str = f"${amount:,.0f}"

        # Price
        price = row.get('price', row.get('avg_price', 0))
        price_str = f"{float(price):.3f}" if pd.notna(price) and price > 0 else "-"

        # Market link
        market_slug = row.get('eventSlug', row.get('slug', ''))
        polymarket_url = f"https://polymarket.com/event/{market_slug}" if market_slug else None

        # Print the card
        if should_highlight:
            # Yellow highlight for big sweeps
            print(colored(f"\n{time_ago}", 'black', 'on_yellow', attrs=['bold']))
            print(colored(market, 'black', 'on_yellow', attrs=['bold']))
            print(colored(f"{side_text} • {amount_str} @ {price_str}", 'black', 'on_yellow', attrs=['bold']))
            if polymarket_url:
                print(f"\033]8;;{polymarket_url}\a{colored('🔗 View Market', 'black', 'on_yellow', attrs=['bold'])}\033]8;;\a")
        else:
            # Normal display with smart colors
            print(colored(f"\n{time_ago}", 'white'))
            print(market)

            # Color the side
            if outcome.upper() == 'YES':
                side_color = colored(side_text, 'green', attrs=['bold'])
            elif outcome.upper() == 'NO':
                side_color = colored(side_text, 'red', attrs=['bold'])
            else:
                side_color = colored(side_text, 'yellow')

            # Color the amount
            if amount >= 100000:
                amount_color = colored(amount_str, 'green', attrs=['bold'])
            elif amount >= 50000:
                amount_color = colored(amount_str, 'yellow', attrs=['bold'])
            else:
                amount_color = colored(amount_str, 'white')

            print(f"{side_color} • {amount_color} @ {colored(price_str, 'cyan')}")

            if polymarket_url:
                print(f"\033]8;;{polymarket_url}\a 🔗 View Market\033]8;;\a")

        # Separator
        print(colored("-" * 40, "white"))

# Main loop
while True:
    try:
        sweeps = load_sweeps_from_csv()
        display_mini_dashboard(sweeps)
    except Exception as e:
        print(colored(f"Error: {e}", "red"))
    time.sleep(REFRESH_INTERVAL_SECONDS)
