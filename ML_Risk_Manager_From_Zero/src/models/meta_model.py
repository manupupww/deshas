import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import sys

# Add src to path for imports
sys.path.append(os.path.abspath("src"))
from labeling.labeling import get_daily_vol, get_events, get_bins

def train_meta_model(primary_signals_path, features_path, output_model_path):
    print(f"Training Meta-Model using {primary_signals_path}...")
    
    # 1. Load Data
    signals_df = pd.read_csv(primary_signals_path)
    features_df = pd.read_csv(features_path)
    
    # Primary signals are our base for events
    # We need timestamps for the Triple-Barrier
    signals_df['datetime'] = pd.to_datetime(signals_df['timestamp'], unit='ms')
    signals_df = signals_df.set_index('datetime')
    
    # 2. Triple-Barrier Labeling (Meta-Labeling)
    print("Applying Triple-Barrier Labeling for Meta-Labels...")
    vol = get_daily_vol(signals_df['close'])
    
    # Use Snippet 3.6 logic (Simplified for From Zero)
    # Target is volatility
    trgt = vol.dropna()
    t_events = trgt.index
    
    # Define barriers
    pt_sl = [2, 1] # 2x vol for profit take, 1x for stop loss
    t1 = pd.Series(signals_df.index + pd.Timedelta(days=5), index=signals_df.index) # 5 day vertical barrier
    
    # Side is from our primary model
    side = signals_df['side']
    
    events = get_events(signals_df['close'], t_events, pt_sl, trgt, 0.005, 1, t1=t1, side=side)
    if events.empty:
        print("CRITICAL: No events found for labeling. Adjust thresholds or signals.")
        return None
        
    labels = get_bins(events, signals_df['close'])
    
    # y = Meta-Label (1 if success, 0 if failure/neutral)
    y = labels['bin']
    
    # 3. Feature Preparation
    # Align features with labels
    features_df['datetime'] = pd.to_datetime(features_df['timestamp'], unit='ms')
    features_df = features_df.set_index('datetime')
    
    # Merge X and y into one frame to drop NaNs together
    data = pd.concat([features_df, y.rename('label')], axis=1).dropna()
    X = data.drop('label', axis=1)
    y = data['label']
    
    # 4. Train Risk Model (Random Forest)
    split = int(len(X) * 0.7)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    
    if len(X_train) == 0:
        print("CRITICAL: Training set is empty after NaN removal.")
        return None
    
    print(f"Training on {len(X_train)} samples, testing on {len(X_test)}...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    clf.fit(X_train, y_train)
    
    # 5. Evaluate
    preds = clf.predict(X_test)
    probs = clf.predict_proba(X_test)[:, 1]
    
    print("\nMeta-Model Evaluation:")
    print(classification_report(y_test, preds))
    
    # 6. Feature Importance
    print("\n" + "="*30)
    print("FEATURE IMPORTANCE (Top Indicators)")
    print("="*30)
    importances = pd.Series(clf.feature_importances_, index=X.columns).sort_values(ascending=False)
    print(importances)
    
    # Save results with metadata for backtesting
    results_df = X_test.copy()
    results_df['actual_label'] = y_test
    results_df['meta_prob'] = probs
    
    # Align side and returns from signals_df using the same index
    results_df['side'] = signals_df.reindex(results_df.index)['side']
    results_df['returns'] = signals_df.reindex(results_df.index)['returns']
    
    results_df.to_csv("data/processed/meta_results.csv")
    print(f"✅ Meta-Model results saved to data/processed/meta_results.csv")
    return clf

if __name__ == "__main__":
    train_meta_model("data/processed/primary_signals.csv", "data/processed/features.csv", "data/processed/meta_model.joblib")
