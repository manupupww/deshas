import pandas as pd
import numpy as np

def generate_features(input_path, output_path):
    """
    Generates technical features for the Meta-Model.
    Follows AFML philosophy: focus on statistical properties and microstructure.
    """
    print(f"Generating expanded features from {input_path}...")
    df = pd.read_csv(input_path)
    
    # Ensure timestamp is datetime for rolling operations if needed, 
    # but here we rely on integer index for simple bars
    
    # 1. Returns & Log Returns
    df['returns'] = df['close'].pct_change()
    df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
    
    # 2. Volatility (Standard Deviation)
    df['volatility_20'] = df['returns'].rolling(window=20).std()
    df['volatility_50'] = df['returns'].rolling(window=50).std()
    
    # 3. Serial Correlation (Memory) (Optimized speed)
    df['autocorr_1'] = df['returns'].rolling(window=20).corr(df['returns'].shift(1))
    df['autocorr_5'] = df['returns'].rolling(window=20).corr(df['returns'].shift(5))
    
    # 4. Moments (Skewness & Kurtosis) - Detects non-normality
    df['skew_20'] = df['returns'].rolling(window=20).skew()
    df['kurt_20'] = df['returns'].rolling(window=20).kurt()
    
    # 5. Momentum (Velocity)
    df['mom_5'] = df['close'].pct_change(periods=5)
    df['mom_10'] = df['close'].pct_change(periods=10)
    
    # 6. Volume Dynamics
    df['log_volume'] = np.log(df['volume'] + 1)
    df['vol_pct_chg'] = df['volume'].pct_change()
    
    # 7. Z-Score Normalization (prevents scale bias in some ML models)
    feature_cols = ['volatility_20', 'volatility_50', 'autocorr_1', 'autocorr_5', 
                    'skew_20', 'kurt_20', 'mom_5', 'mom_10', 'log_volume', 'vol_pct_chg']
    
    for col in feature_cols:
        df[col] = (df[col] - df[col].mean()) / df[col].std()

    # Drop intermediate and NaN rows
    df = df.dropna()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✅ Enhanced features ({len(feature_cols)}) saved to {output_path}")
    return df

if __name__ == "__main__":
    import os
    generate_features("data/processed/dollar_bars_fd.csv", "data/processed/features.csv")
