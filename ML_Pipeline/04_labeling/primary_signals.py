import pandas as pd
import numpy as np
import os
import argparse

def generate_primary_signals(input_file, synthetic_dir, out_path):
    print(f"Loading base data: {input_file}")
    df = pd.read_csv(input_file)
    
    # Load required features
    features_to_load = ['rolling_max_240', 'sma_20', 'sma_50', 'bb_lower', 'bb_upper']
    for feat in features_to_load:
        feat_path = os.path.join(synthetic_dir, f"{feat}.csv")
        if os.path.exists(feat_path):
            feat_df = pd.read_csv(feat_path)
            df = pd.merge(df, feat_df, on='timestamp', how='left')
        else:
            print(f"WARNING: Feature {feat} not found in {synthetic_dir}")

    # 1. 10-day MAX Strategy (Momentum)
    # Signal: 1 if close hits or exceeds 10-day max
    df['signal_max'] = 0
    df.loc[df['close'] >= df['rolling_max_240'], 'signal_max'] = 1
    
    # 2. MA Crossover Strategy (Trend)
    # Signal: 1 if SMA 20 > SMA 50
    df['signal_ma'] = 0
    df.loc[df['sma_20'] > df['sma_50'], 'signal_ma'] = 1
    
    # 3. Bollinger Bands Strategy (Mean Reversion)
    # Signal: 1 if close is below the lower band
    df['signal_bb'] = 0
    df.loc[df['close'] <= df['bb_lower'], 'signal_bb'] = 1

    # 4. Composite Strategy (Trend + Mean Reversion Filter)
    # Signal: Buy on BB lower only if SMA 20 > SMA 50 (Trend is up)
    df['signal_composite'] = 0
    df.loc[(df['close'] <= df['bb_lower']) & (df['sma_20'] > df['sma_50']), 'signal_composite'] = 1

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
