import pandas as pd
import os
import glob
from pathlib import Path

def merge_features():
    base_path = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020_2022_dollar_bars_fracdiff_d0.10.csv"
    synthetic_dir = r"C:\Users\Mr. Perfect\tradingbot\data\synthetic"
    output_path = r"C:\Users\Mr. Perfect\tradingbot\data\merged_features.csv"

    print(f"Loading base data: {base_path}")
    df = pd.read_csv(base_path)
    
    # Ensure timestamp is consistent (float ms)
    df['timestamp'] = df['timestamp'].astype(float)
    
    synthetic_files = glob.glob(os.path.join(synthetic_dir, "*.csv"))
    print(f"Found {len(synthetic_files)} synthetic files.")

    # Sort base for asof merge
    df = df.sort_values('timestamp')

    for file_path in synthetic_files:
        feature_name = Path(file_path).stem
        print(f"Merging {feature_name}...")
        
        feature_df = pd.read_csv(file_path)
        feature_df['timestamp'] = feature_df['timestamp'].astype(float)
        feature_df = feature_df.sort_values('timestamp')
        
        # Determine the feature column (all columns except timestamp)
        val_cols = [c for c in feature_df.columns if c != 'timestamp']
        if not val_cols:
            print(f"Warning: No value column in {file_path}. Skipping.")
            continue
            
        # Merge using asof (align to previous synthetic point)
        df = pd.merge_asof(df, feature_df[['timestamp'] + val_cols], on='timestamp', direction='backward')

    print(f"Initial row count: {len(df)}")
    # Drop rows with NaNs (where synthetic features might not exist)
    df_cleaned = df.dropna()
    print(f"Cleaned row count: {len(df_cleaned)}")

    if len(df_cleaned) < 100:
        print("Warning: Very few rows remaining after merge. Check timestamp alignment.")
    
    df_cleaned.to_csv(output_path, index=False)
    print(f"Merged features saved to {output_path}")

if __name__ == "__main__":
    merge_features()
