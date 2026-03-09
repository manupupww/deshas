import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import scipy.stats as stats
import warnings
import os

warnings.filterwarnings('ignore')

# ─── DATA PREPARATION ────────────────────────────────────────────────────────

def load_and_prepare_data(file_path, aggregate_factor=1, merge_synthetic=True):
    """
    Loads Dollar Bars and aggregates them.
    Merges synthetic features using merge_asof.
    """
    print(f"Loading base data from {file_path}...")
    df = pd.read_csv(file_path, header=None)
    df.columns = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'DollarVolume']
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    if merge_synthetic:
        synthetic_dir = r"C:\Users\Mr. Perfect\tradingbot\data\synthetic"
        if os.path.exists(synthetic_dir):
            print(f"Merging synthetic features from {synthetic_dir}...")
            for filename in os.listdir(synthetic_dir):
                if filename.endswith(".csv"):
                    feature_name = filename.replace(".csv", "")
                    try:
                        feature_df = pd.read_csv(os.path.join(synthetic_dir, filename))
                        if 'timestamp' in feature_df.columns:
                            feature_df['timestamp'] = pd.to_datetime(feature_df['timestamp'], unit='ms')
                            feature_df = feature_df.sort_values('timestamp')
                            df = pd.merge_asof(df, feature_df[['timestamp', feature_name]], 
                                               on='timestamp', 
                                               direction='backward')
                            df[feature_name] = df[feature_name].ffill()
                    except Exception as e:
                        pass

    if aggregate_factor > 1:
        print(f"Aggregating by factor {aggregate_factor}...")
        df['group'] = np.arange(len(df)) // aggregate_factor
        agg_rules = {
            'timestamp': 'last', 'Open': 'first', 'High': 'max', 'Low': 'min', 
            'Close': 'last', 'Volume': 'sum', 'DollarVolume': 'sum'
        }
        for col in df.columns:
            if col not in agg_rules and col not in ['group']:
                agg_rules[col] = 'last'
        df = df.groupby('group').agg(agg_rules)

    df = df.set_index('timestamp')
    return df

# ─── HELPER MIXINS ──────────────────────────────────────────────────────────

class RiskManagementMixin:
    """
    Griežtas Rizikos Valdymas:
    - FIXED STOP LOSS: -20% (Niekada nejuda)
    - TRAILING TAKE PROFIT: Aktyvuojasi ties +3%, uždaro nukritus 2% nuo piko.
    """
    fixed_sl_pct = 0.20  
    tp_trail_activation = 0.03  
    tp_trail_callback = 0.02    

    def check_risk_management(self):
        if not self.position:
            self.peak_pnl = 0.0
            return

        current_pnl = self.position.pl_pct
        if not hasattr(self, 'peak_pnl'): self.peak_pnl = 0.0
        self.peak_pnl = max(self.peak_pnl, current_pnl)

        if current_pnl < -self.fixed_sl_pct:
            self.position.close()
            return

        if self.peak_pnl >= self.tp_trail_activation:
            if current_pnl < (self.peak_pnl - self.tp_trail_callback):
                self.position.close()

# ─── STRATEGIES (ORIGINAL VERSION) ──────────────────────────────────────────

class DollarBarStatsStrategy(Strategy, RiskManagementMixin):
    window = 30
    threshold = 2.0
    
    def init(self):
        self.peak_pnl = 0.0
        returns = pd.Series(self.data.Close).pct_change()
        self.z = self.I(lambda: (returns - returns.rolling(self.window).mean()) / returns.rolling(self.window).std())
        self.sma50 = self.I(lambda: pd.Series(self.data.Close).rolling(50).mean())

    def next(self):
        self.check_risk_management()
        is_uptrend = self.data.Close[-1] > self.sma50[-1] if not np.isnan(self.sma50[-1]) else True
        if not self.position:
            if self.z[-1] < -self.threshold and is_uptrend: self.buy()
            elif self.z[-1] > self.threshold and not is_uptrend: self.sell()
        elif self.position and abs(self.z[-1]) < 0.2:
            self.position.close()

class VPINStrategy(Strategy, RiskManagementMixin):
    vpin_window, vpin_threshold = 20, 0.6
    def init(self):
        self.peak_pnl = 0.0
        close, volume = pd.Series(self.data.Close), pd.Series(self.data.Volume)
        sigma = close.pct_change().rolling(self.vpin_window).std()
        buy_vol_pct = stats.norm.cdf((close.diff() / (close.shift(1) * sigma)).fillna(0))
        self.vpin = self.I(lambda: (volume * buy_vol_pct - volume * (1 - buy_vol_pct)).abs().rolling(self.vpin_window).sum() / (volume.rolling(self.vpin_window).sum()))
    def next(self):
        self.check_risk_management()
        if self.vpin[-1] > self.vpin_threshold and not self.position:
            if self.data.Close[-1] > self.data.Open[-1]: self.buy()
            else: self.sell()

class OFIStrategy(Strategy, RiskManagementMixin):
    ofi_window, threshold = 10, 1.0
    def init(self):
        self.peak_pnl = 0.0
        close, open_p, volume = pd.Series(self.data.Close), pd.Series(self.data.Open), pd.Series(self.data.Volume)
        range_hl = (pd.Series(self.data.High) - pd.Series(self.data.Low)).replace(0, 1e-9)
        net_vol = ((close - open_p) / range_hl) * volume
        self.ofi = self.I(lambda: net_vol.rolling(self.ofi_window).mean())
        self.ofi_std = self.I(lambda: net_vol.rolling(self.ofi_window).std())
    def next(self):
        self.check_risk_management()
        z = self.ofi[-1] / (self.ofi_std[-1] if self.ofi_std[-1] != 0 else 1)
        if not self.position:
            if z > self.threshold: self.buy()
            elif z < -self.threshold: self.sell()

class StructuralBreakStrategy(Strategy, RiskManagementMixin):
    lookback, std_devs = 30, 1.5
    def init(self):
        self.peak_pnl = 0.0
        durations = pd.Series(self.data.index).diff().dt.total_seconds().fillna(method='bfill')
        self.dur = self.I(lambda: durations)
        self.dur_ma = self.I(lambda: durations.rolling(self.lookback).mean())
        self.dur_std = self.I(lambda: durations.rolling(self.lookback).std())
    def next(self):
        self.check_risk_management()
        if self.dur[-1] < self.dur_ma[-1] - self.std_devs * self.dur_std[-1] and not self.position:
            if self.data.Close[-1] > self.data.Close[-2]: self.buy()
            else: self.sell()

class VWAPReversionStrategy(Strategy, RiskManagementMixin):
    window, sigma = 50, 2.0
    def init(self):
        self.peak_pnl = 0.0
        close, vol = pd.Series(self.data.Close), pd.Series(self.data.Volume)
        self.vwap = self.I(lambda: (close * vol).rolling(self.window).sum() / vol.rolling(self.window).sum())
        self.std = self.I(lambda: close.rolling(self.window).std())
        self.sma200 = self.I(lambda: close.rolling(200).mean())
    def next(self):
        self.check_risk_management()
        price, vwap = self.data.Close[-1], self.vwap[-1]
        upper, lower = vwap + self.sigma * self.std[-1], vwap - self.sigma * self.std[-1]
        is_uptrend = price > self.sma200[-1] if not np.isnan(self.sma200[-1]) else True
        if not self.position:
            if price < lower and is_uptrend: self.buy()
            elif price > upper and not is_uptrend: self.sell()
        elif self.position and ((self.position.is_long and price >= vwap) or (self.position.is_short and price <= vwap)):
            self.position.close()

class MarketIntensityStrategy(Strategy, RiskManagementMixin):
    lookback = 30
    def init(self):
        self.peak_pnl = 0.0
        durations = pd.Series(self.data.index).diff().dt.total_seconds().fillna(1e-9).replace(0, 1e-9)
        intensity = pd.Series(self.data.Volume) / durations
        self.intensity = self.I(lambda: intensity)
        self.intensity_ma = self.I(lambda: intensity.rolling(self.lookback).mean())
        self.intensity_std = self.I(lambda: intensity.rolling(self.lookback).std())
    def next(self):
        self.check_risk_management()
        if self.intensity[-1] > self.intensity_ma[-1] + self.intensity_std[-1] and not self.position:
            if self.data.Close[-1] > self.data.Open[-1]: self.buy()
            else: self.sell()

class DollarMomentumStrategy(Strategy, RiskManagementMixin):
    fast, slow = 10, 30
    def init(self):
        self.peak_pnl = 0.0
        close = pd.Series(self.data.Close)
        self.fast_ma, self.slow_ma = self.I(lambda: close.rolling(self.fast).mean()), self.I(lambda: close.rolling(self.slow).mean())
    def next(self):
        self.check_risk_management()
        if not self.position:
            if self.fast_ma[-1] > self.slow_ma[-1]: self.buy()
        elif self.position and self.fast_ma[-1] < self.slow_ma[-1]:
            self.position.close()

class SyntheticFlowStrategy(Strategy, RiskManagementMixin):
    fund_t, liq_std = 0.0001, 1.5
    def init(self):
        self.peak_pnl = 0.0
        f, l = pd.Series(getattr(self.data, 'btc_funding_rates', np.zeros(len(self.data)))), pd.Series(getattr(self.data, 'btc_long_liquidations', np.zeros(len(self.data))))
        self.funding, self.liqs = self.I(lambda: f), self.I(lambda: l)
        self.l_ma, self.l_std = self.I(lambda: l.rolling(30).mean()), self.I(lambda: l.rolling(30).std())
    def next(self):
        self.check_risk_management()
        if not self.position:
            if self.funding[-1] < -self.fund_t: self.buy()
            if self.liqs[-1] > self.l_ma[-1] + self.liq_std * self.l_std[-1]: self.buy()
        elif self.position and self.position.is_long and self.funding[-1] > self.fund_t:
            self.position.close()
