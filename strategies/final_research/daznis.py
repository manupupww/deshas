import pandas as pd
import numpy as np
import os
import sys
from sklearn.ensemble import RandomForestClassifier

# Pridedame backtesting-py
sys.path.append(os.path.abspath('backtesting-py'))
try:
    from backtesting import Backtest, Strategy
except ImportError:
    print("Klaida: Nepavyko rasti 'backtesting' bibliotekos.")
    sys.exit(1)

# --- ML RISK ENGINE (Mokomas atpažinti visas panikas) ---
def train_risk_engine(df):
    print("AI mokosi valdyti riziką visoje rinkoje...")
    data = df.copy()
    data['atr'] = (data['high'] - data['low']).rolling(14).mean()
    data['vol_z'] = (data['volume'] - data['volume'].rolling(50).mean()) / (data['volume'].rolling(50).std() + 1e-9)
    data['liq_total'] = data['long_liquidations'] + data['short_liquidations']
    
    horizon = 24
    targets = []
    closes = data['close'].values
    for i in range(len(closes) - horizon):
        entry = closes[i]
        future = closes[i+1 : i+1+horizon]
        is_loss = 1
        for p in future:
            if p <= entry * 0.99: break # SL 1%
            if p >= entry * 1.015: is_loss = 0; break # TP 1.5%
        targets.append(is_loss)
    
    df_ml = data.iloc[:len(targets)].copy()
    df_ml['is_loss'] = targets
    features = ['atr', 'vol_z', 'liq_total']
    
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(df_ml[features].dropna(), df_ml.loc[df_ml[features].dropna().index, 'is_loss'])
    return model, features

class HighFreqMLRiskStrategy(Strategy):
    risk_model = None
    risk_features = []

    def init(self):
        self.entry_p = 0
        self.highest_p = 0
        self.current_sl = 0
        self.long_liq_avg = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.long_liquidations)
        self.short_liq_avg = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.short_liquidations)

    def next(self):
        price = self.data.Close[-1]
        
        # Trailing Stop valdymas
        if self.position:
            if self.position.is_long:
                self.highest_p = max(self.highest_p, price)
                if (price / self.entry_p - 1) > 0.003:
                    new_sl = self.highest_p * 0.995
                    if new_sl > self.current_sl: self.current_sl = new_sl
                if price <= self.current_sl: self.position.close()
            elif self.position.is_short:
                self.lowest_p = min(self.lowest_p, price)
                if (self.entry_p / price - 1) > 0.003:
                    new_sl = self.lowest_p * 1.005
                    if self.current_sl == 0 or new_sl < self.current_sl: self.current_sl = new_sl
                if price >= self.current_sl: self.position.close()
            return

        # --- DINAMINIS TRIGERIS (BE MAGNETŲ) ---
        long_liq_spike = self.data.long_liquidations[-1] > (self.long_liq_avg[-1] * 2.5)
        short_liq_spike = self.data.short_liquidations[-1] > (self.short_liq_avg[-1] * 2.5)

        if long_liq_spike or short_liq_spike:
            try:
                atr = self.data.High[-1] - self.data.Low[-1]
                vol_z = 0
                liq = self.data.long_liquidations[-1] + self.data.short_liquidations[-1]
                
                state = [[atr, vol_z, liq]]
                loss_prob = self.risk_model.predict_proba(state)[0][1]
                
                # ML Filtruojame pagal sėkmės tikimybę
                if loss_prob > 0.50: return
                
                if long_liq_spike:
                    self.entry_p, self.highest_p, self.current_sl = price, price, price * 0.99
                    self.buy()
                else:
                    self.entry_p, self.lowest_p, self.current_sl = price, price, price * 1.01
                    self.sell()
            except: pass

def run_high_freq_ml_risk():
    df = pd.read_csv('data/BTC_15min_parallel.csv')
    df.columns = df.columns.str.lower()
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df.dropna(inplace=True)
    
    model, f_cols = train_risk_engine(df)
    
    df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'}, inplace=True)
    HighFreqMLRiskStrategy.risk_model = model
    HighFreqMLRiskStrategy.risk_features = f_cols
    
    bt = Backtest(df, HighFreqMLRiskStrategy, cash=100000, commission=0.0, margin=0.05)
    print(bt.run())

if __name__ == "__main__":
    run_high_freq_ml_risk()
