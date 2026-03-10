import pandas as pd
import numpy as np
import os
import sys
# Add parent directory to path to find engines
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pickle
from backtesting import Backtest, Strategy
from ict_judas_engine import ICTJudasEngine

# Configuration
DATA_PATH = "../../data/BTC_1min_upsampled.csv"
MODEL_PATH = "judas_model.pkl"
CASH = 100000
COMMISSION = 0.0006
MARGIN = 0.05 # Corrected to 0.05 for 20x Leverage

class JudasSwingMLStrategy(Strategy):
    sl_mult = 6.5
    default_tp_mult = 1.5
    high_tp_mult = 3.5 # Aggressive TP for high-confidence trades
    
    def init(self):
        # Load ML Model
        with open(MODEL_PATH, 'rb') as f:
            self.model = pickle.load(f)
            
        self.buy_sig = self.I(lambda: self.data.buy_sig, name="BuySig")
        self.sell_sig = self.I(lambda: self.data.sell_sig, name="SellSig")
        self.atr = self.I(lambda: self.data.atr, name="ATR")
        
        # We need these for the model
        self.vol = self.I(lambda: self.data.Volume, name="Volume")
        self.long_liq = self.I(lambda: self.data.long_liquidations, name="LongLiq")
        self.short_liq = self.I(lambda: self.data.short_liquidations, name="ShortLiq")
        self.sma_trend = self.I(lambda: pd.Series(self.data.Close).rolling(60).mean(), name="SMA60")

    def next(self):
        price = self.data.Close[-1]
        atr = self.atr[-1]
        
        if np.isnan(atr) or atr <= 0: return

        # Signal check
        is_long = self.buy_sig[-1] == 1
        is_short = self.sell_sig[-1] == 1
        
        if not is_long and not is_short: return
        if self.position: return

        # --- ML INFERENCE ---
        # Minutes since 09:30 (Matches training data anchor)
        curr_time = self.data.index[-1]
        minute_of_session = curr_time.hour * 60 + curr_time.minute - (9 * 60 + 30)
        
        features = np.array([[
            1 if is_long else 0,
            self.vol[-1],
            self.long_liq[-1],
            self.short_liq[-1],
            minute_of_session,
            1 if price > self.sma_trend[-1] else 0
        ]])
        
        probs = self.model.predict_proba(features)[0]
        prob_success = probs[1]

        if prob_success < 0.20:
            return

        tp_mult = self.default_tp_mult
        if prob_success > 0.45:
            tp_mult = self.high_tp_mult

        # --- PROFESSIONAL RISK MANAGER (1% RISK PER TRADE) ---
        # We want to lose exactly 1% of current equity if Stop Loss is hit.
        risk_percent = 0.01 
        risk_amount = self.equity * risk_percent
        
        # Stop Loss distance in price units
        sl_distance = atr * self.sl_mult
        
        if sl_distance <= 0: return
        
        # Position sizing formula: Units = Risk_Amount / SL_Distance
        units = int(risk_amount / sl_distance)
        
        # Safety check: ensure we have enough margin (using 20x capacity limit)
        max_units = int((self.equity * 20) / price)
        units = min(units, max_units)
        
        if units <= 0: return

        if is_long:
            sl = price - (atr * self.sl_mult)
            tp = price + (atr * tp_mult)
            self.buy(sl=sl, tp=tp, size=units)
        else:
            sl = price + (atr * self.sl_mult)
            tp = price - (atr * tp_mult)
            self.sell(sl=sl, tp=tp, size=units)

def run_ml_validation():
    print("\n" + "═"*40)
    print("  🧠 ICT JUDAS SWING ML VALIDATION")
    print("═"*40)

    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: Model {MODEL_PATH} not found.")
        return

    print(f"📊 Loading data: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    
    engine = ICTJudasEngine(df)
    buy_sig, sell_sig, atr = engine.get_signals(utc_offset=4)
    
    df['buy_sig'] = buy_sig
    df['sell_sig'] = sell_sig
    df['atr'] = atr
    
    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)

    bt = Backtest(df, JudasSwingMLStrategy, cash=CASH, commission=COMMISSION, margin=MARGIN)
    stats = bt.run()
    
    print("\n📈 ML RESULTS:")
    print(f"    Return:           {stats['Return [%]']:.2f}%")
    print(f"    Win Rate:         {stats['Win Rate [%]']:.2f}%")
    print(f"    Trades:           {stats['# Trades']}")
    print(f"    Max Drawdown:     {stats['Max. Drawdown [%]']:.2f}%")
    if stats['# Trades'] > 0:
        print(f"    Final Balance:    ${stats['Equity Final [$]']:.2f}")
    print("═"*40 + "\n")

if __name__ == "__main__":
    run_ml_validation()
