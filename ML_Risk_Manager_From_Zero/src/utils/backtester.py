import pandas as pd
import numpy as np

def run_backtest(input_path):
    print(f"Running backtest on {input_path}...")
    df = pd.read_csv(input_path)
    
    # Calculate returns for Primary Strategy (Baseline)
    # Primary strategy executes on ALL signals
    df['primary_pnl'] = df['side'] * df['returns']
    
    # Calculate returns for Meta-Strategy (Risk Manager)
    # Meta-strategy only executes where meta-label predicted 1 (or prob > 0.5)
    # We use the probabilistic bet size as well
    df['meta_pnl'] = df['side'] * df['returns'] * (df['meta_prob'] > 0.5).astype(int)
    df['weighted_meta_pnl'] = df['side'] * df['returns'] * df['bet_size']
    
    # Cumulative PnL
    primary_cum_pnl = df['primary_pnl'].cumsum()
    meta_cum_pnl = df['meta_pnl'].cumsum()
    weighted_meta_cum_pnl = df['weighted_meta_pnl'].cumsum()
    
    # Metrics
    def calculate_sharpe(pnl_series):
        if pnl_series.std() == 0: return 0
        return (pnl_series.mean() / pnl_series.std()) * np.sqrt(252) # Annualized (daily bars approx)

    results = {
        "Primary PnL": df['primary_pnl'].sum(),
        "Meta PnL (Binary)": df['meta_pnl'].sum(),
        "Meta PnL (Weighted)": df['weighted_meta_pnl'].sum(),
        "Primary Sharpe": calculate_sharpe(df['primary_pnl']),
        "Meta Sharpe (Binary)": calculate_sharpe(df['meta_pnl']),
        "Meta Sharpe (Weighted)": calculate_sharpe(df['weighted_meta_pnl']),
        "Trades Filtered Out (%)": (1 - (df['meta_prob'] > 0.5).mean()) * 100
    }
    
    print("\n" + "="*30)
    print("BACKTEST RESULTS (Real Crypto Data)")
    print("="*30)
    for k, v in results.items():
        print(f"{k:25}: {v:.4f}")
    
    df.to_csv("data/processed/backtest_results.csv", index=False)
    print("\n✅ Backtest results saved to data/processed/backtest_results.csv")
    return results

if __name__ == "__main__":
    run_backtest("data/processed/final_bets.csv")
