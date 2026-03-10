import pandas as pd
import numpy as np
import os

def generate_primary_signals(input_path, output_path):
    """
    Implements a simple trend-following strategy (Z-Score of FracDiff) 
    to provide the 'side' for meta-labeling.
    """
    print(f"Generating primary signals from {input_path}...")
    df = pd.read_csv(input_path)
    
    # Use the existing fracdiff column in the file: close_frac_diff_0.20
    # If the user renamed it, we handle it
    target_col = 'close_frac_diff_0.20'
    if target_col not in df.columns:
        # Fallback to any close_frac_diff column
        cols = [c for c in df.columns if 'frac_diff' in c]
        if cols:
            target_col = cols[0]
        else:
            print(f"Error: {target_col} not found in {input_path}")
            return None

    window = 100 # Increased window for stability in large dataset
    df['mean_fd'] = df[target_col].rolling(window=window).mean()
    df['std_fd'] = df[target_col].rolling(window=window).std()
    df['z_score'] = (df[target_col] - df['mean_fd']) / df['std_fd']
    
    df['side'] = 0
    df.loc[df['z_score'] > 0, 'side'] = 1
    df.loc[df['z_score'] < 0, 'side'] = -1
    
    # Signal Probability (Sigmoid of z-score)
    df['side_prob'] = 1 / (1 + np.exp(-df['z_score']))
    
    # Save processed data with sides
    df = df.dropna()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✅ Primary signals saved to {output_path} (Rows: {len(df)})")
    return df

if __name__ == "__main__":
    # Use the full dataset instead of the truncated features.csv
    base_data = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020_2022_dollar_bars_fracdiff_d0.10.csv"
    generate_primary_signals(base_data, "data/processed/primary_signals.csv")
