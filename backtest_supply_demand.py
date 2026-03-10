import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import sys

# Load custom configuration from the main script conceptually
symbol = "BTC"
timeframe = "DollarBars"
leverage = 20
stop_loss_pct = 5.0
target_pnl = 3.0
trail_activation_pnl = 3.0
trail_distance_pct = 1.0
max_loss_pnl = -3.0
max_true_range = 500.0  
extended_multiplier = 1.5
bar_lookback = 100
sma_period = 200
sd_cluster_bars = 5
displacement_multiplier = 1.5

class SupplyDemandStrategy(Strategy):
    def init(self):
        # Tracking peak PnL for trailing take-profit
        self.peak_pnl = 0.0
        self.touched_demand = False
        self.touched_supply = False
        
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        
        prev_close = close.shift(1)
        high_low = (high - low).abs()
        high_pc = (high - prev_close).abs()
        low_pc = (low - prev_close).abs()
        tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
        
        self.sma = self.I(lambda x: pd.Series(x).rolling(sma_period).mean(), close)
        self.rolling_max_tr = self.I(lambda x: pd.Series(x).rolling(84).max(), tr)

    def next(self):
        required_bars = int(max(bar_lookback * extended_multiplier, sma_period + 5))
        if len(self.data.Close) < required_bars:
            return
            
        current_price = self.data.Close[-1]
        trend_up = current_price > self.sma[-1]
        size_pct = 0.2

        # 1. Manage existing positions (Trailing PnL check)
        if self.position:
            # Pnl% = (raw_change %) * leverage * 100
            levaraged_pnl_pct = self.position.pl_pct * 100 * leverage
            self.peak_pnl = max(self.peak_pnl, levaraged_pnl_pct)

            # Trailing logic if activation reached
            if self.peak_pnl >= trail_activation_pnl:
                if levaraged_pnl_pct <= (self.peak_pnl - trail_distance_pct):
                    self.position.close()
                    self.peak_pnl = 0.0
                    return
            
            # Hard stop (max loss)
            if levaraged_pnl_pct <= max_loss_pnl:
                self.position.close()
                self.peak_pnl = 0.0
                return
            
            return
        else:
            self.peak_pnl = 0.0
            
        # ── Safety checks ────────────────────────────────────
        # Skip if TR in the last 7 hours exceeded max_true_range (from bot logic)
        if self.rolling_max_tr[-1] > max_true_range:
            return
            
        # ── Zone Calculations ────────────────────────────────────
        # Last bars high/low (extended)
        ext_high = np.max(self.data.High[-int(bar_lookback * extended_multiplier):])
        ext_low = np.min(self.data.Low[-int(bar_lookback * extended_multiplier):])
        
        # Cluster of bars for supply/demand zones (more stable than 2 bars)
        cluster_high = self.data.High[-sd_cluster_bars:]
        cluster_low = self.data.Low[-sd_cluster_bars:]
        cluster_close = self.data.Close[-sd_cluster_bars:]
        
        support_close = np.min(cluster_close)
        resistance_close = np.max(cluster_close)
        wick_low = np.min(cluster_low)
        wick_high = np.max(cluster_high)
        
        # Displacement Check: Was the move away from this area explosive?
        # Check last 20 bars for any bar range > 1.5x ATR
        tr_recent = pd.Series(self.data.High - self.data.Low).tail(20)
        atr_recent = tr_recent.rolling(14).mean().iloc[-1]
        displacement_found = any(tr_recent > atr_recent * displacement_multiplier)
        
        if not displacement_found:
            return

        # ── Rejection Trigger Logic ──────────────────────────────
        # Demand Zone Trigger (Long)
        if trend_up:
            # 1. Check for touch (Current High/Low hit the zone)
            if self.data.Low[-1] <= support_close and self.data.High[-1] >= wick_low:
                self.touched_demand = True
            
            # 2. Check for rejection (Close out of zone)
            if self.touched_demand and current_price > support_close:
                sl_val = support_close * (1 - (stop_loss_pct / 100))
                # TP at 1:1.5 RR for higher win rate
                tp_val = current_price * (1 + (target_pnl / 100))
                self.buy(size=size_pct, sl=sl_val, tp=tp_val)
                self.touched_demand = False
            
            # 3. Fail safe
            if current_price < wick_low:
                self.touched_demand = False
        else:
            # Supply Zone Trigger (Short)
            # 1. Check for touch
            if self.data.High[-1] >= resistance_close and self.data.Low[-1] <= wick_high:
                self.touched_supply = True
            
            # 2. Check for rejection
            if self.touched_supply and current_price < resistance_close:
                sl_val = resistance_close * (1 + (stop_loss_pct / 100))
                tp_val = current_price * (1 - (target_pnl / 100))
                self.sell(size=size_pct, sl=sl_val, tp=tp_val)
                self.touched_supply = False
            
            # 3. Fail safe
            if current_price > wick_high:
                self.touched_supply = False

def run_backtest():
    import warnings
    warnings.filterwarnings('ignore')
    
    print("Loading data...")
    # Load data
    df = pd.read_csv(r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020-2025dollarBars_.csv", header=None)
    
    # Dollar Bar format: 2020-01-01 00:00:01.481,7189.43,7239.74,7170.15,7216.24,13871.046,100004248.88
    # Map columns manually
    df.columns = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'DollarVolume']
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # Run on a recent slice to save time
    df = df.loc["2024-01-01":"2024-12-31"]
    print(f"Running backtest on {len(df)} rows from {df.index[0]} to {df.index[-1]}")
    
    # We use margin to simulate leverage in backtesting
    margin_ratio = 1 / leverage
    
    # Exclusive trades only (buy closes sell, missing feature in code above maybe?),
    # backtesting.py by default uses FIFO and handles opposites well.
    bt = Backtest(df, SupplyDemandStrategy, cash=10000, margin=margin_ratio, commission=0.0005, trade_on_close=False, exclusive_orders=False)
    
    stats = bt.run()
    
    print("\n=== Backtest Results ===")
    print(stats)
    
    # Save the plot
    try:
        plot_path = r"C:\Users\Mr. Perfect\tradingbot\SupplyDemand_backtest_plot.html"
        bt.plot(filename=plot_path, open_browser=False)
        print(f"\nPlot saved to {plot_path}")
    except Exception as e:
        print(f"Failed to generate plot: {e}")

if __name__ == '__main__':
    run_backtest()
