import pandas as pd
import numpy as np
import os
import argparse

def get_dollar_bars(input_path, output_path, threshold=1000000):
    """
    Converts tick data into Dollar Bars.
    Each bar represents 'threshold' amount of dollar value (price * volume).
    """
    print(f"Sampling dollar bars from {input_path} with threshold {threshold}...")
    
    # Check if input exists
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return
        
    df = pd.read_csv(input_path)
    df['dv'] = df['price'] * df['volume']
    
    # Cumulative sum of dollar value
    df['cum_dv'] = df['dv'].cumsum()
    
    # Determine bar indices
    df['bar_id'] = (df['cum_dv'] / threshold).astype(int)
    
    # Aggregate into OHLCV bars
    bars = df.groupby('bar_id').agg({
        'timestamp': ['first', 'last'],
        'price': ['first', 'max', 'min', 'last'],
        'volume': 'sum',
        'dv': 'sum'
    })
    
    # Flatten columns
    bars.columns = [
        'timestamp_start', 'timestamp_end', 
        'open', 'high', 'low', 'close', 
        'volume', 'dollar_volume'
    ]
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bars.to_csv(output_path, index=False)
    print(f"✅ Created {len(bars)} dollar bars. Saved to {output_path}")
    return bars

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="data/raw/ticks.csv")
    parser.add_argument("--output", type=str, default="data/processed/dollar_bars.csv")
    parser.add_argument("--threshold", type=float, default=1000000)
    args = parser.parse_args()
    
    get_dollar_bars(args.input, args.output, args.threshold)
