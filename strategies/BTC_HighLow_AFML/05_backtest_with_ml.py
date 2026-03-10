import pandas as pd
import numpy as np
import os
import joblib

def calculate_returns(signal_series, close_series, num_days=10):
    rets = []
    for i in range(len(signal_series)):
        if signal_series.iloc[i] != 0:
            side = signal_series.iloc[i]
            idx = signal_series.index[i]
            if idx not in close_series.index: continue
            
            p0 = close_series.loc[idx]
            t1 = idx + pd.Timedelta(days=num_days)
            # Find the slice after entry
            future = close_series.loc[idx:][1:]
            if future.empty: continue
            
            # Find where time > t1
            exit_target = future.index.searchsorted(t1)
            p1 = future.iloc[exit_target] if exit_target < len(future) else future.iloc[-1]
            rets.append(side * (p1 / p0 - 1))
    return rets

if __name__ == "__main__":
    output_dir = r"C:\Users\Mr. Perfect\tradingbot\strategies\BTC_HighLow_AFML"
    raw_path = os.path.join(output_dir, "processed_data.csv")
    sig_path = os.path.join(output_dir, "signals_raw.csv")
    model_path = os.path.join(output_dir, "meta_model.pkl")
    features_path = os.path.join(output_dir, "features.pkl")
    
    print("Loading data...")
    # Read raw data ONLY for the close price to compute vol
    df_raw = pd.read_csv(raw_path, index_col=0, parse_dates=True)
    # Read signals which already has close_fd, prev_max, etc.
    df_sig = pd.read_csv(sig_path, index_col=0, parse_dates=True)
    
    model = joblib.load(model_path)
    feature_cols = joblib.load(features_path)
    
    # 1. Recompute volatility for all bars
    def get_daily_vol(close, span0=100):
        df0 = close.index.searchsorted(close.index - pd.Timedelta(days=1))
        df0 = df0[df0 > 0]
        p_t = close.iloc[len(close)-len(df0):]
        p_t_minus_1 = close.iloc[df0[:len(p_t)]]
        returns = pd.Series(p_t.values.flatten() / p_t_minus_1.values.flatten() - 1, index=p_t.index)
        return returns.ewm(span=span0).std()

    df_raw['vol'] = get_daily_vol(df_raw[['close']])
    
    # 2. Join volatility to signals (avoiding duplicating columns that already exist)
    # df_sig already has close, close_fd, prev_max, prev_min
    full_df = df_sig.join(df_raw[['vol']], how='inner')
    
    # 3. Features
    full_df['dist_max'] = (full_df['close'] - full_df['prev_max']) / full_df['close']
    full_df['dist_min'] = (full_df['close'] - full_df['prev_min']) / full_df['close']
    
    # 4. Filter and Predict
    sig_mask = full_df['signal'] != 0
    df_to_test = full_df[sig_mask][feature_cols].dropna()
    
    if not df_to_test.empty:
        full_df.loc[df_to_test.index, 'ml_prob'] = model.predict_proba(df_to_test)[:, 1]
    
    # Primary vs Filtered
    full_df['filtered_signal'] = full_df['signal']
    # Higher threshold for better quality (0.55)
    full_df.loc[full_df['ml_prob'] < 0.55, 'filtered_signal'] = 0
    
    # 5. Result
    print("\n--- BTC AFML HYPOTHESIS TESTING ---")
    orig = calculate_returns(full_df['signal'], full_df['close'])
    ml = calculate_returns(full_df['filtered_signal'], full_df['close'])
    
    print(f"BASELINE: {len(orig)} trades, Avg Ret: {np.mean(orig):.4%}, SR-Proxy: {np.mean(orig)/np.std(orig):.4f}")
    print(f"AFML UPGRADE: {len(ml)} trades, Avg Ret: {np.mean(ml):.4%}, SR-Proxy: {np.mean(ml)/np.std(ml):.4f}")
    
    improvement = (np.mean(ml)/np.mean(orig)-1) * 100
    print(f"\nEXPECTANCY IMPROVEMENT: {improvement:+.2f}%")
    print(f"Precision Boost: {(np.array(ml)>0).mean() - (np.array(orig)>0).mean():+.2%}")
