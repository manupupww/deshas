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

def get_levels(df, window=50):
    resistance = df['high'].rolling(window).max()
    support = df['low'].rolling(window).min()
    return support, resistance

class BestDualModeStrategy(Strategy):
    def init(self):
        self.entry_p = 0
        self.is_power_move = False
        self.vol_avg = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.Volume)

    def next(self):
        if len(self.data) < 20: return
        
        price = self.data.Close[-1]
        open_p = self.data.Open[-1]
        vol = self.data.Volume[-1]
        
        sup_4h = self.data.sup_4h[-1]
        res_4h = self.data.res_4h[-1]
        sup_1h = self.data.sup_1h[-1]
        res_1h = self.data.res_1h[-1]
        long_liq = self.data.long_liquidations[-1]
        short_liq = self.data.short_liquidations[-1]

        if self.position:
            if not self.is_power_move:
                if self.position.is_long:
                    if (price / self.entry_p - 1) > 0.005 and price < open_p:
                        self.position.close()
                        return
                elif self.position.is_short:
                    if (self.entry_p / price - 1) > 0.005 and price > open_p:
                        self.position.close()
                        return

        if not self.position:
            is_at_support = (price <= sup_1h * 1.002) or (price <= sup_4h * 1.002)
            is_at_resistance = (price >= res_1h * 0.998) or (price >= res_4h * 0.998)
            
            self.is_power_move = vol > (self.vol_avg[-1] * 1.5)

            if is_at_support and long_liq > 10.0:
                self.entry_p = price
                # Padidintas TP ir suamzintas SL maksimaliam svertui
                self.buy(sl = price * 0.995, tp = price * 1.03)

            elif is_at_resistance and short_liq > 10.0:
                self.entry_p = price
                self.sell(sl = price * 1.005, tp = price * 0.97)

def run_best_test():
    df_15m = pd.read_csv('data/BTC_15min_parallel.csv')
    df_1h = pd.read_csv('data/BTC_1h_parallel.csv')
    df_4h = pd.read_csv('data/BTC_4h_parallel.csv')
    
    for df in [df_15m, df_1h, df_4h]:
        df.columns = df.columns.str.lower()
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        df.dropna(inplace=True)

    df_1h['sup_1h'], df_1h['res_1h'] = get_levels(df_1h, 50)
    df_4h['sup_4h'], df_4h['res_4h'] = get_levels(df_4h, 50)
    
    df_15m['sup_1h'] = df_1h['sup_1h'].reindex(df_15m.index).ffill()
    df_15m['res_1h'] = df_1h['res_1h'].reindex(df_15m.index).ffill()
    df_15m['sup_4h'] = df_4h['sup_4h'].reindex(df_15m.index).ffill()
    df_15m['res_4h'] = df_4h['res_4h'].reindex(df_15m.index).ffill()
    
    df_15m.dropna(inplace=True)
    df_15m.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'}, inplace=True)
    
    bt = Backtest(df_15m, BestDualModeStrategy, cash=10000, commission=0.0, margin=0.05)
    print(bt.run())

if __name__ == "__main__":
    run_best_test()
