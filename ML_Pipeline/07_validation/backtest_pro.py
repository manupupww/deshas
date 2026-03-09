import pandas as pd
import numpy as np
import os
import argparse
from backtesting import Backtest, Strategy

class ProAlgoStrategy(Strategy):
    # Parametrai
    sl_pct = 0.02
    trail_pct = 0.02
    
    def init(self):
        # Mes naudojame is anksto sugeneruotus signalus is DataFrame
        self.signal = self.I(lambda: self.data.signal_composite, name='Signal')

    def next(self):
        price = self.data.Close[-1]
        
        # Jei turime signala ir nesame pozicijoje - PERKAME
        if self.signal[-1] == 1 and not self.position:
            # Pirkimas su pradiniu Stop Loss (2%)
            self.buy(sl=price * (1 - self.sl_pct))
            
        # Trailing Stop logika: kelsime SL kartu su kaina
        if self.position:
            for trade in self.trades:
                # Naujas Trailing SL (2% nuo max kainos)
                new_sl = price * (1 - self.trail_pct)
                # Keliame tik jei naujas SL yra auksciau uz esama
                if trade.sl is None or new_sl > trade.sl:
                    trade.sl = new_sl

def load_data(data_dir, signals_path):
    # A. Dollar Bars + FracDiff
    bars_path = os.path.join(data_dir, "BTCUSDT_2020-2025dollarBars__fracdiff_d0.10.csv")
    # CSV has 8 columns. We map them correctly.
    cols = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dollar_Volume', 'Close_FracDiff']
    df = pd.read_csv(bars_path, names=cols, header=None)
    
    # Konvertuojame i skaicius
    for c in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp', 'Close'])
    df.set_index('timestamp', inplace=True)
    
    # B. Load Signals
    signals_df = pd.read_csv(signals_path)
    signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'], unit='ms')
    signals_df.set_index('timestamp', inplace=True)
    
    # C. Merge all signals
    signal_cols = ['signal_max', 'signal_ma', 'signal_bb', 'signal_composite']
    df = df.merge(signals_df[signal_cols], left_index=True, right_index=True, how='left').fillna(0)
                
    return df

class ProStrategy(Strategy):
    # Dynamic signal column name
    sig_col = 'signal_composite'
    sl_pct = 0.02
    trail_pct = 0.02
    
    def init(self):
        # Imsime signala pagal nurodyta stulpeli
        self.signal = self.I(lambda: self.data[self.sig_col], name='Signal')

    def next(self):
        price = self.data.Close[-1]
        
        if self.signal[-1] == 1 and not self.position:
            self.buy(sl=price * (1 - self.sl_pct))
            
        if self.position:
            for trade in self.trades:
                new_sl = price * (1 - self.trail_pct)
                if trade.sl is None or new_sl > trade.sl:
                    trade.sl = new_sl

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="../../data")
    parser.add_argument("--signals", default="../../data/signals/primary_signals.csv")
    args = parser.parse_args()
    
    full_df = load_data(args.data_dir, args.signals)
    
    signal_types = ['signal_max', 'signal_ma', 'signal_bb', 'signal_composite']
    
    print("\n" + "="*50)
    print("🚀 PROFESSIONAL BTC ALGO BACKTEST (2020-2025)")
    print(f"Settings: SL=2%, Trailing=2%")
    print("="*50)

    for sig in signal_types:
        print(f"\n📈 TESTING STRATEGY: {sig.upper()}")
        # Klonuojame ir nustatome specfini signala
        bt = Backtest(full_df, ProStrategy, cash=10000, commission=.001, exclusive_orders=True)
        # Paduodame signala per klase (overwrite sig_col)
        ProStrategy.sig_col = sig
        stats = bt.run()
        
        print("-" * 30)
        # Rodome svarbiausias stulpelius kaip nuotraukoje
        relevant_metrics = [
            'Start', 'End', 'Duration', 'Equity Final [$]', 'Return [%]', 
            'Buy & Hold Return [%]', 'CAGR [%]', 'Sharpe Ratio', 'Max. Drawdown [%]', 
            '# Trades', 'Win Rate [%]', 'Profit Factor', 'Best Trade [%]', 'Worst Trade [%]'
        ]
        for m in relevant_metrics:
            if m in stats:
                print(f"{m:<25}: {stats[m]}")
        
        # Isaugome kievienai strategijai grafa
        output_file = f"backtest_{sig}.html"
        bt.plot(filename=output_file, open_browser=False)
        print(f"✅ Report saved to: {output_file}")
