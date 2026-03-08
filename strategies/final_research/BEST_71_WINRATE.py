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

class BestWinRateMagnetStrategy(Strategy):
    def init(self):
        self.entry_p = 0
        self.highest_p = 0
        self.lowest_p = 999999
        self.current_sl = 0

    def next(self):
        price = self.data.Close[-1]
        
        # --- TRAILING STOP VALDYMAS (Leidžiame laimėti iki galo) ---
        if self.position:
            if self.position.is_long:
                self.highest_p = max(self.highest_p, price)
                # Jei turime bent 0.3% pelno, pradedame traukti Stop Loss 0.5% atstumu
                if (price / self.entry_p - 1) > 0.003:
                    new_sl = self.highest_p * 0.995
                    if new_sl > self.current_sl:
                        self.current_sl = new_sl
                
                if price <= self.current_sl:
                    self.position.close()
                    return

            elif self.position.is_short:
                self.lowest_p = min(self.lowest_p, price)
                if (self.entry_p / price - 1) > 0.003:
                    new_sl = self.lowest_p * 1.005
                    if self.current_sl == 0 or new_sl < self.current_sl:
                        self.current_sl = new_sl
                
                if price >= self.current_sl:
                    self.position.close()
                    return

        # --- ĮĖJIMO LOGIKA ---
        if not self.position:
            sup_4h = self.data.sup_4h[-1]
            res_4h = self.data.res_4h[-1]
            sup_1h = self.data.sup_1h[-1]
            res_1h = self.data.res_1h[-1]
            long_liq = self.data.long_liquidations[-1]
            short_liq = self.data.short_liquidations[-1]

            is_at_support = (price <= sup_1h * 1.002) or (price <= sup_4h * 1.002)
            if is_at_support and long_liq > 10.0:
                self.entry_p = price
                self.highest_p = price
                self.current_sl = price * 0.99 # Pradinis 1% Stop Loss
                self.buy()

            is_at_resistance = (price >= res_1h * 0.998) or (price >= res_4h * 0.998)
            if is_at_resistance and short_liq > 10.0:
                self.entry_p = price
                self.lowest_p = price
                self.current_sl = price * 1.01 # Pradinis 1% Stop Loss
                self.sell()

def run_final_win_test():
    df_15m = pd.read_csv('data/BTC_15min_parallel.csv')
    df_1h = pd.read_csv('data/BTC_1h_parallel.csv')
    df_4h = pd.read_csv('data/BTC_4h_parallel.csv')
    
    for df in [df_15m, df_1h, df_4h]:
        df.columns = df.columns.str.lower()
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        df.dropna(inplace=True)

    df_1h['sup_1h'], df_1h['res_1h'] = get_levels(df_1h)
    df_4h['sup_4h'], df_4h['res_4h'] = get_levels(df_4h)
    
    df_15m['sup_1h'] = df_1h['sup_1h'].reindex(df_15m.index).ffill()
    df_15m['res_1h'] = df_1h['res_1h'].reindex(df_15m.index).ffill()
    df_15m['sup_4h'] = df_4h['sup_4h'].reindex(df_15m.index).ffill()
    df_15m['res_4h'] = df_4h['res_4h'].reindex(df_15m.index).ffill()
    
    df_15m.dropna(inplace=True)
    df_15m.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'}, inplace=True)
    
    # 20x leverage (margin=0.05) ir 0 mokesčių
    bt = Backtest(df_15m, BestWinRateMagnetStrategy, cash=100000, commission=0.0, margin=0.05)
    stats = bt.run()
    print(stats)

if __name__ == "__main__":
    run_final_win_test()
