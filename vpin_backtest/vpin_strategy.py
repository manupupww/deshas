"""
VPIN-Based Bitcoin Trading Strategy
=====================================
Based on: "Bitcoin wild moves: Evidence from order flow toxicity and price jumps"
Authors: Kitvanitphasu, Kyaw, Likitapiwat, Treepongkaruna (ScienceDirect, 2026)
DOI: https://doi.org/10.1016/j.ribaf.2025.103163

Key Findings from the paper:
- VPIN (Volume-Synchronized Probability of Informed Trading) Granger-causes
  future Bitcoin price jumps.
- Positive serial correlation in both VPIN and jump size → momentum/herding.
- High VPIN = high order flow toxicity = impending price jump.

Strategy Adaptation (NO ML):
- Compute VPIN proxy from daily OHLCV using Bulk Volume Classification (BVC)
  method from Easley et al. (2012).
- Buy when VPIN exceeds threshold AND price is in uptrend (SMA filter).
- Exit when VPIN drops below exit threshold OR trailing stop hit.
"""

import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
from backtesting import Backtest, Strategy
from backtesting.lib import FractionalBacktest

# Suppress noisy warnings
warnings.filterwarnings("ignore", message=".*fractional.*")
warnings.filterwarnings("ignore", message=".*prices are larger.*")


# ───────────────────────────────────────────────────────
# Data Download
# ───────────────────────────────────────────────────────
def download_btc_data(start="2015-11-01", end="2024-08-31"):
    """Download BTC/USD daily data from Yahoo Finance."""
    print(f"📥 Downloading BTC-USD data from {start} to {end} ...")
    df = yf.download("BTC-USD", start=start, end=end, auto_adjust=True)

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)
    print(f"✅ Downloaded {len(df)} rows ({df.index[0].date()} → {df.index[-1].date()})")
    return df


# ───────────────────────────────────────────────────────
# VPIN Calculation Helper (Bulk Volume Classification)
# ───────────────────────────────────────────────────────
def compute_vpin_series(open_prices, close_prices, volume, n_buckets=16, vol_window=20):
    """
    Compute a VPIN proxy from daily OHLCV data using Bulk Volume Classification.

    Following Easley et al. (2012):
      buy_vol  = volume * Φ((close - open) / σ)
      sell_vol = volume - buy_vol
      OI       = |buy_vol - sell_vol|
      VPIN     = rolling_mean(OI / volume, n_buckets)

    Parameters:
    - n_buckets: Number of volume buckets for VPIN averaging (paper uses 16)
    - vol_window: Window for price change volatility estimation
    """
    o = pd.Series(open_prices)
    c = pd.Series(close_prices)
    v = pd.Series(volume)

    # Price change and its rolling std
    price_change = c - o
    sigma = price_change.rolling(vol_window).std()

    # Standardized price change
    z = price_change / sigma.replace(0, np.nan)

    # Bulk Volume Classification: buy probability via CDF
    buy_prob = pd.Series(norm.cdf(z.values), index=z.index)

    # Buy/Sell volume
    buy_vol = v * buy_prob
    sell_vol = v * (1 - buy_prob)

    # Order imbalance
    oi = (buy_vol - sell_vol).abs()

    # VPIN = rolling mean of (OI / V) over n_buckets
    vpin = (oi / v.replace(0, np.nan)).rolling(n_buckets).mean()

    return vpin.values


# ───────────────────────────────────────────────────────
# Strategy: VPIN Toxicity + Trend Filter
# ───────────────────────────────────────────────────────
class VPINStrategy(Strategy):
    """
    VPIN-based strategy:
    - Compute VPIN from daily volume imbalance (BVC method).
    - BUY when VPIN > entry threshold AND close > SMA (uptrend).
    - EXIT when VPIN < exit threshold OR trailing stop hit.

    Paper insight: High VPIN predicts future jumps.
    Direction filter: SMA trend determines expected jump direction.
    """
    n_buckets = 16          # VPIN averaging window (paper: 16 for 8h blocks)
    vol_window = 20         # Volatility estimation window
    vpin_entry = 0.60       # Enter when VPIN > this (high toxicity)
    vpin_exit = 0.40        # Exit when VPIN < this (toxicity drops)
    sma_period = 20         # SMA trend filter period
    trail_pct = 0.08        # 8% trailing stop

    def init(self):
        # VPIN indicator
        self.vpin = self.I(
            compute_vpin_series,
            self.data.Open,
            self.data.Close,
            self.data.Volume,
            self.n_buckets,
            self.vol_window,
            name=f"VPIN({self.n_buckets})"
        )

        # SMA trend filter
        self.sma = self.I(
            lambda c: pd.Series(c).rolling(self.sma_period).mean().values,
            self.data.Close,
            name=f"SMA({self.sma_period})"
        )

        # Trailing stop tracking
        self.highest_price = 0

    def next(self):
        price = self.data.Close[-1]
        vpin = self.vpin[-1]
        sma = self.sma[-1]

        if np.isnan(vpin) or np.isnan(sma):
            return

        if self.position:
            # Update trailing high
            if price > self.highest_price:
                self.highest_price = price

            # Exit conditions:
            # 1. VPIN drops below exit threshold (toxicity resolved)
            # 2. Trailing stop hit
            trail_stop = self.highest_price * (1 - self.trail_pct)
            if vpin < self.vpin_exit or price < trail_stop:
                self.position.close()
                self.highest_price = 0

        else:
            # Entry: High toxicity + uptrend
            if vpin > self.vpin_entry and price > sma:
                self.buy()
                self.highest_price = price


# ───────────────────────────────────────────────────────
# Runner (uses FractionalBacktest for BTC)
# ───────────────────────────────────────────────────────
def run_backtest(data, strategy_class, name, cash=100_000, commission=0.001):
    """Run a single backtest using FractionalBacktest for BTC."""
    print(f"\n{'='*60}")
    print(f"  📊 {name}")
    print(f"{'='*60}")

    bt = FractionalBacktest(
        data,
        strategy_class,
        cash=cash,
        commission=commission,
        exclusive_orders=True,
        trade_on_close=True,
        fractional_unit=1 / 1e6,  # Trade in μBTC
    )
    stats = bt.run()

    # Print key metrics
    print(f"  Return [%]:        {stats['Return [%]']:.2f}%")
    print(f"  Buy & Hold [%]:    {stats['Buy & Hold Return [%]']:.2f}%")
    print(f"  Max Drawdown [%]:  {stats['Max. Drawdown [%]']:.2f}%")
    sharpe = stats['Sharpe Ratio']
    print(f"  Sharpe Ratio:      {sharpe:.4f}" if not np.isnan(sharpe) else "  Sharpe Ratio:      N/A")
    print(f"  # Trades:          {stats['# Trades']}")
    print(f"  Win Rate [%]:      {stats['Win Rate [%]']:.2f}%")
    print(f"  Avg Trade [%]:     {stats['Avg. Trade [%]']:.2f}%")
    print(f"  Exposure [%]:      {stats['Exposure Time [%]']:.2f}%")

    # Save interactive HTML plot
    filename = f"{name.lower().replace(' ', '_').replace('(', '').replace(')', '')}.html"
    bt.plot(filename=filename, open_browser=False)
    print(f"  📈 Plot saved: {filename}")

    return stats, bt


def run_parameter_comparison(data):
    """Compare VPIN strategy across different parameter combinations."""
    print(f"\n{'='*60}")
    print(f"  📊 VPIN Strategy — Parameter Comparison")
    print(f"{'='*60}")
    print(f"  {'Buckets':>8} | {'Entry':>6} | {'SMA':>5} | {'Return %':>10} | {'MaxDD %':>10} | {'Sharpe':>8} | {'Trades':>8} | {'Win%':>8}")
    print(f"  {'-'*8}-+-{'-'*6}-+-{'-'*5}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")

    results = {}
    configs = [
        # n_buckets, vpin_entry, sma_period
        (10, 0.55, 15),
        (10, 0.60, 20),
        (16, 0.55, 15),
        (16, 0.55, 20),
        (16, 0.60, 20),
        (16, 0.60, 30),
        (16, 0.65, 20),
        (20, 0.55, 20),
        (20, 0.60, 20),
        (30, 0.55, 20),
        (30, 0.60, 20),
    ]

    for n_buckets, vpin_entry, sma_period in configs:
        bt = FractionalBacktest(
            data,
            VPINStrategy,
            cash=100_000,
            commission=0.001,
            exclusive_orders=True,
            trade_on_close=True,
            fractional_unit=1 / 1e6,
        )
        stats = bt.run(
            n_buckets=n_buckets,
            vpin_entry=vpin_entry,
            sma_period=sma_period,
        )

        sharpe = stats['Sharpe Ratio']
        sharpe_str = f"{sharpe:.4f}" if not np.isnan(sharpe) else "N/A"
        key = f"b{n_buckets}_e{vpin_entry}_s{sma_period}"
        print(f"  {n_buckets:>8} | {vpin_entry:>6.2f} | {sma_period:>5} | {stats['Return [%]']:>10.2f} | {stats['Max. Drawdown [%]']:>10.2f} | {sharpe_str:>8} | {stats['# Trades']:>8} | {stats['Win Rate [%]']:>7.1f}%")
        results[key] = stats

    return results


# ───────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────
if __name__ == "__main__":
    # Download data (matching paper period: Apr 2020 → Dec 2022 for paper,
    # but we extend to full BTC history for more robust testing)
    data = download_btc_data(start="2015-11-01", end="2024-08-31")

    # --- Run with default parameters ---
    stats, bt = run_backtest(data, VPINStrategy, "VPIN Toxicity Strategy")

    # --- Compare parameters ---
    print("\n\n" + "🔬" * 30)
    print("  PARAMETER COMPARISON")
    print("🔬" * 30)

    run_parameter_comparison(data)

    print("\n✅ All backtests complete! Open the .html files to see interactive charts.")
