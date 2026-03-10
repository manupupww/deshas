import pandas as pd
import numpy as np
import os
import time

def generate_synthetic_ticks(n_ticks=100000, start_price=50000, volatility=0.0001, output_path="data/raw/ticks.csv"):
    """
    Generates synthetic tick data (Price, Volume, Timestamp) using a random walk.
    """
    print(f"Generating {n_ticks} synthetic ticks...")
    
    # Random walk for price
    price_changes = np.random.normal(loc=0, scale=volatility, size=n_ticks)
    prices = start_price * np.exp(np.cumsum(price_changes))
    
    # Random volume (log-normal distribution)
    volumes = np.random.lognormal(mean=2, sigma=1, size=n_ticks)
    
    # Timestamps (randomly distributed over a period)
    start_ts = int(time.time() * 1000)
    # Average 100ms between ticks
    ts_gaps = np.random.poisson(lam=100, size=n_ticks)
    timestamps = start_ts + np.cumsum(ts_gaps)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'price': prices,
        'volume': volumes
    })
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✅ Ticks saved to {output_path}")
    return df

if __name__ == "__main__":
    # Ensure we run from the project root
    generate_synthetic_ticks()
