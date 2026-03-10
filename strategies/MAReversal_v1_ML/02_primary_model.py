"""
02_primary_model.py - MA Reversal Primary Signal Generator
==========================================================
This script generates PRIMARY trading signals using the MA Crossover logic
from the original "Moon Dev" strategy. These signals are the RAW hypothesis -
they will later be filtered by a Meta-Labeling model.

AFML Role: This is the "Primary Model" (Chapter 3) - it generates events.
"""
import pandas as pd
import numpy as np
import os

def generate_ma_signals(df, ma_fast=20, ma_slow=40):
    """
    Generate primary MA crossover signals.
    
    Logic (from original strategy):
    - LONG  (1): Price > SMA_fast AND Price > SMA_slow
    - SHORT (-1): Price > SMA_fast AND Price < SMA_slow
    - NONE  (0): No signal
    """
    df = df.copy()
    df['sma_fast'] = df['close'].rolling(window=ma_fast).mean()
    df['sma_slow'] = df['close'].rolling(window=ma_slow).mean()
    df.dropna(inplace=True)
    
    # Generate signals
    conditions_long = (df['close'] > df['sma_fast']) & (df['close'] > df['sma_slow'])
    conditions_short = (df['close'] > df['sma_fast']) & (df['close'] < df['sma_slow'])
    
    df['signal'] = 0
    df.loc[conditions_long, 'signal'] = 1
    df.loc[conditions_short, 'signal'] = -1
    
    # Keep only signal CHANGES (entry points)
    df['signal_shift'] = df['signal'].shift(1)
    df['entry'] = 0
    df.loc[(df['signal'] != df['signal_shift']) & (df['signal'] != 0), 'entry'] = df['signal']
    
    entries = df[df['entry'] != 0].copy()
    print(f"Generated {len(entries)} entry signals (Long: {(entries['entry']==1).sum()}, Short: {(entries['entry']==-1).sum()})")
    return df, entries


def apply_triple_barrier(df, entries, pt_sl=[1, 1], min_ret=0.005, num_days=10):
    """
    Triple-Barrier Method (AFML Chapter 3).
    
    For each entry signal, we check which barrier is hit first:
    - Upper barrier (Take Profit): +pt * daily_vol
    - Lower barrier (Stop Loss): -sl * daily_vol
    - Vertical barrier (Timeout): num_days bars later
    
    Returns labels: 1 (profit), -1 (loss), 0 (timeout)
    """
    # Calculate daily volatility
    daily_vol = df['close'].pct_change().rolling(window=50).std()
    
    labels = []
    for idx in entries.index:
        loc = df.index.get_loc(idx)
        if loc + num_days >= len(df):
            continue
            
        entry_price = df['close'].iloc[loc]
        vol = daily_vol.iloc[loc]
        if np.isnan(vol) or vol == 0:
            continue
            
        # Barrier levels
        upper = entry_price * (1 + pt_sl[0] * vol)
        lower = entry_price * (1 - pt_sl[1] * vol)
        
        # Check future prices
        future = df['close'].iloc[loc+1 : loc+1+num_days]
        
        # Find first touch
        label = 0  # default: timeout
        for i, price in enumerate(future):
            if price >= upper:
                label = 1
                break
            elif price <= lower:
                label = -1
                break
        
        labels.append({
            'entry_time': idx,
            'entry_price': entry_price,
            'signal': entries.loc[idx, 'entry'],
            'barrier_label': label,
            'vol': vol
        })
    
    result = pd.DataFrame(labels)
    if len(result) > 0:
        print(f"\nTriple-Barrier Results:")
        print(f"  Profit (1):  {(result['barrier_label']==1).sum()}")
        print(f"  Loss (-1):   {(result['barrier_label']==-1).sum()}")
        print(f"  Timeout (0): {(result['barrier_label']==0).sum()}")
    return result


if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try to load processed Dollar Bars
    data_path = os.path.join(output_dir, "processed_data.csv")
    if not os.path.exists(data_path):
        # Fallback: use existing Dollar Bars from project
        data_path = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020_2022_dollar_bars.csv"
        print(f"Using fallback data: {data_path}")
    
    df = pd.read_csv(data_path, parse_dates=[0], index_col=0)
    
    # Standardize column names
    col_map = {c: c.lower() for c in df.columns}
    df.rename(columns=col_map, inplace=True)
    
    # 1. Generate Primary Signals
    df_signals, entries = generate_ma_signals(df, ma_fast=20, ma_slow=40)
    
    # 2. Apply Triple-Barrier
    labeled = apply_triple_barrier(df_signals, entries, pt_sl=[2, 2], num_days=20)
    
    # 3. Save
    df_signals.to_csv(os.path.join(output_dir, "signals_with_ma.csv"))
    labeled.to_csv(os.path.join(output_dir, "labeled_data.csv"), index=False)
    print(f"\nSaved signals and labels to {output_dir}")
