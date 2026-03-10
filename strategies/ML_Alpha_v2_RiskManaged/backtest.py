"""
ML Backtest v2 — Su ML Risk Manager (Dynamic Bet Sizing)
=========================================================
Ši versija naudoja rizikos valdymo sluoksnį pozicijų dydžio parinkimui.

Pakeitimai:
- Įtrauktas risk_manager.py.
- Strategija dabar užsako konkrečius UNIT'us, o ne fiksuotus %.
"""

import pandas as pd
import numpy as np
import os
import sys
import glob
import joblib
from backtesting import Backtest, Strategy
from risk_manager import MLRiskManager

# Pridedame kelią į strategies folderį, kad matytų risk_manager module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# 1. DUOMENŲ PARUOŠIMAS (Išlieka toks pat kaip v1)
# ============================================================
def prepare_backtest_data(data_dir, model_path):
    bars_path = os.path.join(data_dir, "BTCUSDT_2020_2022_dollar_bars_fracdiff_d0.10.csv")
    bars = pd.read_csv(bars_path)
    bars['timestamp'] = pd.to_numeric(bars['timestamp']).astype(np.int64)
    bars = bars.sort_values('timestamp').reset_index(drop=True)
    
    synthetic_dir = os.path.join(data_dir, "synthetic")
    csv_files = sorted(glob.glob(os.path.join(synthetic_dir, "*.csv")))
    
    df = bars.copy()
    for csv_path in csv_files:
        feat = pd.read_csv(csv_path)
        feat['timestamp'] = pd.to_numeric(feat['timestamp']).astype(np.int64)
        df = pd.merge_asof(df, feat, on='timestamp', direction='nearest', tolerance=1000000)
    
    model_data = joblib.load(model_path)
    model = model_data['model']
    feature_cols = model_data['feature_cols']
    
    X = df[feature_cols].copy()
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    X = X.fillna(X.median())
    
    df['ML_Signal'] = model.predict(X.values)
    probabilities = model.predict_proba(X.values)
    df['ML_Confidence'] = np.max(probabilities, axis=1)
    
    bt_df = pd.DataFrame({
        'Open': df['open'].values,
        'High': df['high'].values,
        'Low': df['low'].values,
        'Close': df['close'].values,
        'Volume': df['volume'].values,
        'ML_Signal': df['ML_Signal'].values,
        'ML_Confidence': df['ML_Confidence'].values,
    }, index=pd.to_datetime(df['datetime']))
    
    bt_df = bt_df.sort_index(ascending=True)
    bt_df = bt_df[~bt_df.index.duplicated(keep='first')]
    return bt_df

# ============================================================
# 2. ML STRATEGIJA SU RISK MANAGER
# ============================================================
class MLRiskStrategy(Strategy):
    # Parametrai
    confidence_threshold = 0.70    # Pakeltas slenkstis pagal mūsų optimizaciją
    take_profit_pct = 0.03         # 3% pagal optimizaciją
    stop_loss_pct = 0.10           # 10% pagal optimizaciją
    risk_per_trade = 0.02          # Rizikuojame 2% kapitalo per sandorį
    
    def init(self):
        # Inicializuojame Risk Managerį
        self.risk_mgr = MLRiskManager(
            cash_balance=self.equity, 
            risk_per_trade=self.risk_per_trade,
            min_confidence=self.confidence_threshold
        )
        self.ml_signal = self.I(lambda: self.data.ML_Signal, name='ML Signal')
        self.ml_confidence = self.I(lambda: self.data.ML_Confidence, name='ML Confidence')
    
    def next(self):
        # Atnaujiname balansą Risk Manageriui
        self.risk_mgr.cash_balance = self.equity
        
        price = self.data.Close[-1]
        signal = self.data.ML_Signal[-1]
        confidence = self.data.ML_Confidence[-1]
        
        # Stop Loss ir Take Profit kainos (vėliau jas naudosime dydžio skaičiavimui)
        if signal == 1:
            sl_price = price * (1 - self.stop_loss_pct)
            tp_price = price * (1 + self.take_profit_pct)
        else:
            sl_price = price * (1 + self.stop_loss_pct)
            tp_price = price * (1 - self.take_profit_pct)
        
        # Tikriname per Risk Managerį
        approved, reason = self.risk_mgr.validate_setup(signal, confidence)
        
        if not self.position and approved:
            # Skaičiuojame dinaminį dydį unit'ais
            size_units = int(self.risk_mgr.get_position_size(price, sl_price, confidence))
            
            if size_units > 0:
                if signal == 1:
                    self.buy(size=size_units, sl=sl_price, tp=tp_price)
                elif signal == 0:
                    self.sell(size=size_units, sl=sl_price, tp=tp_price)
        else:
            # Emergency Exit: jei pasikeičia regime / signalas
            if self.position.is_long and signal == 0 and confidence >= self.confidence_threshold:
                self.position.close()
            elif self.position.is_short and signal == 1 and confidence >= self.confidence_threshold:
                self.position.close()

# ============================================================
# 3. MAIN — Vykdymas
# ============================================================
def main():
    data_dir = r"C:\Users\Mr. Perfect\tradingbot\data"
    # 1. Parinkti modelio kelią (prioritetas vietiniam failui)
    local_model = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_model.pkl")
    if os.path.exists(local_model):
        model_path = local_model
    else:
        model_path = os.path.join(data_dir, "models", "best_model.pkl")

    data = prepare_backtest_data(data_dir, model_path)

    print("\n" + "=" * 60)
    print("BACKTESTAS: ML ALPHA v2 + RISK MANAGER")
    print("=" * 60)
    
    bt = Backtest(
        data, 
        MLRiskStrategy,
        cash=100_000,
        commission=0.001,
        exclusive_orders=True,
        trade_on_close=True
    )
    
    stats = bt.run()
    print(stats)
    
    # Išsaugojame naujus rezultatus vietiniame aplanke
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_risk_results.html")
    bt.plot(filename=output_path, open_browser=False)
    print(f"\n✅ Rezultatai išsaugoti: {output_path}")

if __name__ == "__main__":
    main()
