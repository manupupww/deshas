import pandas as pd
import numpy as np
import os
import argparse

def get_volatility(close, span=100):
    returns = np.log(close / close.shift(1)).fillna(0)
    vol = returns.ewm(span=span).std()
    return vol

def apply_triple_barrier_vectorized(df, signal_col, pt_sl=[2, 2], horizon=100):
    """
    Simpler version for speed: only looks at indices where signal == 1
    """
    close = df['close'].values
    ts = df['timestamp'].values
    vol = df['vol'].values
    indices = df.index[df[signal_col] == 1].tolist()
    n = len(df)
    
    results = []
    
    print(f"Labeling {len(indices)} signals for {signal_col}...")
    
    for i in indices:
        if i >= n - 1: continue
        
        target_vol = vol[i]
        upper_barrier = close[i] * (1 + target_vol * pt_sl[0])
        lower_barrier = close[i] * (1 - target_vol * pt_sl[1])
        
        t1 = min(i + horizon, n - 1)
        
        label = 0
        end_ts = ts[t1]
        
        for j in range(i + 1, t1 + 1):
            if close[j] >= upper_barrier:
                label = 1
                end_ts = ts[j]
                break
            elif close[j] <= lower_barrier:
                label = -1
                end_ts = ts[j]
                break
        
        results.append({
            'timestamp': ts[i],
            'end_timestamp': end_ts,
            'label': label,
            'start_price': close[i],
            'end_price': close[j] if label != 0 else close[t1]
        })
        
    return pd.DataFrame(results)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--signals", type=str, required=True, help="Path to primary_signals.csv")
    parser.add_argument("--output_dir", type=str, default="../../data/labels", help="Output directory")
    args = parser.parse_args()
    
    if not os.path.exists(args.signals):
        print(f"Error: {args.signals} not found")
        return
        
    df = pd.read_csv(args.signals)
    print("Calculating volatility...")
    df['vol'] = get_volatility(df['close'])
    
    strategies = {
        'signal_max': 'max_10d',
        'signal_ma': 'ma_crossover',
        'signal_bb': 'bollinger_reversion'
    }
    
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        
    for sig_col, name in strategies.items():
        # Using institucional standard multipliers: 2.0 PT, 1.0 SL
        labels_df = apply_triple_barrier_vectorized(df, sig_col, pt_sl=[2.0, 1.0], horizon=24*5) # 5 days horizon if hourly
        
        out_file = os.path.join(args.output_dir, f"labels_{name}.csv")
        labels_df.to_csv(out_file, index=False)
        print(f"✅ Labels for {name} saved to {out_file}")
        print("Distribution:")
        print(labels_df['label'].value_counts(normalize=True))
        print("-" * 30)

if __name__ == "__main__":
    main()
