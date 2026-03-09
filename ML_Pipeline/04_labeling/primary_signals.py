import pandas as pd
import numpy as np
import os
import argparse

def generate_primary_signals(input_file, synthetic_dir, out_path):
    print(f"Loading base data: {input_file}")
    # AFML UPGRADE: Handling headerless BTC Dollar Bars with FracDiff (8 columns)
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'dollar_volume', 'close_fracdiff']
    df = pd.read_csv(input_file, names=cols, header=None)
    
    # Isitikiname, kad skaiciai yra skaiciai
    for c in ['open', 'high', 'low', 'close', 'volume', 'dollar_volume', 'close_fracdiff']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        
    # Isitikiname, kad timestamp yra skaicius (ms)
    df['dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['dt'])
    df['timestamp'] = (df['dt'].view('int64') // 10**6).astype(np.int64)
    
    # Load required features
    features_to_load = ['rolling_max_240', 'sma_20', 'sma_50', 'bb_lower', 'bb_upper']
    for feat in features_to_load:
        feat_path = os.path.join(synthetic_dir, f"{feat}.csv")
        if os.path.exists(feat_path):
            feat_df = pd.read_csv(feat_path)
            # Standartizuojam feat_df timestamp
            feat_df['timestamp'] = feat_df['timestamp'].astype(np.int64)
            df = pd.merge(df, feat_df, on='timestamp', how='left')
        else:
            print(f"WARNING: Feature {feat} not found in {synthetic_dir}")

    # 1. 10-day MAX Breakthrough (Momentum)
    # Signal: 1 only on the first bar it hits or exceeds the max
    df['signal_max'] = ((df['close'] >= df['rolling_max_240']) & (df['close'].shift(1) < df['rolling_max_240'].shift(1))).astype(int)
    
    # 2. MA Crossover Strategy (Trend)
    # Signal: 1 only on the golden cross (SMA 20 crosses above SMA 50)
    df['ma_cross_up'] = (df['sma_20'] > df['sma_50']) & (df['sma_20'].shift(1) <= df['sma_50'].shift(1))
    df['signal_ma'] = df['ma_cross_up'].astype(int)
    
    # 3. Bollinger Bands Strategy (Mean Reversion)
    # Signal: 1 only when it crosses below the lower band
    df['signal_bb'] = ((df['close'] <= df['bb_lower']) & (df['close'].shift(1) > df['bb_lower'].shift(1))).astype(int)

    # 4. Composite Strategy (Trend + Mean Reversion Filter)
    # Signal: Buy on BB cross-down only if SMA 20 > SMA 50 (Trend is up)
    df['signal_composite'] = ((df['signal_bb'] == 1) & (df['sma_20'] > df['sma_50'])).astype(int)

    # Save signals
    output_cols = ['timestamp', 'close', 'signal_max', 'signal_ma', 'signal_bb', 'signal_composite']
    # Filter only where at least one signal is active for efficiency, 
    # but Triple Barrier usually needs the whole series context? 
    # Actually, we need to know WHERE the signals occur to apply barriers.
    
    if not os.path.exists(os.path.dirname(out_path)):
        os.makedirs(os.path.dirname(out_path))
        
    df[output_cols].to_csv(out_path, index=False)
    print(f"✅ Primary signals saved to: {out_path}")
    
    print("\nSignal Distribution:")
    for col in ['signal_max', 'signal_ma', 'signal_bb']:
        print(f"{col}:")
        print(df[col].value_counts())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Base dollar bars CSV path")
    parser.add_argument("--synthetic_dir", type=str, default="../../data/synthetic", help="Dir with feature CSVs")
    parser.add_argument("--output", type=str, default="../../data/signals/primary_signals.csv", help="Output signals path")
    args = parser.parse_args()
    
    generate_primary_signals(os.path.abspath(args.input), os.path.abspath(args.synthetic_dir), os.path.abspath(args.output))
