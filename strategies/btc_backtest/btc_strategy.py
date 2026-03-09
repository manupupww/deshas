"""
BTC Trend-Following & Mean-Reversion Strategies
================================================
Based on: "Revisiting Trend-following and Mean-Reversion Strategies in Bitcoin"
Authors: Soňa Beluská & Radovan Vojtko (Quantpedia, 2024)
SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4955617

Strategy Rules (NO ML):
- MAX (Trend-Following): Buy when BTC price == N-day high
- MIN (Mean-Reversion):  Buy when BTC price == N-day low  
- MIN+MAX (Combined):    Buy when price hits either N-day high OR N-day low
- Default lookback: 10 days (best performer in paper)
"""

import warnings
import numpy as np
import pandas as pd
import yfinance as yf
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

    # backtesting.py requires these exact column names
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)
    print(f"✅ Downloaded {len(df)} rows ({df.index[0].date()} → {df.index[-1].date()})")
    return df


# ───────────────────────────────────────────────────────
# Strategy 1: MAX (Trend-Following)
# ───────────────────────────────────────────────────────
class MaxStrategy(Strategy):
    """
    Trend-Following: Buy BTC when today's close reaches the N-day maximum.
    Hold for `hold_days` days, then sell.
    """
    lookback = 10
    hold_days = 10

    def init(self):
        self.rolling_max = self.I(
            lambda c: pd.Series(c).rolling(self.lookback).max().values,
            self.data.Close,
            name=f"{self.lookback}d MAX"
        )
        self.entry_bar = 0

    def next(self):
        price = self.data.Close[-1]
        rolling_max = self.rolling_max[-1]

        if self.position:
            bars_held = len(self.data) - self.entry_bar
            if bars_held >= self.hold_days:
                self.position.close()
        else:
            if not np.isnan(rolling_max) and price >= rolling_max:
                self.buy()
                self.entry_bar = len(self.data)


# ───────────────────────────────────────────────────────
# Strategy 2: MIN (Mean-Reversion)
# ───────────────────────────────────────────────────────
class MinStrategy(Strategy):
    """
    Mean-Reversion: Buy BTC when today's close reaches the N-day minimum.
    Hold for `hold_days` days, then sell.
    """
    lookback = 10
    hold_days = 10

    def init(self):
        self.rolling_min = self.I(
            lambda c: pd.Series(c).rolling(self.lookback).min().values,
            self.data.Close,
            name=f"{self.lookback}d MIN"
        )
        self.entry_bar = 0

    def next(self):
        price = self.data.Close[-1]
        rolling_min = self.rolling_min[-1]

        if self.position:
            bars_held = len(self.data) - self.entry_bar
            if bars_held >= self.hold_days:
                self.position.close()
        else:
            if not np.isnan(rolling_min) and price <= rolling_min:
                self.buy()
                self.entry_bar = len(self.data)


# ───────────────────────────────────────────────────────
# Strategy 3: MIN+MAX Combined
# ───────────────────────────────────────────────────────
class MinMaxStrategy(Strategy):
    """
    Combined: Buy BTC when today's close reaches either the N-day MAX or N-day MIN.
    Hold for `hold_days` days, then sell.
    """
    lookback = 10
    hold_days = 10

    def init(self):
        self.rolling_max = self.I(
            lambda c: pd.Series(c).rolling(self.lookback).max().values,
            self.data.Close,
            name=f"{self.lookback}d MAX"
        )
        self.rolling_min = self.I(
            lambda c: pd.Series(c).rolling(self.lookback).min().values,
            self.data.Close,
            name=f"{self.lookback}d MIN"
        )
        self.entry_bar = 0

    def next(self):
        price = self.data.Close[-1]
        rolling_max = self.rolling_max[-1]
        rolling_min = self.rolling_min[-1]

        if self.position:
            bars_held = len(self.data) - self.entry_bar
            if bars_held >= self.hold_days:
                self.position.close()
        else:
            if not np.isnan(rolling_max) and not np.isnan(rolling_min):
                if price >= rolling_max or price <= rolling_min:
                    self.buy()
                    self.entry_bar = len(self.data)


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
    filename = f"{name.lower().replace(' ', '_').replace('+', 'plus').replace('(', '').replace(')', '')}.html"
    bt.plot(filename=filename, open_browser=False)
    print(f"  📈 Plot saved: {filename}")

    return stats


def run_lookback_comparison(data, strategy_class, name, lookbacks=[10, 20, 30, 40, 50]):
    """Run backtest across multiple lookback periods."""
    print(f"\n{'='*60}")
    print(f"  📊 {name} — Lookback Comparison")
    print(f"{'='*60}")
    print(f"  {'Lookback':>10} | {'Return %':>10} | {'MaxDD %':>10} | {'Sharpe':>8} | {'Trades':>8} | {'Win%':>8}")
    print(f"  {'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")

    results = {}
    for lb in lookbacks:
        bt = FractionalBacktest(
            data,
            strategy_class,
            cash=100_000,
            commission=0.001,
            exclusive_orders=True,
            trade_on_close=True,
            fractional_unit=1 / 1e6,
        )
        stats = bt.run(lookback=lb, hold_days=lb)

        sharpe = stats['Sharpe Ratio']
        sharpe_str = f"{sharpe:.4f}" if not np.isnan(sharpe) else "N/A"
        print(f"  {lb:>10} | {stats['Return [%]']:>10.2f} | {stats['Max. Drawdown [%]']:>10.2f} | {sharpe_str:>8} | {stats['# Trades']:>8} | {stats['Win Rate [%]']:>7.1f}%")
        results[lb] = stats

    return results


# ───────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────
if __name__ == "__main__":
    # Download data (matching paper period: Nov 2015 → Aug 2024)
    data = download_btc_data(start="2015-11-01", end="2024-08-31")

    # --- Run each strategy with default 10-day lookback ---
    max_stats = run_backtest(data, MaxStrategy, "MAX Strategy (Trend-Following)")
    min_stats = run_backtest(data, MinStrategy, "MIN Strategy (Mean-Reversion)")
    minmax_stats = run_backtest(data, MinMaxStrategy, "MIN+MAX Combined Strategy")

    # --- Compare lookback periods for each strategy ---
    print("\n\n" + "🔬" * 30)
    print("  LOOKBACK PERIOD COMPARISON")
    print("🔬" * 30)

    run_lookback_comparison(data, MaxStrategy, "MAX Strategy")
    run_lookback_comparison(data, MinStrategy, "MIN Strategy")
    run_lookback_comparison(data, MinMaxStrategy, "MIN+MAX Strategy")

    print("\n✅ All backtests complete! Open the .html files in your browser to see interactive charts.")
