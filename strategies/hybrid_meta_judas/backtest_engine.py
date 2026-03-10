import pandas as pd
import numpy as np
import logging
import os
import joblib
import glob
import matplotlib.pyplot as plt

# Custom Modules
from continuous_engine import ContinuousPrimaryEngine
from feature_extraction import FeatureExtraction
from meta_model import MetaModelEngine

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def run_detailed_backtest():
    logger.info("--- STARTING DETAILED INSTITUTIONAL BACKTEST ---")
    
    # 1. Load Data
    price_data_path = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020_2022_dollar_bars.csv"
    synthetic_dir = r"C:\Users\Mr. Perfect\tradingbot\data\synthetic"
    real_fund_dir = r"C:\Users\Mr. Perfect\tradingbot\ML_Pipeline\03_features\extracted"
    
    df = pd.read_csv(price_data_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df.set_index('timestamp', inplace=True)
    
    # 2. Engines
    primary = ContinuousPrimaryEngine(window=50, z_threshold=1.5)
    df_signals = primary.generate_signals(df)
    
    extractor = FeatureExtraction()
    test_features = extractor.generate_all_features(df_signals.copy())
    
    # Load model and feature cols
    model = joblib.load("meta_model.pkl")
    feature_cols = joblib.load("feature_cols.joblib")
    
    # 3. Load External Data
    funding_files = glob.glob(os.path.join(real_fund_dir, "*.csv"))
    if funding_files:
        funding_dfs = []
        for f in funding_files:
            tmp = pd.read_csv(f)
            tmp = tmp[['calc_time', 'last_funding_rate']]
            tmp.columns = ['timestamp', 'real_funding_rate']
            funding_dfs.append(tmp)
        df_real_funding = pd.concat(funding_dfs).sort_values('timestamp')
        df_real_funding['timestamp'] = pd.to_datetime(df_real_funding['timestamp'], unit='ms')
        df_real_funding.set_index('timestamp', inplace=True)
        test_features = pd.merge_asof(test_features.sort_index(), 
                                   df_real_funding.sort_index(), 
                                   left_index=True, 
                                   right_index=True, 
                                   direction='backward')
    
    for col in feature_cols:
        if col not in test_features.columns:
            path = os.path.join(synthetic_dir, f"{col}.csv")
            if os.path.exists(path):
                ext_df = pd.read_csv(path)
                ext_df['timestamp'] = pd.to_datetime(ext_df['timestamp'])
                ext_df.set_index('timestamp', inplace=True)
                test_features = pd.merge_asof(test_features.sort_index(), 
                                           ext_df[[col]].sort_index(), 
                                           left_index=True, 
                                           right_index=True, 
                                           direction='backward')
    
    # 4. Out-of-Sample Split
    split_idx = int(len(test_features) * 0.7)
    X_test_all = test_features.iloc[split_idx:].fillna(0)
    
    # 5. Inference
    X = X_test_all[feature_cols]
    probs = model.predict_proba(X)[:, 1]
    
    # Bet Sizing
    temp_meta = MetaModelEngine()
    bet_sizes = temp_meta.calculate_bet_size(probs, method='continuous')
    
    # 6. Returns Calculation
    test_prices = df.loc[X.index, 'close']
    test_signals = df_signals.loc[X.index, 'primary_signal']
    raw_returns = test_prices.pct_change().shift(-1).fillna(0)
    
    # Base strategy returns
    base_returns = raw_returns * test_signals
    
    # Hybrid strategy returns
    hybrid_returns = raw_returns * test_signals * bet_sizes
    
    # 7. Metrics & Trade Analysis
    def analyze_strategy(strategy_returns, name):
        equity = (1 + strategy_returns).cumprod()
        trades = strategy_returns[strategy_returns != 0]
        total_trades = len(trades)
        win_rate = (trades > 0).mean() * 100 if total_trades > 0 else 0
        
        # Max Drawdown
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        max_dd = drawdown.min() * 100
        
        # Sharpe (Annualized ~5min frequency)
        sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(365 * 24 * 12) if strategy_returns.std() > 0 else 0
        
        logger.info(f"\n--- {name} RESULTS ---")
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Win Rate: {win_rate:.2f}%")
        logger.info(f"Max Drawdown: {max_dd:.2f}%")
        logger.info(f"Sharpe Ratio: {sharpe:.4f}")
        logger.info(f"Cumulative Return: {(equity.iloc[-1]-1)*100:.2f}%")
        return equity

    base_eq = analyze_strategy(base_returns, "BASE STRATEGY")
    hybrid_eq = analyze_strategy(hybrid_returns, "HYBRID META-BOT")
    
    # 8. Plotting
    plt.figure(figsize=(15, 8))
    plt.subplot(2, 1, 1)
    plt.plot(base_eq, label='Base (Z-Score)', alpha=0.6, color='gray')
    plt.plot(hybrid_eq, label='Hybrid (Meta-Labeling)', linewidth=2, color='green')
    plt.title('Hedge Fund Performance: Equity Curve')
    plt.legend()
    plt.grid(True, alpha=0.2)
    
    plt.subplot(2, 1, 2)
    plt.plot(bet_sizes, color='blue', alpha=0.4)
    plt.title('ML Bet Sizing (Risk Manager Activity)')
    plt.tight_layout()
    plt.savefig('detailed_backtest.png')
    logger.info("\nDetailed plots saved to 'detailed_backtest.png'")

if __name__ == "__main__":
    run_detailed_backtest()
