import pandas as pd
import numpy as np
import ccxt
import os
from datetime import datetime, timedelta

def download_data(symbol='BTC/USDT', timeframe='1m', days=30):
    print(f"Downloading {days} days of {timeframe} data for {symbol}...")
    exchange = ccxt.binance()
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    all_ohlcv = []
    
    while since < exchange.milliseconds():
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1
        print(f"Fetched until {exchange.iso8601(since)}")
        
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def create_dollar_bars(df, dollar_threshold=1000000):
    print(f"Creating Dollar Bars with threshold ${dollar_threshold}...")
    df['dollar_vol'] = df['close'] * df['volume']
    df['cum_dollar_vol'] = df['dollar_vol'].cumsum()
    
    bars = []
    last_cum_vol = 0
    
    for i in range(len(df)):
        if df['cum_dollar_vol'].iloc[i] - last_cum_vol >= dollar_threshold:
            bars.append(df.iloc[i])
            last_cum_vol = df['cum_dollar_vol'].iloc[i]
            
    res = pd.DataFrame(bars)
    print(f"Generated {len(res)} Dollar Bars from {len(df)} 1m candles.")
    return res

def get_weights_ffd(d, threshold, size):
    w = [1.0]
    for k in range(1, size):
        w_ = -w[-1] / k * (d - k + 1)
        if abs(w_) < threshold:
            break
        w.append(w_)
    return np.array(w[::-1]).reshape(-1, 1)

def frac_diff_ffd(series, d, threshold=1e-5):
    weights = get_weights_ffd(d, threshold, len(series))
    width = len(weights) - 1
    df = {}
    for name in series.columns:
        series_f = series[name].fillna(method='ffill').dropna()
        res = pd.Series(index=series_f.index, dtype=float)
        for iloc in range(width, series_f.shape[0]):
            loc = series_f.index[iloc]
            if not np.isfinite(series_f.loc[loc]):
                continue
            res.loc[loc] = np.dot(weights.T, series_f.iloc[iloc - width : iloc + 1])[0]
        df[name] = res.copy()
    return pd.DataFrame(df)

if __name__ == "__main__":
    # Settings
    symbol = 'BTC/USDT'
    output_dir = "strategies/MAReversal_v1_ML"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Download
    raw_data = download_data(symbol=symbol, days=30)
    raw_data.to_csv(f"{output_dir}/raw_1m_data.csv")
    
    # 2. Dollar Bars
    # Find average 1m dollar volume to set threshold
    avg_vol = (raw_data['close'] * raw_data['volume']).mean()
    threshold = avg_vol * 60 # Roughly 1-hour bars equivalent
    dollar_bars = create_dollar_bars(raw_data, dollar_threshold=threshold)
    dollar_bars.to_csv(f"{output_dir}/dollar_bars.csv")
    
    # 3. Frac Diff (only on Close for now)
    print("Applying Fractional Differentiation...")
    # We use a small d (0.3) for Close to keep memory
    close_df = dollar_bars[['close']]
    fd_close = frac_diff_ffd(close_df, d=0.3)
    
    # Merge back
    dollar_bars['close_fd'] = fd_close['close']
    dollar_bars.to_csv(f"{output_dir}/processed_data.csv")
    print(f"Data Engineering complete. Saved to {output_dir}/processed_data.csv")
