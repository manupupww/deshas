import pandas as pd
import numpy as np
import os
from scipy.signal import lfilter

def get_weights_ffd(d, threshold, size):
    """
    Fixed-window fractional difference weights.
    """
    w = [1.0]
    for k in range(1, size):
        w_ = -w[-1] / k * (d - k + 1)
        if abs(w_) < threshold:
            break
        w.append(w_)
    return np.array(w)

def frac_diff_ffd_vectorized(series, d, threshold=1e-5):
    """
    Apply Fractional Differentiation using vectorized convolution.
    Much faster for large series.
    """
    w = get_weights_ffd(d, threshold, len(series))
    # Using np.convolve or scipy.signal.lfilter for vectorization
    # But for FFD with fixed window, we can use rolling dot product or generic convolution
    
    # Simple vectorized convolution for FFD:
    res = np.convolve(series.values.flatten(), w, mode='valid')
    
    # Pad the beginning with NaNs to match original length
    # Convolution with 'valid' mode returns length L - len(w) + 1
    pad_size = len(series) - len(res)
    res_padded = np.append(np.full(pad_size, np.nan), res)
    
    return pd.Series(res_padded, index=series.index)

if __name__ == "__main__":
    input_path = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020-2025dollarBars_.csv"
    output_dir = r"C:\Users\Mr. Perfect\tradingbot\strategies\BTC_HighLow_AFML"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading Dollar Bars from {input_path}...")
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'dollar_volume']
    df = pd.read_csv(input_path, names=cols, parse_dates=['timestamp'])
    
    # Deduplicate timestamps if any (common in tick-to-bar conversion)
    df = df.drop_duplicates(subset='timestamp').set_index('timestamp')
    
    print(f"Applying Vectorized FracDiff to {len(df)} rows...")
    df['close_fd'] = frac_diff_ffd_vectorized(df[['close']], d=0.3)
    
    df.dropna(inplace=True)
    
    output_path = os.path.join(output_dir, "processed_data.csv")
    df.to_csv(output_path)
    print(f"Data Prepared and saved to {output_path}")
    print(f"Processed {len(df)} rows.")
