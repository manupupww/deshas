import pandas as pd
import warnings
import os
import sys

# Define strategy class compatible with backtesting.py
try:
    from backtesting import Backtest, Strategy
except ImportError:
    # Fallback to local path if not in site-packages
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backtesting-py')))
    from backtesting import Backtest, Strategy

warnings.filterwarnings('ignore')

from backtesting.lib import resample_apply, crossover

class BreakoutStrategy(Strategy):
    n1 = 10
    n2 = 20
    sl_percent = 3
    trail_percent = 3

    def init(self):
        # SMA 10 and 20 as seen in the target screenshot
        self.sma1 = self.I(lambda x: pd.Series(x).rolling(self.n1).mean(), self.data.Close)
        self.sma2 = self.I(lambda x: pd.Series(x).rolling(self.n2).mean(), self.data.Close)
        self.highest_price = 0
        self.current_sl = 0

    def next(self):
        current_close = self.data.Close[-1]
        
        # Entry logic: SMA Crossover (10 over 20)
        if crossover(self.sma1, self.sma2) and not self.position:
            self.highest_price = current_close
            self.current_sl = current_close * (1 - self.sl_percent / 100)
            self.buy(sl=self.current_sl)
            return

        # Trailing Stop logic
        if self.position:
            # Exit also if SMA crosses back (optional, but let's stick to TSL for now)
            # if crossover(self.sma2, self.sma1):
            #     self.position.close()
            #     return

            if current_close > self.highest_price:
                self.highest_price = current_close
                new_sl = self.highest_price * (1 - self.trail_percent / 100)
                if new_sl > self.current_sl:
                    self.current_sl = new_sl
                    for trade in self.trades:
                        trade.sl = new_sl

if __name__ == "__main__":
    print("SMA Crossover Strategy (n1=10, n2=20) ready.")
