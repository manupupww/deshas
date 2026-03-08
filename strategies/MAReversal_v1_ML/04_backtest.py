"""
04_backtest.py - AFML-Grade Backtest with Meta-Labeling Bet Sizing
==================================================================
Compares two modes:
  A) BASELINE: Raw MA signals (original Moon Dev strategy)
  B) ML RISK MANAGED: MA signals filtered + sized by Meta-Model

AFML Role: Chapter 10 (Bet Sizing) + Chapter 14 (Backtest Statistics)
"""
import pandas as pd
import numpy as np
import os
import joblib
from backtesting import Backtest, Strategy

# ============================================================
# Strategy A: Baseline (Original MA Reversal - no ML)
# ============================================================
class MAReversalBaseline(Strategy):
    ma_fast = 20
    ma_slow = 40
    take_profit = 0.10
    stop_loss = 0.10

    def init(self):
        close = pd.Series(self.data.Close)
        self.sma_fast = self.I(lambda: close.rolling(self.ma_fast).mean().values)
        self.sma_slow = self.I(lambda: close.rolling(self.ma_slow).mean().values)

    def next(self):
        price = self.data.Close[-1]
        if np.isnan(self.sma_fast[-1]) or np.isnan(self.sma_slow[-1]):
            return

        # Short: price > SMA_fast but < SMA_slow
        if price > self.sma_fast[-1] and price < self.sma_slow[-1] and not self.position:
            self.sell(sl=price * (1 + self.stop_loss), tp=price * (1 - self.take_profit))
        # Long: price > both SMAs
        elif price > self.sma_fast[-1] and price > self.sma_slow[-1] and not self.position:
            self.buy(sl=price * (1 - self.stop_loss), tp=price * (1 + self.take_profit))
        # Close short if price > SMA_slow
        elif self.position and self.position.is_short and price > self.sma_slow[-1]:
            self.position.close()


# ============================================================
# Strategy B: ML Risk Managed (MA + Meta-Model Bet Sizing)
# ============================================================
class MAReversalML(Strategy):
    ma_fast = 20
    ma_slow = 40
    take_profit = 0.10
    stop_loss = 0.10
    confidence_threshold = 0.55  # Only trade if Meta-Model > 55%
    
    # These will be set externally
    meta_model = None
    
    def init(self):
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        self.sma_fast = self.I(lambda: close.rolling(self.ma_fast).mean().values)
        self.sma_slow = self.I(lambda: close.rolling(self.ma_slow).mean().values)
        self.close_series = close
        self.volume_series = volume

    def _get_meta_features(self, signal):
        """Build feature vector for Meta-Model prediction."""
        idx = len(self.data.Close) - 1
        if idx < 50:
            return None
            
        close = self.close_series.iloc[:idx+1]
        vol = self.volume_series.iloc[:idx+1]
        
        price = close.iloc[-1]
        sma_f = self.sma_fast[-1]
        sma_s = self.sma_slow[-1]
        
        volatility = close.pct_change().rolling(50).std().iloc[-1]
        if np.isnan(volatility) or volatility == 0:
            return None
        
        vol_5 = close.pct_change().rolling(5).std().iloc[-1]
        vol_20 = close.pct_change().rolling(20).std().iloc[-1]
        vol_sma = vol.rolling(20).mean().iloc[-1]
        
        features = np.array([[
            signal,
            volatility,
            (price - sma_f) / price if price > 0 else 0,
            (price - sma_s) / price if price > 0 else 0,
            close.pct_change(5).iloc[-1] if not np.isnan(close.pct_change(5).iloc[-1]) else 0,
            close.pct_change(10).iloc[-1] if not np.isnan(close.pct_change(10).iloc[-1]) else 0,
            close.pct_change(20).iloc[-1] if not np.isnan(close.pct_change(20).iloc[-1]) else 0,
            vol_5 / vol_20 if vol_20 > 0 else 1,
            vol.iloc[-1] / vol_sma if vol_sma > 0 else 1,
        ]])
        
        return np.nan_to_num(features, nan=0.0)

    def next(self):
        price = self.data.Close[-1]
        if np.isnan(self.sma_fast[-1]) or np.isnan(self.sma_slow[-1]):
            return
        if self.meta_model is None:
            return

        signal = 0
        # Short signal
        if price > self.sma_fast[-1] and price < self.sma_slow[-1] and not self.position:
            signal = -1
        # Long signal
        elif price > self.sma_fast[-1] and price > self.sma_slow[-1] and not self.position:
            signal = 1
        # Close short
        elif self.position and self.position.is_short and price > self.sma_slow[-1]:
            self.position.close()
            return
        
        if signal == 0:
            return
            
        # === META-MODEL FILTER ===
        features = self._get_meta_features(signal)
        if features is None:
            return
            
        probability = self.meta_model.predict_proba(features)[0][1]
        
        # Only trade if confidence exceeds threshold
        if probability < self.confidence_threshold:
            return
        
        # === BET SIZING (Kelly-inspired) ===
        # Size proportional to confidence: higher confidence = larger position
        base_size = 0.1  # 10% base allocation
        kelly_fraction = max(0, (probability - 0.5) * 2)  # Scale 0.5-1.0 -> 0-1
        size_pct = base_size * (0.5 + kelly_fraction * 0.5)  # 5% to 10%
        size_units = int(max(1, (self.equity * size_pct) / price))
        
        if signal == 1:
            self.buy(size=size_units,
                     sl=price * (1 - self.stop_loss),
                     tp=price * (1 + self.take_profit))
        elif signal == -1:
            self.sell(size=size_units,
                      sl=price * (1 + self.stop_loss),
                      tp=price * (1 - self.take_profit))


def calculate_dsr(sharpe, n_trials, skew=0, kurtosis=3):
    """
    Deflated Sharpe Ratio (AFML Chapter 14).
    Accounts for multiple testing bias.
    """
    from scipy.stats import norm
    
    if n_trials <= 1:
        return sharpe
    
    # Expected max Sharpe under null hypothesis
    e_max_sr = norm.ppf(1 - 1/n_trials) * np.sqrt(1 + (skew * sharpe) + ((kurtosis - 3)/4) * sharpe**2)
    
    # DSR: probability that observed Sharpe > expected max
    dsr = norm.cdf((sharpe - e_max_sr) / np.sqrt(1 + (skew * sharpe) + ((kurtosis - 3)/4) * sharpe**2))
    return dsr


if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load data
    data_path = os.path.join(output_dir, "signals_with_ma.csv")
    if not os.path.exists(data_path):
        data_path = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020_2022_dollar_bars.csv"
        print(f"Using fallback data: {data_path}")
    
    df = pd.read_csv(data_path, parse_dates=[0], index_col=0)
    col_map = {c: c.capitalize() for c in df.columns}
    df.rename(columns=col_map, inplace=True)
    
    # Ensure required columns exist
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col not in df.columns:
            print(f"ERROR: Missing column '{col}'. Available: {list(df.columns)}")
            exit(1)
    
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    
    # ========================
    # A) BASELINE Backtest
    # ========================
    print("=" * 60)
    print("  BASELINE: Raw MA Reversal (No ML)")
    print("=" * 60)
    bt_baseline = Backtest(df, MAReversalBaseline, cash=1_000_000, commission=0.002)
    stats_baseline = bt_baseline.run()
    print(stats_baseline)
    bt_baseline.plot(filename=os.path.join(output_dir, "baseline_results.html"), open_browser=False)
    
    # ========================
    # B) ML RISK MANAGED Backtest
    # ========================
    model_path = os.path.join(output_dir, "meta_model.pkl")
    if os.path.exists(model_path):
        print("\n" + "=" * 60)
        print("  ML RISK MANAGED: MA + Meta-Model Bet Sizing")
        print("=" * 60)
        
        meta_model = joblib.load(model_path)
        MAReversalML.meta_model = meta_model
        
        bt_ml = Backtest(df, MAReversalML, cash=1_000_000, commission=0.002)
        stats_ml = bt_ml.run()
        print(stats_ml)
        bt_ml.plot(filename=os.path.join(output_dir, "ml_risk_results.html"), open_browser=False)
        
        # ========================
        # C) COMPARISON
        # ========================
        print("\n" + "=" * 60)
        print("  COMPARISON: Baseline vs ML Risk Managed")
        print("=" * 60)
        comparison = pd.DataFrame({
            'Baseline': [
                stats_baseline['Return [%]'],
                stats_baseline['Sharpe Ratio'],
                stats_baseline['Max. Drawdown [%]'],
                stats_baseline['# Trades'],
                stats_baseline['Win Rate [%]'],
                stats_baseline['Exposure Time [%]'],
            ],
            'ML Risk Managed': [
                stats_ml['Return [%]'],
                stats_ml['Sharpe Ratio'],
                stats_ml['Max. Drawdown [%]'],
                stats_ml['# Trades'],
                stats_ml['Win Rate [%]'],
                stats_ml['Exposure Time [%]'],
            ]
        }, index=['Return %', 'Sharpe Ratio', 'Max Drawdown %', '# Trades', 'Win Rate %', 'Exposure %'])
        print(comparison.to_string())
        
        # DSR Check
        print("\n--- Deflated Sharpe Ratio (DSR) ---")
        n_trials = 2  # We only ran 2 strategies
        for name, sr in [('Baseline', stats_baseline['Sharpe Ratio']), ('ML', stats_ml['Sharpe Ratio'])]:
            if sr and not np.isnan(sr):
                dsr = calculate_dsr(sr, n_trials)
                status = "PASS" if dsr > 0.95 else "FAIL"
                print(f"  {name}: Sharpe={sr:.3f}, DSR={dsr:.4f} [{status}]")
    else:
        print(f"\nMeta-model not found at {model_path}. Run 03_meta_labeling.py first.")
        print("Only baseline results available.")
    
    print("\nBacktest complete. Results saved to", output_dir)
