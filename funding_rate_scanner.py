#!/usr/bin/env python3
"""
AI Pirate Vycka G's Funding Rate Scanner

Scans ALL Hyperliquid funding rates (both crypto perps and HIP3 tokenized assets)
and displays them in a clean pandas table. Loops every 5 minutes.

Built by AI Pirate Vycka G
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

import colorama
import pandas as pd
import requests
from colorama import Fore
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

colorama.init(autoreset=True)
load_dotenv()

# ===== CONFIG =====
BASE_URL = "https://api.moonddev.com"
LOOP_INTERVAL_SECONDS = 5 * 60  # 5 minutes
MIN_OI_VALUE = 5_000_000  # Minimum Open Interest value filter ($5M)

PIRATE_BANNER = f"""{Fore.CYAN}
   ___  ____    ____  _           _       
  / _ \\|_ _|   |  _ \\(_)_ __ __ _| |_ ___ 
 | |_| || |    | |_) | | '__/ _` | __/ _ \\
 |  _  || |    |  __/| | | | (_| | ||  __/
 |_| |_|___|   |_|   |_|_|  \\__,_|\\__\\___|
                  Vycka G                 
{Fore.MAGENTA}Funding Rate Scanner{Fore.RESET}
{Fore.YELLOW}Scan all Hyperliquid funding rates - Crypto & HIP3{Fore.RESET}

def _auth_headers():
    """AI Pirate Vycka G API auth headers"""
    api_key = os.getenv("MOONDEV_API_KEY")
    return {"X-API-Key": api_key} if api_key else {}

def fetch_crypto_funding():
    """Fetch funding rates for all crypto perps"""
    print(f"{Fore.CYAN}AI Pirate Vycka G fetching crypto perp funding rates...")
    response = requests.get(
        f"{BASE_URL}/api/hlp/funding",
        headers=_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def fetch_hip3_funding():
    """Fetch funding rates for all HIP3 tokenized assets"""
    print(f"{Fore.CYAN}AI Pirate Vycka G fetching HIP3 funding rates...")
    response = requests.get(
        f"{BASE_URL}/api/hlp/funding/hip3",
        headers=_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def parse_rates_to_df(data, source_label):
    """Parse funding rate data into a pandas DataFrame"""
    rates = data.get("all_rates", [])

    if not rates:
        if isinstance(data, list):
            rates = data
        else:
            for key in ["current_rates", "rates", "data"]:
                if key in data and data[key]:
                    rates = data[key]
                    break

    if not rates:
        print(f"{Fore.YELLOW}Warning: No rates found in {source_label} response")
        print(f"{Fore.YELLOW}  Response keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        return pd.DataFrame()

    if isinstance(rates, dict):
        rows = []
        for symbol, info in rates.items():
            if isinstance(info, dict):
                info["coin"] = symbol
                rows.append(info)
            else:
                rows.append({"coin": symbol, "rate_pct": info})
        rates = rows

df = pd.DataFrame(rates)
df["source"] = source_label
return df

def _standardize_df(df):
    """Standardize column names and numeric types"""
    col_map = {}
    for col in df.columns:
        lower = col.lower()
        if "coin" in lower or "symbol" in lower or "name" in lower:
            col_map[col] = "Symbol"
        elif "rate_pct" in lower or ("rate" in lower and "annual" not in lower and "yearly" not in lower):
            col_map[col] = "Rate %"
        elif "annual" in lower or "yearly" in lower:
            col_map[col] = "Annualized %"
        elif "mark" in lower and "price" in lower:
            col_map[col] = "Mark Price"
        elif "oi" in lower or "open_interest" in lower:
            col_map[col] = "OI Value"

    df = df.rename(columns=col_map)
    for c in ["Rate %", "Annualized %"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def display_top_bottom(df, label):
    """Show top 30 highest and top 30 lowest funding for a category"""
    df = _standardize_df(df.copy())

    if "Rate %" not in df.columns:
        print(f"{Fore.YELLOW}No Rate % column for {label}")
        return

    df = df.dropna(subset=["Rate %"]).sort_values("Rate %", ascending=False)
    display_cols = [c for c in ["Symbol", "Rate %", "Annualized %", "OI Value"] if c in df.columns]

    # OI filter - only show assets with OI >= MIN_OI_VALUE
    if "OI Value" in df.columns:
        df["OI Value"] = pd.to_numeric(df["OI Value"], errors="coerce")
        before_count = len(df)
        df = df[df["OI Value"] >= MIN_OI_VALUE]
        print(f"{Fore.YELLOW}OI Filter: {before_count} -> {len(df)} assets (min OI: {MIN_OI_VALUE})")

    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", lambda x: f"{x:.6f}" if abs(x) < 1 else f"{x:.2f}")

    top_pos = df.head(30)
    top_neg = df.tail(30).sort_values("Rate %", ascending=True)

    print(f"\n{Fore.GREEN}{'-' * 70}")
    print(f"{Fore.MAGENTA} AI Pirate Vycka G {label} TOP 30 HIGHEST FUNDING")
    print(f"{Fore.GREEN}{'-' * 70}")
    print(top_pos[display_cols].to_string(index=False))

print(f"\n{Fore.GREEN}{'= * 70'}")
print(f"{Fore.MAGENTA} AI Pirate Vycka G | {label} TOP 30 MOST NEGATIVE FUNDING")
print(f"{Fore.GREEN}{'= * 70'}")
print(top_neg[display_cols].to_string(index=False))
print(f"{Fore.GREEN}{'= * 70'}")

def scan():
    """Run one full funding rate scan"""
    print(f"\n{Fore.CYAN}{'= * 90'}")
    print(f"{Fore.YELLOW} AI Pirate Vycka G Funding Rate Scan | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.CYAN}{'= * 90'}")

    # Fetch crypto perps
    crypto_data = fetch_crypto_funding()
    crypto_df = parse_rates_to_df(crypto_data, "crypto")

    # Fetch HIP3 tokenized assets
    hip3_data = fetch_hip3_funding()
    hip3_df = parse_rates_to_df(hip3_data, "hip3")

    # Show top 30 high & top 30 low for each category
    for label, df in [("Crypto Perps", crypto_df), ("HIP3 Tokenized", hip3_df)]:
        if df.empty:
            continue
        display_top_bottom(df, label)

    print(f"{Fore.YELLOW}Scan complete. Next scan in {LOOP_INTERVAL_SECONDS // 60} minutes.")

if __name__ == "__main__":
    print(PIRATE_BANNER)
    print(f"{Fore.GREEN}AI Pirate Vycka G Funding Rate Scanner starting...")
    print(f"{Fore.YELLOW}    Scanning every {LOOP_INTERVAL_SECONDS // 60} minutes. Pr")

    scan()
    while True:
        time.sleep(LOOP_INTERVAL_SECONDS)
        scan()
