import pandas as pd
import numpy as np

def get_weights_ffwd(d, size):
    """
    Fixed-Window Fractional Differentiation weights.
    d: differentiation order (e.g. 0.4)
    size: window size
    """
    w = [1.]
    for k in range(1, size):
        w_ = -w[-1] / k * (d - k + 1)
        w.append(w_)
    return np.array(w[::-1]).reshape(-1, 1)

def frac_diff_ffwd(series, d, threshold=1e-5):
    """
    Apply FFWD Fractional Differentiation to a series.
    series: pandas Series (e.g. 'close' price)
    d: differentiation order
    threshold: threshold for ignoring small weights
    """
    # 1. Determine window size based on threshold
    w = get_weights_ffwd(d, len(series))
    w_cum = np.cumsum(np.abs(w))
    w_cum /= w_cum[-1]
    skip = (w_cum < threshold).sum()
    w = w[skip:]
    
    # 2. Shift and dot product
    size = len(w)
    output = []
    for i in range(size - 1, len(series)):
        val = np.dot(w.T, series.values[i - size + 1: i + 1])[0]
        output.append(val)
    
    # Pad with NaNs
    res = pd.Series(np.nan, index=series.index)
    res.iloc[size - 1:] = output
    return res

if __name__ == "__main__":
    # Test with real data
    input_path = "C:/Users/Mr. Perfect/tradingbot/data/BTCUSDT_2020_2022_dollar_bars.csv"
    df = pd.read_csv(input_path)
    print(f"Applying FracDiff (d=0.2) to {len(df)} bars from {input_path}...")
    df['close_fd'] = frac_diff_ffwd(df['close'], d=0.2)
    print(df[['close', 'close_fd']].tail(10))
    df.to_csv("data/processed/dollar_bars_fd.csv", index=False)
    print("✅ Fractional differentiation complete.")
