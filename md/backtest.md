import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# Load the filtered data
data_path = '/Users/and/Dropbox/dev/github/hyper-liquid-trading-bots/bac'
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')

# Bollinger Band Breakout Strategy (Short Only)
class BollingerBandBreakoutShort(Strategy):
    window = 21
    num_std = 2.7
    take_profit = 0.05  # 5%
    stop_loss = 0.03    # 3%

    def init(self):
        # Calculate Bollinger Bands using TA-Lib
        self.upper_band, self.middle_band, self.lower_band = self.I(
            talib.BBANDS,
            self.data.Close,
            timeperiod=self.window,
            nbdevup=self.num_std,
            nbdevdn=self.num_std,
            matype=0
        )

    def next(self):
        if len(self.data) < self.window:
            return

        # Check for breakout below lower band
        if self.data.Close[-1] < self.lower_band[-1] and not self.position:
            self.sell(
                sl=self.data.Close[-1] * (1 + self.stop_loss),
                tp=self.data.Close[-1] * (1 - self.take_profit)
            )

# Rename necessary columns if present and ensure format correctly
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Unnamed: 6']

# Drop the unnecessary column
data.drop(columns=['Unnamed: 6'], inplace=True)

# Create and configure the backtest
bt = Backtest(data, BollingerBandBreakoutShort, cash=100000, commission=.002)

# Run the backtest with default parameters and print the results
stats_default = bt.run()
print("Default Parameters Results:")
print(stats_default)

# Now perform the optimization
optimization_results = bt.optimize(
    window=range(10, 28, 5),
    num_std=[round(i, 1) for i in np.arange(1.5, 3.5, 0.1)],
    take_profit=[i / 100 for i in range(1, 7, 1)],  # Optimize TP from 1% to 6%
    stop_loss=[i / 100 for i in range(1, 7, 1)],    # Optimize SL from 1% to 6%
    maximize='Equity Final [$]',
    constraint=lambda param: param.window > 8 and param.num_std > 1
)

# Print the optimization results
print(optimization_results)

# Print the best optimized values
print("Best Parameters:")
print("Window:", optimization_results._strategy.window)
print("Number of Standard Deviations:", optimization_results._strategy.num_std)
print("Take Profit:", optimization_results._strategy.take_profit)
print("Stop Loss:", optimization_results._strategy.stop_loss)


 noriu kad isbandytum 20 ideju pagristu tik likvidavimo ideju ir paleisti 10 agentu lygegretus 2 dviem idojom kieivenas ir jie visi turi naudoti kurios yra parasytos tame md faile likvidavimo idejos bet mums reikai variajnciu su dvigubais patvvirtinimais nes buvo keletas ideju kai mes perejomes su sisias likvidavimo duomeninimis kurie buvo apie dviguba patvritinima pries is tirkuju ienant taigi bus vienas patobulinimas kuris kieveinas is ju agentai imis veiksmu ir igyvendins remdamiesi musu laimejusiais idejom ir tada isisuta faktine statisine lentele foramta kad galeciau analizuoti ryskumo santiki , rusiavimo santiki m nuosmokius ROI, EV 
