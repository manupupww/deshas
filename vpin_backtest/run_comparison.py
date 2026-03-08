"""Quick comparison runner for VPIN strategy parameters."""
import os, sys, warnings
os.environ['TQDM_DISABLE'] = '1'
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(__file__))
from vpin_strategy import VPINStrategy, download_btc_data
import numpy as np
from backtesting.lib import FractionalBacktest

data = download_btc_data()

configs = [
    (10, 0.55, 15), (10, 0.60, 20),
    (16, 0.55, 15), (16, 0.55, 20), (16, 0.60, 20), (16, 0.60, 30), (16, 0.65, 20),
    (20, 0.55, 20), (20, 0.60, 20),
    (30, 0.55, 20), (30, 0.60, 20),
]

print(f"{'Buckets':>7} | {'Entry':>5} | {'SMA':>3} | {'Return%':>10} | {'MaxDD%':>10} | {'Sharpe':>8} | {'Trades':>6} | {'Win%':>6}")
print("-" * 75)

for nb, ve, sp in configs:
    bt = FractionalBacktest(
        data, VPINStrategy,
        cash=100_000, commission=0.002,
        exclusive_orders=True, trade_on_close=True,
        fractional_unit=1 / 1e6,
    )
    stats = bt.run(n_buckets=nb, vpin_entry=ve, sma_period=sp)
    sh = stats['Sharpe Ratio']
    sh_s = f"{sh:.4f}" if not np.isnan(sh) else "N/A"
    print(f"{nb:>7} | {ve:>5.2f} | {sp:>3} | {stats['Return [%]']:>10.1f} | {stats['Max. Drawdown [%]']:>10.1f} | {sh_s:>8} | {stats['# Trades']:>6} | {stats['Win Rate [%]']:>5.1f}%")
