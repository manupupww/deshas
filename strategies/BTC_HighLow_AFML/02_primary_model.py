import pandas as pd
import numpy as np
import os

def generate_trend_events(df, lookback_days=10):
    """
    Identifies entry events based on N-day High/Low.
    """
    df = df.copy()
    
    # Since we are in Dollar Bars, we use time-based rolling
    # The index must be DatetimeIndex (which it is from Step 1)
    
    # Calculate N-day High/Low
    # We use a 1-day offset to avoid lookahead bias (current bar close vs PREVIOUS N-day high)
    df['rolling_max'] = df['high'].rolling(window=f'{lookback_days}D').max()
    df['rolling_min'] = df['low'].rolling(window=f'{lookback_days}D').min()
    
    # Shift so we compare current close with previous high/low
    df['prev_max'] = df['rolling_max'].shift(1)
    df['prev_min'] = df['rolling_min'].shift(1)
    
    df['signal'] = 0
    # Long if close >= prev_max (breakout)
    df.loc[df['close'] >= df['prev_max'], 'signal'] = 1
    # Short if close <= prev_min (breakout)
    df.loc[df['close'] <= df['prev_min'], 'signal'] = -1
    
    # Events are points where signal != 0
    events = df[df['signal'] != 0].copy()
    
    print(f"Generated {len(events)} events (Long: {(events['signal']==1).sum()}, Short: {(events['signal']==-1).sum()})")
    return df, events

if __name__ == "__main__":
    output_dir = r"C:\Users\Mr. Perfect\tradingbot\strategies\BTC_HighLow_AFML"
    data_path = os.path.join(output_dir, "processed_data.csv")
    
    if not os.path.exists(data_path):
        print(f"ERROR: Data file {data_path} not found. Run 01_data_preparation.py first.")
        exit(1)
        
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path, index_col=0, parse_dates=True)
    
    # 1. Generate Signal Events
    df_with_signals, events = generate_trend_events(df, lookback_days=10)
    
    # 2. Save
    df_with_signals.to_csv(os.path.join(output_dir, "signals_raw.csv"))
    events.to_csv(os.path.join(output_dir, "entry_events.csv"))
    
    print(f"Signals and events saved to {output_dir}")
