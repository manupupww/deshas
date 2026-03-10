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

def prepare_features(df):
    data = df.copy()
    data['RSI'] = 100 - (100 / (1 + (data['Close'].diff().where(data['Close'].diff() > 0, 0).rolling(14).mean() / 
                                    (data['Close'].diff().where(data['Close'].diff() < 0, 0).abs().rolling(14).mean() + 0.00001))))
    data['EMA_Diff'] = data['Close'].ewm(span=12).mean() - data['Close'].ewm(span=21).mean()
    data['Long_Liq_Z'] = (data['long_liquidations'] - data['long_liquidations'].rolling(50).mean()) / (data['long_liquidations'].rolling(50).std() + 0.00001)
    data['Short_Liq_Z'] = (data['short_liquidations'] - data['short_liquidations'].rolling(50).mean()) / (data['short_liquidations'].rolling(50).std() + 0.00001)
    data['Liq_Ratio'] = (data['long_liquidations'] - data['short_liquidations']) / (data['long_liquidations'] + data['short_liquidations'] + 0.00001)
    data['Vol_Liq_Ratio'] = (data['long_liquidations'] + data['short_liquidations']) / (data['Volume'] + 0.00001)
    data['Return_5'] = data['Close'].pct_change(5)
    data.dropna(inplace=True)
    return data

def train_ml_model(df):
    print("Mokomas AI modelis naudojant LIKVIDAVIMŲ duomenis...")
    horizon, tp_pct, sl_pct = 48, 0.015, 0.015
    targets, closes = [], df['Close'].values
    for i in range(len(closes) - horizon):
        future = closes[i+1 : i+1+horizon]
        hit_tp = hit_sl = False
        for p in future:
            if p >= closes[i] * (1 + tp_pct): hit_tp = True; break
            if p <= closes[i] * (1 - sl_pct): hit_sl = True; break
        targets.append(1 if hit_tp and not hit_sl else 0)
    df_ml = df.iloc[:len(targets)].copy()
    df_ml['Target'] = targets
    feature_cols = ['Long_Liq_Z', 'Short_Liq_Z', 'Liq_Ratio', 'Vol_Liq_Ratio', 'RSI', 'EMA_Diff', 'Return_5']
    X, y = df_ml[feature_cols], df_ml['Target']
    split_idx = int(len(X) * 0.6)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    model = RandomForestClassifier(n_estimators=150, max_depth=6, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    return model, feature_cols, split_idx

class MLStrategy(Strategy):
    model, features = None, []
    def init(self):
        pass
    def next(self):
        try:
            current_f = [self.data[col][-1] for col in self.features]
            prob = self.model.predict_proba([current_f])[0][1]
            if prob > 0.55 and not self.position:
                self.buy(tp = self.data.Close[-1] * 1.015, sl = self.data.Close[-1] * 0.985)
        except: pass

def run_ml_system():
    data_path = os.path.join('data', 'BTC_15min_parallel.csv')
    df = pd.read_csv(data_path)
    df.dropna(inplace=True)
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    df_f = prepare_features(df)
    model, f_cols, split_idx = train_ml_model(df_f)
    test_data = df_f.iloc[split_idx:].copy()
    MLStrategy.model, MLStrategy.features = model, f_cols
    bt = Backtest(test_data, MLStrategy, cash=1000000, commission=0.0004)
    print(bt.run())

if __name__ == "__main__":
    run_ml_system()
