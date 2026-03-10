import pandas as pd
import numpy as np
import os
import sys

# Pridedame backtesting-py
sys.path.append(os.path.abspath('backtesting-py'))
try:
    from backtesting import Backtest, Strategy
except ImportError:
    print("Klaida: Nepavyko rasti 'backtesting' bibliotekos.")
    sys.exit(1)

class MoonStrategy(Strategy):
    # Agresyvūs parametrai 100,000% tikslui su 20x svertu
    tp_pct = 0.015
    sl_pct = 0.003
    liq_threshold = 1.2

    def init(self):
        self.long_liq_avg = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.long_liquidations)
        self.short_liq_avg = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.short_liquidations)

    def next(self):
        if len(self.data) < 20: return
        price = self.data.Close[-1]
        
        if self.position:
            # Smart Exit po 0.2% pelno
            profit = (price / self.position.entry_price - 1) if self.position.is_long else (self.position.entry_price / price - 1)
            if profit > 0.002:
                if (self.position.is_long and price < self.data.Open[-1]) or (self.position.is_short and price > self.data.Open[-1]):
                    self.position.close()
            return

        # Dažni įėjimai pagal skausmą
        if self.data.long_liquidations[-1] > (self.long_liq_avg[-1] * self.liq_threshold):
            self.buy(sl = price * (1 - self.sl_pct), tp = price * (1 + self.tp_pct))
        elif self.data.short_liquidations[-1] > (self.short_liq_avg[-1] * self.liq_threshold):
            self.sell(sl = price * (1 + self.sl_pct), tp = price * (1 - self.tp_pct))

def run_moon_test():
    df = pd.read_csv('data/BTC_15min_parallel.csv')
    df.columns = df.columns.str.lower()
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df.dropna(inplace=True)
    df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'}, inplace=True)
    
    # 20x svertas ir 0 mokesčių
    bt = Backtest(df, MoonStrategy, cash=10000, commission=0.0, margin=0.05)
    print(bt.run())

if __name__ == "__main__":
    run_moon_test()
