"""
BTC Strategy Backtest with ML Filtering
Compares Baseline (Primary) vs ML-Filtered performance.
"""

import pandas as pd
import numpy as np
import os
import sys
import glob
import joblib
import argparse
from datetime import datetime

def load_data(data_dir, signals_path):
    print("=" * 60)
    print("1. LOADING DATA & SIGNALS")
    print("=" * 60)
    
    # A. Dollar Bars + FracDiff
    bars_path = os.path.join(data_dir, "BTCUSDT_2020-2025dollarBars__fracdiff_d0.10.csv")
    print(f"Loading Bars: {bars_path}")
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'dollar_volume', 'close_fracdiff']
    df = pd.read_csv(bars_path, names=cols, header=None)
    
    # Isitikiname, kad skaiciai yra skaiciai
    for c in ['open', 'high', 'low', 'close', 'volume', 'dollar_volume', 'close_fracdiff']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp_dt'])
    df['ms'] = (df['timestamp_dt'].view('int64') // 10**6).astype(np.int64)
    df = df.sort_values('ms').reset_index(drop=True)
    
    # B. Load Primary Signals
    print(f"Loading Signals: {signals_path}")
    signals_df = pd.read_csv(signals_path)
    signals_df['timestamp'] = signals_df['timestamp'].astype(np.int64)
    
    # Drop 'close' from signals if it exists to avoid close_x/close_y
    if 'close' in signals_df.columns:
        signals_df = signals_df.drop(columns=['close'])
    
    # C. Merge
    df = pd.merge_asof(df, signals_df.sort_values('timestamp'), 
                       left_on='ms', right_on='timestamp', direction='nearest', tolerance=1000000)
                
    return df

def calculate_metrics(returns, df, strategy_name):
    if len(returns) == 0:
        return None
    
    # 1. Pagrindiniai skaiciai
    total_return = (1 + returns).prod() - 1
    win_rate = (returns > 0).mean()
    profit_factor = returns[returns > 0].sum() / abs(returns[returns < 0].sum()) if len(returns[returns < 0]) > 0 else np.inf
    
    # 2. Laiko matavimas (apytikslis metinis skaiciavimas)
    # Kadangi naudojame Dollar Bars, laikas nera tiesinis.
    # Pirmas baras vs Paskutinis baras
    duration_days = (df['timestamp_dt'].max() - df['timestamp_dt'].min()).days
    if duration_days <= 0: duration_days = 1
    
    # CAGR (Cumulative Annual Growth Rate)
    cagr = (1 + total_return) ** (365 / duration_days) - 1
    
    # Sharpe Ratio (metinis)
    # Apytiksliai tarkime 24 barai per diena (labai priklauso nuo likvidumo)
    # Bet geriau naudoti standartini annualization 365*24
    vol_ann = returns.std() * np.sqrt(365 * 24)
    sharpe = (returns.mean() * 365 * 24) / vol_ann if vol_ann > 0 else 0
    
    # Drawdown skaiciavimas
    equity_curve = (1 + returns).cumprod()
    rolling_max = equity_curve.cummax()
    drawdowns = (equity_curve - rolling_max) / rolling_max
    max_dd = drawdowns.min()
    
    return {
        "Duration (Days)": duration_days,
        "Total Return (%)": total_return * 100,
        "CAGR (%)": cagr * 100,
        "Sharpe Ratio": sharpe,
        "Max Drawdown (%)": max_dd * 100,
        "Trades": len(returns),
        "Win Rate (%)": win_rate * 100,
        "Avg Trade (%)": returns.mean() * 100,
        "Profit Factor": profit_factor,
        "Best Trade (%)": returns.max() * 100,
        "Worst Trade (%)": returns.min() * 100
    }

def backtest(df, init_sl=0.02, tp_trigger=0.03, trail_percent=0.02):
    print("\n" + "=" * 60)
    print("2. RUNNING TRAILING STOP BACKTEST (NON-ML)")
    print(f"Settings: SL={init_sl*100}%, TP_Trigger={tp_trigger*100}%, Trail={trail_percent*100}%")
    print("=" * 60)
    
    strategies = ['signal_max', 'signal_ma', 'signal_bb', 'signal_composite']
    
    for strat in strategies:
        if strat not in df.columns: continue
        
        signals = df[df[strat] == 1].index
        trade_returns = []
        
        for idx in signals:
            if idx + 200 >= len(df): continue
            
            entry_price = df['close'].iloc[idx]
            current_sl = entry_price * (1 - init_sl)
            max_price = entry_price
            in_trade = True
            trade_ret = 0
            
            # Simuliuojame sandori bar po baro
            for j in range(idx + 1, idx + 500): # Ilgesnis horizontas "leisti laimetojui judeti"
                if j >= len(df): break
                
                price = df['close'].iloc[j]
                
                # Atnaujiname auksciausia kaina
                if price > max_price:
                    max_price = price
                    
                # Atnaujiname Trailing SL jei pasiektas TP Trigger
                # Arba tiesiog trailiname nuo pat pradziu, bet uztikriname kad SL nekrenta
                new_sl = max_price * (1 - trail_percent)
                if new_sl > current_sl:
                    current_sl = new_sl
                
                # Tikriname Isėjimo sąlygas
                if price <= current_sl:
                    trade_ret = current_sl / entry_price - 1
                    in_trade = False
                    break
                
                # Jei norime griezto TP ties 3%, bet useris sako "leisti judeti",
                # tai mes tiesiog trailiname. Jei pasiekia 3%, SL jau bus ties 1% (3% - 2% trail).
                
            if in_trade: # Jei vis dar trade po 500 baru
                trade_ret = df['close'].iloc[j-1] / entry_price - 1
                
            trade_returns.append(trade_ret)
            
        metrics = calculate_metrics(pd.Series(trade_returns), df, strat)
        
        if metrics:
            print(f"\n📈 RESULTS FOR: {strat.upper()}")
            print("-" * 30)
            for k, v in metrics.items():
                if isinstance(v, float):
                    print(f"{k:20}: {v:>10.2f}")
                else:
                    print(f"{k:20}: {v:>10}")
            print("-" * 30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="../../data")
    parser.add_argument("--signals", default="../../data/signals/primary_signals.csv")
    args = parser.parse_args()
    
    if not os.path.exists(args.signals):
        print(f"❌ KLAIDA: Signalai nerasti {args.signals}")
        sys.exit(1)
        
    df = load_data(args.data_dir, args.signals)
    backtest(df)
