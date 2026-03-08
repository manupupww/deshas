import pandas as pd
import numpy as np

df = pd.read_csv('data/processed/backtest_results.csv')

def calculate_sharpe_v2(returns):
    if len(returns) < 2: return 0
    mean_ret = returns.mean()
    std_ret = returns.std()
    if std_ret == 0: return 0
    return (mean_ret / std_ret) * np.sqrt(252 * 24 * 6) # Assuming 10 min bars roughly

print("--- Backtest Summary (d=0.2) ---")
print(f"Primary PnL: {df['primary_pnl'].sum():.4f}")
print(f"Primary Sharpe: {calculate_sharpe_v2(df['primary_pnl']):.4f}")

meta_trades = df[df['filtered_signal'] == 1]
print(f"Meta PnL: {df['meta_pnl'].sum():.4f}")
print(f"Meta Sharpe: {calculate_sharpe_v2(df['meta_pnl']):.4f}")

filter_rate = (1 - len(meta_trades) / len(df)) * 100
print(f"Trades Filtered Out: {filter_rate:.2f}%")
