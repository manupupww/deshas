import pandas as pd
import numpy as np
import logging
import os
import joblib
import glob
from sklearn.metrics import classification_report
from continuous_engine import ContinuousPrimaryEngine
from labeling import TripleBarrierLabeler
from feature_extraction import FeatureExtraction
from meta_model import MetaModelEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_refined_data(price_path, synthetic_dir, real_funding_dir):
    """
    Loads price data, merges with Top Features and REAL funding rates.
    """
    logger.info(f"Loading primary price data from {price_path}...")
    df_price = pd.read_csv(price_path)
    df_price['timestamp'] = pd.to_datetime(df_price['datetime'])
    df_price.set_index('timestamp', inplace=True)
    df_price = df_price[['close', 'volume']]
    
    merged_df = df_price.copy()
    
    # 1. LOAD REAL FUNDING RATES (Priority over synthetic)
    funding_files = glob.glob(os.path.join(real_funding_dir, "*.csv"))
    if funding_files:
        logger.info(f"Loading {len(funding_files)} REAL funding files...")
        funding_dfs = []
        for f in funding_files:
            tmp = pd.read_csv(f)
            # Binance columns: calc_time, last_funding_rate
            tmp = tmp[['calc_time', 'last_funding_rate']]
            tmp.columns = ['timestamp', 'real_funding_rate']
            funding_dfs.append(tmp)
        
        df_real_funding = pd.concat(funding_dfs).sort_values('timestamp')
        df_real_funding['timestamp'] = pd.to_datetime(df_real_funding['timestamp'], unit='ms')
        df_real_funding.set_index('timestamp', inplace=True)
        
        merged_df = pd.merge_asof(merged_df.sort_index(), 
                                   df_real_funding.sort_index(), 
                                   left_index=True, 
                                   right_index=True, 
                                   direction='backward')
        # Fill missing with 0 (pre-2020)
        merged_df['real_funding_rate'] = merged_df['real_funding_rate'].fillna(0)
    else:
        merged_df['real_funding_rate'] = 0

    # 2. LOAD TOP EXTERNAL FEATURES (Based on previous run importance)
    top_features = [
        'btc_open_interest.csv',
        'btc_exchange_reserve.csv',
        'stablecoin_exchange_supply_ratio.csv',
        'btc_taker_buy_sell_ratio.csv'
    ]
    
    for filename in top_features:
        path = os.path.join(synthetic_dir, filename)
        if os.path.exists(path):
            logger.info(f"Merging Top Feature: {filename}...")
            df_feat = pd.read_csv(path)
            df_feat['timestamp'] = pd.to_datetime(df_feat['timestamp'])
            df_feat.set_index('timestamp', inplace=True)
            
            val_col = [c for c in df_feat.columns if c != 'timestamp'][0]
            merged_df = pd.merge_asof(merged_df.sort_index(), 
                                       df_feat[[val_col]].sort_index(), 
                                       left_index=True, 
                                       right_index=True, 
                                       direction='backward')
            
    return merged_df.dropna()

def run_research_pipeline():
    logger.info("--- STARTING KVANTO FONDO (HEDGE FUND) REFINED PIPELINE ---")
    
    # Paths
    BASE_DIR = r"C:\Users\Mr. Perfect\tradingbot\data"
    SYNTHETIC_DIR = os.path.join(BASE_DIR, "synthetic")
    REAL_FUND_DIR = r"C:\Users\Mr. Perfect\tradingbot\ML_Pipeline\03_features\extracted"
    PRICE_DATA = os.path.join(BASE_DIR, "BTCUSDT_2020_2022_dollar_bars.csv")
    
    # 1. Load Refined Data
    df = load_refined_data(PRICE_DATA, SYNTHETIC_DIR, REAL_FUND_DIR)
    
    # 2. Primary Engine
    primary = ContinuousPrimaryEngine(window=50, z_threshold=1.5)
    df_signals = primary.generate_signals(df)
    
    # 3. Labeling
    labeler = TripleBarrierLabeler(pt_sl_ratios=[1.0, 1.0], timeout_bars=20, min_ret=0.001)
    volatility = labeler.get_volatility(df_signals, span=100)
    events = labeler.get_events(df_signals, df_signals['primary_signal'], target=volatility)
    labels_df = labeler.apply_barriers(df_signals, events, pt_sl=[1.0, 1.0])
    
    # 4. Feature Extraction (Internal)
    extractor = FeatureExtraction()
    df_internal = extractor.generate_all_features(df_signals.copy())
    
    # 5. Prepare ML Dataset
    ml_dataset = df_internal.join(labels_df[['meta_label']], how='inner').dropna()
    
    # Join with external features from df
    # We use 'real_funding_rate' and the Top synthetic ones
    external_cols = [c for c in df.columns if c not in ['close', 'volume']]
    for col in external_cols:
        ml_dataset[col] = df.loc[ml_dataset.index, col]

    X = ml_dataset.drop(columns=['meta_label'])
    y = ml_dataset['meta_label']
    
    logger.info(f"Refined Feature Count: {len(X.columns)}")
    
    split_idx = int(len(X) * 0.7)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    # 6. Train Meta-Model
    meta_engine = MetaModelEngine(n_estimators=100, max_depth=5)
    meta_engine.train(X_train, y_train)
    
    # 7. Evaluate Performance
    y_pred_prob = meta_engine.predict_probability(X_test)
    y_pred = (y_pred_prob > 0.5).astype(int)
    
    logger.info("\n*** REFINED PERFORMANCE REPORT ***")
    print(classification_report(y_test, y_pred))
    
    # 8. Strategy Analysis
    bet_sizes = meta_engine.calculate_bet_size(y_pred_prob, method='continuous')
    test_prices = df.loc[X_test.index, 'close']
    test_returns = test_prices.pct_change().shift(-1).fillna(0)
    strategy_returns = test_returns * df_signals.loc[X_test.index, 'primary_signal'] * bet_sizes
    
    passed, sr_obs, emsr = meta_engine.evaluate_deflated_sharpe_ratio(strategy_returns, k_trials=1000)
    logger.info(f"Observed Sharpe: {sr_obs:.4f}")
    logger.info(f"DSR Passed: {passed}")
    
    # 9. SAVE FOR PRODUCTION
    joblib.dump(meta_engine.model, "meta_model.pkl")
    joblib.dump(list(X.columns), "feature_cols.joblib")
    logger.info("Refined model and features saved for live execution.")

if __name__ == "__main__":
    run_research_pipeline()
