import pandas as pd
import numpy as np
import os

def get_daily_vol(close, span0=100):
    """
    Computes volatility for barrier sizing using daily returns.
    """
    # 1. Compute daily returns
    # We find the price 24h ago for each timestamp
    # For speed, we just use a fixed lag if many bars, or shift
    # Since we have dollar bars, 1 day offset is better
    df0 = close.index.searchsorted(close.index - pd.Timedelta(days=1))
    df0 = df0[df0 > 0]
    
    # Correct alignment:
    # close.iloc[df0] are prices 1 day ago for close.index[len(close)-len(df0):]
    # But let's do it simpler with pct_change on daily resampled or similar
    # or just a rolling standard deviation of log returns
    
    # AFML approach:
    # returns = close / close.shift(1) - 1
    # or better: 
    df0 = close.index.searchsorted(close.index - pd.Timedelta(days=1))
    df0 = df0[df0 > 0]
    # Prices at t and t-1day
    p_t = close.iloc[len(close)-len(df0):]
    p_t_minus_1 = close.iloc[df0[:len(p_t)]]
    
    returns = pd.Series(p_t.values.flatten() / p_t_minus_1.values.flatten() - 1, index=p_t.index)
    return returns.ewm(span=span0).std()

def apply_triple_barrier(df, events, pt_sl=[1, 1], num_days=10):
    """
    Labels events based on Triple-Barrier.
    """
    print("Applying Triple Barrier Labeling...")
    # 1. Volatility
    vol = get_daily_vol(df[['close']])
    
    # We'll use a more efficient way to scan future prices
    # For each event, we check the window [idx, idx + num_days]
    labels = []
    
    # Convert to numpy for much faster access
    times = df.index.values
    closes = df['close'].values
    
    for idx in events.index:
        # Get entry price and barriers
        row_idx = df.index.get_loc(idx)
        p0 = closes[row_idx]
        v = vol.get(idx, vol.iloc[-1])
        if np.isnan(v): v = 0.01
        
        up = p0 * (1 + pt_sl[0] * v)
        dn = p0 * (1 - pt_sl[1] * v)
        t1 = idx + pd.Timedelta(days=num_days)
        
        # Scan forward
        # Limit search to a reasonable number of bars for speed (e.g. 10000 bars)
        # 10 days in dollar bars is roughly 1300 bars
        limit = min(row_idx + 10000, len(df))
        
        label = 0 # default timeout
        for i in range(row_idx + 1, limit):
            t = times[i]
            p = closes[i]
            
            if t > np.datetime64(t1):
                break
            if p >= up:
                label = 1
                break
            elif p <= dn:
                label = 0 # Loss is 0 for meta-labeling (only profit is 1)
                break
        
        labels.append({'time': idx, 'label': label, 'vol': v})
        
    return pd.DataFrame(labels).set_index('time')

if __name__ == "__main__":
    output_dir = r"C:\Users\Mr. Perfect\tradingbot\strategies\BTC_HighLow_AFML"
    data_path = os.path.join(output_dir, "signals_raw.csv")
    events_path = os.path.join(output_dir, "entry_events.csv")
    
    if not os.path.exists(data_path) or not os.path.exists(events_path):
        print("ERROR: Previous step files missing. Run 01 and 02 first.")
        exit(1)
        
    print(f"Loading data...")
    df = pd.read_csv(data_path, index_col=0, parse_dates=True)
    events = pd.read_csv(events_path, index_col=0, parse_dates=True)
    
    # 1. Apply Triple Barrier
    labeled_events = apply_triple_barrier(df, events, pt_sl=[2, 2], num_days=10)
    
    # 2. Merge with features
    ml_data = events.join(labeled_events[['label', 'vol']], how='inner')
    
    # Add distance features
    ml_data['dist_max'] = (ml_data['close'] - ml_data['prev_max']) / ml_data['close']
    ml_data['dist_min'] = (ml_data['close'] - ml_data['prev_min']) / ml_data['close']
    
    output_path = os.path.join(output_dir, "labeled_ml_data.csv")
    ml_data.to_csv(output_path)
    print(f"Labeled data saved to {output_path}")
    print(f"Total labeled events: {len(ml_data)}")
    print(f"Win Rate (Label 1): {ml_data['label'].mean():.2%}")
