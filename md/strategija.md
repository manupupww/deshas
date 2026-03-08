import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import matplotlib.pyplot as plt
# Load the data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/quant/BTCUSD.csv'
# #data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/IS_BTCUSD.csv'
# #data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/OS_BTCUSD.csv'
# #data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/IS_ETHUSD.csv'
# #data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/OS_ETHUSD.csv'
# #data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/IS_SOLUSD.csv'
# #data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/OS_SOLUSD.csv'
# #data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DiHyRMQiS.csv'
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
class MAReversalStrategy(Strategy):
    # Define the parameters we'll optimize
    ma_fast = 20
    ma_slow = 40
    take_profit = 0.10   # 10%
    stop_loss = 0.10     # 10%

    def init(self):
        # Calculate moving averages using TA-Lib
        self.sma_fast = self.I(talib.SMA, self.data.Close, self.ma_fast)
        self.sma_slow = self.I(talib.SMA, self.data.Close, self.ma_slow)

        # Add indicators to the plot - fixed lambda functions
        self.I(lambda x: self.sma_fast, f'SMA{self.ma_fast}', overlay=True)
        self.I(lambda x: self.sma_slow, f'SMA{self.ma_slow}', overlay=True)
def init(self):
    # Calculate moving averages using TA-Lib
    self.sma_fast = self.I(talib.SMA, self.data.Close, self.ma_fast)
    self.sma_slow = self.I(talib.SMA, self.data.Close, self.ma_slow)

    # Add indicators to the plot - fixed lambda functions
    self.I(lambda x: self.sma_fast, f'SMA{self.ma_fast}', overlay=True)
    self.I(lambda x: self.sma_slow, f'SMA{self.ma_slow}', overlay=True)

def next(self):
    price = self.data.Close[-1]

    # Check for short setup: price above SMA20 but below SMA40
    if price > self.sma_fast[-1] and price < self.sma_slow[-1] and not self.position:
        self.sell(sl=price * (1 + self.stop_loss),
                  tp=price * (1 - self.take_profit))
# Check for long setup: price above both SMAs
elif price > self.sma_fast[-1] and price > self.sma_slow[-1] and not self.position:
    self.buy(sl=price * (1 - self.stop_loss),
             tp=price * (1 + self.take_profit))

# Close short if price moves above SMA40
elif self.position and self.position.is_short and price > self.sma_slow[-1]:
    self.position.close()

# Rename columns to match Backtest.py requirements
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Sort index in ascending order to fix the warning
data = data.sort_index(ascending=True)
# Run backtest with default parameters
print("\n🌙 Moon Dev's Initial Backtest Results 🌙")
print("=" * 50)
stats = bt.run()
print(stats)

# Plot the unoptimized strategy results
print("\n📊 Showing plot for unoptimized strategy (close plot to continue)...")
bt.plot(filename=None)  # Setting filename=None to show plot instead of saving
plt.show()

# Optimize the strategy
print("\n🚀 Moon Dev's Strategy Optimization Starting 🚀")
print("=" * 50)

# Perform optimization
optimization_results = bt.optimize(
    ma_fast=range(10, 30, 3),
    ma_slow=range(30, 60, 3),
    take_profit=[i/100 for i in range(2, 20, 2)],  # 1% to 15%
    stop_loss=[i/100 for i in range(2, 20, 2)],    # 1% to 15%
    maximize='Equity Final [$]',
    constraint=lambda p: p.ma_fast < p.ma_slow
)
print("\n🍉 Moon Dev's Optimized Results 🍉")
print("=" * 50)
print(optimization_results)

# Print optimized parameters
print("\n✨ Moon Dev's Best Parameters ✨")
print("=" * 50)
print(f"Fast MA: {optimization_results._strategy.ma_fast}")
print(f"Slow MA: {optimization_results._strategy.ma_slow}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.2%}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.2%}")

# Create a new backtest with optimized parameters
optimized_bt = Backtest(data, MAReversalStrategy, cash=1000000, commission=0.002)
# Run backtest with default parameters
print("\n🌙 Moon Dev's Initial Backtest Results 🌙")
print("=" * 50)
stats = bt.run()
print(stats)

# Plot the unoptimized strategy results
print("\n📊 Showing plot for unoptimized strategy (close plot to continue)...")
bt.plot(filename=None)  # Setting filename=None to show plot instead of saving
plt.show()

# Optimize the strategy
print("\n🚀 Moon Dev's Strategy Optimization Starting 🚀")
print("=" * 50)
# Perform optimization
optimization_results = bt.optimize(
    ma_fast=range(10, 30, 3),
    ma_slow=range(30, 60, 3),
    take_profit=[i/100 for i in range(2, 20, 2)],  # 1% to 15%
    stop_loss=[i/100 for i in range(2, 20, 2)],    # 1% to 15%
    maximize='Equity Final [$]',
    constraint=lambda p: p.ma_fast < p.ma_slow
)

print("\n🎯 Moon Dev's Optimized Results 🎯")
print("=" * 50)
print(optimization_results)

# Print optimized parameters
print("\n✨ Moon Dev's Best Parameters ✨")
print("=" * 50)
print(f"Fast MA: {optimization_results._strategy.ma_fast}")
print(f"Slow MA: {optimization_results._strategy.ma_slow}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.2%}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.2%}")
# Create a new backtest with optimized parameters
optimized_bt = Backtest(data, MAReversalStrategy, cash=1000000, commission=0.002)

# Run backtest with optimized parameters
optimized_stats = optimized_bt.run(
    ma_fast=optimization_results._strategy.ma_fast,
    ma_slow=optimization_results._strategy.ma_slow,
    take_profit=optimization_results._strategy.take_profit,
    stop_loss=optimization_results._strategy.stop_loss
)
