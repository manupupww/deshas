"""
VPIN-Based Bitcoin Trading Strategy (Dollar Bars Version)
===========================================================
Based on: "Bitcoin wild moves: Evidence from order flow toxicity and price jumps"
Uses local Dollar Bars data for higher precision and volume-synchronized analysis.
"""

import os
import warnings
import numpy as np
import pandas as pd
from scipy.stats import norm
from backtesting import Backtest, Strategy
from backtesting.lib import FractionalBacktest

# Suppress noisy warnings
warnings.filterwarnings("ignore", message=".*fractional.*")
warnings.filterwarnings("ignore", message=".*prices are larger.*")

# ───────────────────────────────────────────────────────
# Data Loading (Local Dollar Bars)
# ───────────────────────────────────────────────────────
def load_dollar_bars(filepath):
    """Load BTC/USDT dollar bars from local CSV."""
    print(f"--- Loading Dollar Bars from {filepath} ---")
    
    # Headerless CSV based on inspection:
    # Timestamp, Open, High, Low, Close, Volume, DollarVolume
    df = pd.read_csv(filepath)
    
    # Map common column names to what backtesting needs
    rename_map = {
        'timestamp': 'Timestamp',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume',
        'dollar_volume': 'DollarVolume'
    }
    df.rename(columns=rename_map, inplace=True)
    
    # Convert to datetime and set index
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df.set_index('Timestamp', inplace=True)
    
    # backtesting.py requirements
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)
    
    print(f"LOADED {len(df)} bars ({df.index[0].date()} -> {df.index[-1].date()})")
    return df

# ───────────────────────────────────────────────────────
# VPIN Calculation (BVC Method)
# ───────────────────────────────────────────────────────
def compute_vpin_series(open_prices, close_prices, volume, n_buckets=16, vol_window=50):
    """
    Compute VPIN from OHLCV data. 
    On dollar bars, this is naturally more synchronous with volume.
    """
    o = pd.Series(open_prices)
    c = pd.Series(close_prices)
    v = pd.Series(volume)

    price_change = c - o
    sigma = price_change.rolling(vol_window).std()
    z = price_change / sigma.replace(0, np.nan)
    
    buy_prob = pd.Series(norm.cdf(z.values), index=z.index)
    buy_vol = v * buy_prob
    sell_vol = v * (1 - buy_prob)
    
    oi = (buy_vol - sell_vol).abs()
    vpin = (oi / v.replace(0, np.nan)).rolling(n_buckets).mean()
    return vpin.values

# ───────────────────────────────────────────────────────
# Strategy
# ───────────────────────────────────────────────────────
class VPINStrategy(Strategy):
    n_buckets = 25          # VPIN lookback
    vol_window = 100        # Volatility window
    vpin_entry = 0.65       # High toxicity entry
    vpin_exit = 0.45        # Toxicity drop exit
    sma_period = 100        # Trend filter (longer for intra-day bars)
    trail_pct = 0.05        # 5% trailing stop

    def init(self):
        self.vpin = self.I(
            compute_vpin_series,
            self.data.Open, self.data.Close, self.data.Volume,
            self.n_buckets, self.vol_window,
            name="VPIN"
        )
        self.sma = self.I(
            lambda c: pd.Series(c).rolling(self.sma_period).mean().values,
            self.data.Close,
            name="SMA"
        )
        self.highest_price = 0

    def next(self):
        price = self.data.Close[-1]
        vpin = self.vpin[-1]
        sma = self.sma[-1]

        if np.isnan(vpin) or np.isnan(sma):
            return

        if self.position:
            if price > self.highest_price:
                self.highest_price = price
            
            trail_stop = self.highest_price * (1 - self.trail_pct)
            if vpin < self.vpin_exit or price < trail_stop:
                self.position.close()
                self.highest_price = 0
        else:
            if vpin > self.vpin_entry and price > sma:
                self.buy()
                self.highest_price = price

# ───────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────
if __name__ == "__main__":
    csv_path = r"c:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020-2025dollarBars_.csv"
    data = load_dollar_bars(csv_path)

    bt = FractionalBacktest(
        data,
        VPINStrategy,
        cash=100_000,
        commission=0.001,
        exclusive_orders=True,
        trade_on_close=True,
        fractional_unit=1 / 1e6,
    )
    
    print("RUNNING VPIN Backtest on Dollar Bars...")
    stats = bt.run()
    
    print(f"\n{'='*40}\n RESULTS\n{'='*40}")
    print(f"Return [%]:        {stats['Return [%]']:.2f}%")
    print(f"Sharpe Ratio:      {stats['Sharpe Ratio']:.4f}")
    print(f"Max Drawdown [%]:  {stats['Max. Drawdown [%]']:.2f}%")
    print(f"# Trades:          {stats['# Trades']}")
    print(f"Win Rate [%]:      {stats['Win Rate [%]']:.2f}%")
    
    bt.plot(filename="vpin_dollar_bars.html", open_browser=False)
    print("PLOT SAVED: vpin_dollar_bars.html")

