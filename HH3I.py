#!/usr/bin/env python3
"""
AI Pirate Terminator X Funding Rate Scanner

Scans ALL Hyperliquid funding rates (crypto perps)
and displays them in a clean pandas table. Refresh interval: 5 minutes.

Author: AI Pirate Terminator X
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

import requests
import pandas as pd
import colorama
from colorama import Fore
from dotenv import load_dotenv


# ---------------------------------------------------------
# Path Setup
# ---------------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ---------------------------------------------------------
# Initialization
# ---------------------------------------------------------
colorama.init(autoreset=True)
load_dotenv()

# =========================================================
# Configuration
# =========================================================

# Official Hyperliquid Info API (No key needed)
BASE_URL = "https://api.hyperliquid.xyz/info"

# Loop interval: 5 minutes
LOOP_INTERVAL_SECONDS = 5 * 60

# Minimum Open Interest filter ($5M)
MIN_OI_VALUE = 5_000_000


# =========================================================
# Banner (ASCII Art)
# =========================================================

PIRATE_BANNER = rf"""{Fore.CYAN}
                ________
             .-"        "-.
            /               \
           |                 |
    |\     |  .-., (X) .-.,  |     /|
    | \    | )(__/     \__)( |    / |
    |  \   |/       /\      \|   /  |
    |   \  (_       ^^      _)  /   |
    |    \  \__  |IIIIII| __/  /    |
    |_____\  |   \IIIIII/  |  /_____|
              \           /
                `--------`
  _____ ___ ___ __  __ ___ _  _   _ _____ ___  ___ 
 |_   _| __| _ \  \/  |_ _| \| | /_\_   _/ _ \| _ \
   | | | _||   / |\/| || || .` |/ _ \| || (_) |   /
   |_| |___|_|_\_|  |_|___|_|\_/_/ \_\_| \___/|_|_\
                  Vycka X
{Fore.MAGENTA}Funding Rate Scanner{Fore.RESET}
{Fore.YELLOW}Scan all Hyperliquid funding rates — Live Official API{Fore.RESET}
"""

# No auth headers needed for official HL Info API
def _auth_headers() -> dict:
    return {"Content-Type": "application/json"}

def fetch_hl_data() -> tuple[list, list]:
    """
    Fetch all metadata and asset contexts from Hyperliquid.
    Returns (meta_list, asset_ctxs_list).
    """
    print(f"{Fore.CYAN}AI Pirate Terminator X fetching official Hyperliquid data...")

    try:
        response = requests.post(
            BASE_URL,
            headers=_auth_headers(),
            json={"type": "metaAndAssetCtxs"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        
        # Hyperliquid returns [meta_data, asset_ctxs]
        if isinstance(data, list) and len(data) >= 2:
            return data[0].get("universe", []), data[1]
        return [], []
    except Exception as e:
        print(f"{Fore.RED}Error fetching from HL: {e}")
        return [], []

def parse_hl_to_df(universe: list, asset_ctxs: list) -> pd.DataFrame:
    """
    Parse official HL data into a readable DataFrame.
    """
    rows = []
    for i, asset in enumerate(universe):
        # universe and asset_ctxs should match by index
        if i < len(asset_ctxs):
            name = asset.get("name")
            ctx = asset_ctxs[i]
            funding = float(ctx.get("funding", 0))
            oi = float(ctx.get("openInterest", 0))
            mark_price = float(ctx.get("markPx", 0))
            
            rows.append({
                "Symbol": name,
                "Rate %": funding * 100,  # HL uses decimals
                "Annualized %": funding * 100 * 24 * 365,
                "OI Value": oi * mark_price, # Calculate $ value
                "Mark Price": mark_price,
                "source": "official"
            })
    
    return pd.DataFrame(rows)

def display_top_bottom(df, label):
    """Show top 30 highest and top 30 lowest funding."""
    if df.empty:
        return

    # Sort
    df = df.sort_values("Rate %", ascending=False)
    display_cols = ["Symbol", "Rate %", "Annualized %", "OI Value", "Mark Price"]

    # OI filter
    before = len(df)
    df = df[df["OI Value"] >= MIN_OI_VALUE]
    print(f"{Fore.YELLOW}OI Filter ({label}): {before} -> {len(df)} assets (min OI: ${MIN_OI_VALUE:,.0f})")

    if df.empty:
        print(f"{Fore.YELLOW}No assets passed the OI filter.")
        return

    # Display formatting
    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", lambda x: f"{x:.6f}" if abs(x) < 0.1 else f"{x:,.2f}")

    # Top/bottom
    top_pos = df.head(30)
    top_neg = df.tail(30).sort_values("Rate %")

    # Output
    print(f"\n{Fore.GREEN}{'=' * 85}")
    print(f"{Fore.MAGENTA}AI Pirate Terminator X | {label} TOP 30 HIGHEST FUNDING")
    print(f"{Fore.GREEN}{'=' * 85}")
    print(top_pos[display_cols].to_string(index=False))

    print(f"\n{Fore.GREEN}{'=' * 85}")
    print(f"{Fore.MAGENTA}AI Pirate Terminator X | {label} TOP 30 MOST NEGATIVE FUNDING")
    print(f"{Fore.GREEN}{'=' * 85}")
    print(top_neg[display_cols].to_string(index=False))
    print(f"{Fore.GREEN}{'=' * 85}")

def scan():
    """Run one full funding rate scan."""
    print(f"\n{Fore.CYAN}{'=' * 95}")
    print(f"{Fore.YELLOW}AI Pirate Terminator X Funding Rate Scan | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.CYAN}{'=' * 95}")

    # Fetch and parse official HL data
    universe, asset_ctxs = fetch_hl_data()
    df = parse_hl_to_df(universe, asset_ctxs)

    if not df.empty:
        display_top_bottom(df, "ALL Hyperliquid")

    print(f"\n{Fore.YELLOW}Scan complete. Next scan in {LOOP_INTERVAL_SECONDS // 60}m")

if __name__ == "__main__":
    print(PIRATE_BANNER)
    print(f"{Fore.GREEN}AI Pirate Terminator X Funding Rate Scanner starting...")
    print(f"{Fore.YELLOW}Scanning every {LOOP_INTERVAL_SECONDS // 60} minutes.")

    scan()

    while True:
        time.sleep(LOOP_INTERVAL_SECONDS)
        scan()
