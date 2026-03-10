"""
BTC Meta-Labeling Training Script
Customized for BTCUSDT Dollar Bars and Synthetic Features
"""

import pandas as pd
import numpy as np
import os
import sys
import glob
import argparse
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, log_loss

# Add hygiene path for PurgedKFold
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '05_hygiene'))
try:
    from purged_cv import PurgedKFold
except ImportError:
    print("WARNING: PurgedKFold not found in 05_hygiene. Using standard KFold fallback.")
    from sklearn.model_selection import KFold as PurgedKFold

def load_and_merge_data(data_dir):
    print("=" * 60)
    print("1. BTC DATA MERGING")
    print("=" * 60)
    
    # A. FracDiff Dollar Bars
    bars_path = os.path.join(data_dir, "BTCUSDT_2020-2025dollarBars__fracdiff_d0.10.csv")
    print(f"\n📊 Loading Dollar Bars: {bars_path}")
    # Fix: FracDiff file has 8 columns (including the diffed close)
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'dollar_volume', 'close_fracdiff']
    df_bars = pd.read_csv(bars_path, names=cols, header=None)
    
    # Isitikiname, kad timestamp yra skaicius (ms)
    df_bars['timestamp_dt'] = pd.to_datetime(df_bars['timestamp'], errors='coerce')
    df_bars = df_bars.dropna(subset=['timestamp_dt'])
    df_bars['ms'] = (df_bars['timestamp_dt'].view('int64') // 10**6).astype(np.int64)
    df_bars = df_bars.sort_values('ms').reset_index(drop=True)
    
    # B. Features
    synthetic_dir = os.path.join(data_dir, "synthetic")
    csv_files = sorted(glob.glob(os.path.join(synthetic_dir, "*.csv")))
    print(f"\n📈 Loading {len(csv_files)} features from {synthetic_dir}...")
    
    for csv_path in csv_files:
        feat_name = os.path.basename(csv_path).replace(".csv", "")
        feat_df = pd.read_csv(csv_path)
        feat_df['timestamp'] = feat_df['timestamp'].astype(np.int64)
        feat_df = feat_df.sort_values('timestamp').reset_index(drop=True)
        # Merge by timestamp
        df_bars = pd.merge_asof(df_bars, feat_df, left_on='ms', right_on='timestamp', direction='nearest', tolerance=1000000)
        # Cleanup redundant timestamp
        if 'timestamp_y' in df_bars.columns:
            df_bars.drop(columns=['timestamp_y'], inplace=True)
            df_bars.rename(columns={'timestamp_x': 'timestamp'}, inplace=True)
        elif 'timestamp' in feat_df.columns:
             # If merge_asof created a timestamp_y, handle it
             pass

    # C. Labels
    labels_path = os.path.abspath(os.path.join(data_dir, "labels", "BTCUSDT_labels.csv"))
    print(f"\n🏷️  Loading Labels: {labels_path}")
    if not os.path.exists(labels_path):
        print(f"KLAIDA: Nerastas labels failas: {labels_path}")
        return None
        
    try:
        # AFML FIX: Try reading with a more robust handle 
        # and checking if it's open elsewhere
        labels = pd.read_csv(labels_path)
    except PermissionError:
        print(f"\n❌ KLAIDA: Negaliu pasiekti failo {labels_path}.")
        print("Tikriausiai jis atidarytas kitoje programoje (pvz. Excel) arba labeling skriptas dar nebaige darbo.")
        print("Sprendimas: Uzdarykite Excel/failu narsykle ir bandykite vel.\n")
        return None
        
    labels['timestamp'] = labels['timestamp'].astype(np.int64)
    labels['end_timestamp'] = labels['end_timestamp'].astype(np.int64)
    
    df_bars = pd.merge_asof(df_bars, labels, left_on='ms', right_on='timestamp', direction='nearest', tolerance=1000000)
    
    # Cleanup
    df_bars = df_bars.dropna(subset=['label'])
    # Meta-labeling logic: 1 if success (PT), 0 if failure (SL/TS)
    # Triple barrier output: 1 (PT), -1 (SL), 0 (TS). 
    # For meta-labeling we want to know if it hit PT (1) or NOT (0)
    df_bars['target'] = (df_bars['label'] == 1).astype(int)
    
    print(f"\nTarget distribution:")
    print(df_bars['target'].value_counts(normalize=True))
    
    return df_bars

def train(df, output_path):
    # Exclude non-features
    meta = ['timestamp', 'timestamp_dt', 'ms', 'label', 'end_timestamp', 'target', 
            'open', 'high', 'low', 'close', 'volume', 'dollar_volume', 
            'timestamp_x', 'timestamp_y', 'datetime']
    
    # Tikriname tik skaicinius stulpelius ir tuos, kurie nera meta
    features = [c for c in df.columns if c not in meta and pd.api.types.is_numeric_dtype(df[c])]
    
    print(f"\nTraining with {len(features)} features...")
    # Atspausdiname kelis, kad matytume ar viskas gerai
    print(f"Sample features: {features[:5]}")
    
    X = df[features].fillna(0)
    # Isitikiname, kad visos reiksmes yra float/int
    X = X.apply(pd.to_numeric, errors='coerce').fillna(0)
    
    y = df['target'].values
    ts = df['ms'].values
    ets = df['end_timestamp'].values
    
    print(f"\nTraining with {len(features)} features...")
    
    # Using standard KFold or Purged if available
    cv = PurgedKFold(n_splits=5)
    
    model = RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42)
    scores = []
    
    for train_idx, test_idx in cv.split(ts, ets):
        X_train, X_test = X.iloc[train_idx].values, X.iloc[test_idx].values
        y_train, y_test = y[train_idx], y[test_idx]
        
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        scores.append(accuracy_score(y_test, pred))
        
    print(f"Mean Accuracy: {np.mean(scores):.4f}")
    
    # Final fit
    model.fit(X.values, y)
    
    # Feature Importance
    print("\nTop Features:")
    importances = model.feature_importances_
    idx = np.argsort(importances)[::-1][:10]
    for i in idx:
        print(f"{features[i]}: {importances[i]:.4f}")
        
    joblib.dump({'model': model, 'features': features}, output_path)
    print(f"\nModel saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="../../data")
    parser.add_argument("--output", default="../../data/models/btc_meta_model.pkl")
    args = parser.parse_args()
    
    df = load_and_merge_data(os.path.abspath(args.data_dir))
    if df is not None:
        train(df, os.path.abspath(args.output))
    else:
        print("\n❌ KLAIDA: Duomenu krovimas nepavyko. Sutvarkykite klaidas ir bandykite vel.")
