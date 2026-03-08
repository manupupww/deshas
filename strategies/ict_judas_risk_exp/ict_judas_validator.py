"""
📉 ICT Judas Swing Validator
===========================
Tests the NY Session Manipulation strategy on BTC 1min data.
Leverage: 20x | Capital: $1000
"""

import pandas as pd
import numpy as np
import os
import sys
# Add parent directory to path to find engines
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backtesting import Backtest, Strategy
from ict_judas_engine import ICTJudasEngine

# Konfigūracija
DATA_PATH = "../data/BTC_1min_upsampled.csv"
CASH = 100000
LEVERAGE = 1
TP_PERCENT = 0.4 / 100
SL_PERCENT = 0.4 / 100

class JudasSwingStrategy(Strategy):
    # SL/TP multipliers (Flux Charts style default risk)
    sl_mult = 6.5
    tp_mult = 1.5 # Adjusted RR for crypto volatility
    
    def init(self):
        self.buy_sig = self.I(lambda: self.data.buy_sig, name="BuySig")
        self.sell_sig = self.I(lambda: self.data.sell_sig, name="SellSig")
        self.atr = self.I(lambda: self.data.atr, name="ATR")
        
        # Diagnostic: Check for signals in backtest data
        buy_count = np.sum(self.buy_sig == 1)
        print(f"    [INIT] Strategy initialized. Signals in backtest data: Buy={buy_count}")

    def next(self):
        price = self.data.Close[-1]
        atr = self.atr[-1]
        
        if np.isnan(atr) or atr <= 0: return

        # Exact unit calculation for 15x leverage (leaving $ room for fees/slippage)
        # 15x instead of 20x to avoid immediate 'insufficient margin' on volatility
        available_leverage = 15
        units = (self.equity * available_leverage) / price
        units = int(units) # MUST be whole number for backtesting.py if > 1

        if units <= 0: return

        # Long Entry
        if self.buy_sig[-1] == 1:
            if not self.position:
                sl = price - (atr * self.sl_mult)
                tp = price + (atr * self.tp_mult)
                if sl < price:
                    print(f"    [TRADE] Long at {price:.2f}, SL: {sl:.2f}, TP: {tp:.2f}, Units: {units}")
                    self.buy(sl=sl, tp=tp, size=units)
        
        # Short Entry
        elif self.sell_sig[-1] == 1:
            if not self.position:
                sl = price + (atr * self.sl_mult)
                tp = price - (atr * self.tp_mult)
                if sl > price:
                    print(f"    [TRADE] Short at {price:.2f}, SL: {sl:.2f}, TP: {tp:.2f}, Units: {units}")
                    self.sell(sl=sl, tp=tp, size=units)

def run_validation():
    print("\n" + "═"*40)
    print("  🚀 ICT JUDAS SWING VALIDATION (20x)")
    print("═"*40)

    if not os.path.exists(DATA_PATH):
        print(f"❌ Klaida: Nerastas failas {DATA_PATH}")
        return

    print(f"📊 Kraunami duomenys: {os.path.basename(DATA_PATH)}")
    df = pd.read_csv(DATA_PATH)
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    
    print("  🧮 Skaičiuojami signalai (NY Session)...")
    engine = ICTJudasEngine(df)
    # Naudojame UTC-4 (NY Summer Time)
    buy_sig, sell_sig, atr = engine.get_signals(utc_offset=4)
    
    # Pridedame signalus prieš pervadinant stulpelius
    df['buy_sig'] = buy_sig
    df['sell_sig'] = sell_sig
    df['atr'] = atr

    # Pre-process naming conventions for backtesting ONLY after signals are calculated
    df.rename(columns={
        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
    }, inplace=True)
    
    print(f"  📡 Sugeneruoti signalai: Buy={buy_sig.sum()}, Sell={sell_sig.sum()}")
    
    if buy_sig.sum() > 0:
        # Show first 5 signal timestamps
        signal_times = df[df['buy_sig'] == 1].index[:5]
        print(f"    [DEBUG] Pirmieji Buy signalai (UTC): {list(signal_times)}")

    # Backtest nustatymai - Naudojame margin=0.05 (20x svertas)
    bt = Backtest(df, JudasSwingStrategy, cash=CASH, commission=0.0006, margin=0.05)
    stats = bt.run()
    
    print("\n📈 REZULTATAI:")
    print(f"    Pradinis kapitalas: ${CASH}")
    print(f"    Svertas (Leverage): {LEVERAGE}x")
    print(f"    Pelnas/Nuostolis:   {stats['Return [%]']:.2f}%")
    print(f"    Laimėjimo procentas: {stats['Win Rate [%]']:.2f}%")
    print(f"    Iš viso sandorių:    {stats['# Trades']}")
    print(f"    Max. Drawdown:      {stats['Max. Drawdown [%]']:.2f}%")
    print(f"    Sharpe Ratio:       {stats['Sharpe Ratio']:.2f}")

    if stats['# Trades'] > 0:
        # Pavyzdinis rezultatas doleriais
        final_equity = stats['Equity Final [$]']
        print(f"    Galutinis balansas: ${final_equity:.2f}")
    
    print("═"*40 + "\n")

if __name__ == "__main__":
    run_validation()
