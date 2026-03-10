"""
03_meta_labeling.py - Meta-Labeling Model Training
===================================================
This script trains a secondary ML model (Random Forest) that predicts
whether the Primary Model's signal will be CORRECT.

AFML Role: Meta-Labeling (Chapter 3 + Chapter 10 Bet Sizing)
- Input: Primary signal + features (SMA distance, volatility, volume, etc.)
- Output: Probability of success -> used for Bet Sizing
"""
import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# --- Purged K-Fold (simplified AFML Chapter 7) ---
class PurgedKFold:
    """
    Cross-validation with purging and embargo for financial data.
    Prevents data leakage from overlapping labels.
    """
    def __init__(self, n_splits=5, embargo_pct=0.01):
        self.n_splits = n_splits
        self.embargo_pct = embargo_pct
    
    def split(self, X):
        n = len(X)
        embargo = int(n * self.embargo_pct)
        fold_size = n // self.n_splits
        
        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = min((i + 1) * fold_size, n)
            
            # Training: everything except test + embargo zone
            train_mask = np.ones(n, dtype=bool)
            # Purge: remove test period
            train_mask[test_start:test_end] = False
            # Embargo: remove post-test buffer
            embargo_end = min(test_end + embargo, n)
            train_mask[test_end:embargo_end] = False
            
            train_idx = np.where(train_mask)[0]
            test_idx = np.arange(test_start, test_end)
            
            yield train_idx, test_idx


def create_meta_features(df_signals, labeled_data):
    """
    Create features for the Meta-Labeling model.
    These features describe the CONTEXT of each signal.
    """
    features = []
    
    for _, row in labeled_data.iterrows():
        entry_time = row['entry_time']
        if entry_time not in df_signals.index:
            # Try parsing
            entry_time = pd.Timestamp(entry_time)
            if entry_time not in df_signals.index:
                continue
        
        loc = df_signals.index.get_loc(entry_time)
        if loc < 50:
            continue
        
        window = df_signals.iloc[loc-50:loc+1]
        
        feat = {
            'signal': row['signal'],
            'vol': row['vol'],
            # Distance from MAs (normalized)
            'dist_fast': (window['close'].iloc[-1] - window['sma_fast'].iloc[-1]) / window['close'].iloc[-1],
            'dist_slow': (window['close'].iloc[-1] - window['sma_slow'].iloc[-1]) / window['close'].iloc[-1],
            # Momentum
            'ret_5': window['close'].pct_change(5).iloc[-1],
            'ret_10': window['close'].pct_change(10).iloc[-1],
            'ret_20': window['close'].pct_change(20).iloc[-1],
            # Volatility regime
            'vol_ratio': window['close'].pct_change().rolling(5).std().iloc[-1] / \
                         window['close'].pct_change().rolling(20).std().iloc[-1] if \
                         window['close'].pct_change().rolling(20).std().iloc[-1] > 0 else 1,
            # Volume trend
            'vol_sma_ratio': window['volume'].iloc[-1] / window['volume'].rolling(20).mean().iloc[-1] if \
                             window['volume'].rolling(20).mean().iloc[-1] > 0 else 1,
            # Label (binary: 1 = profit, 0 = loss/timeout)
            'meta_label': 1 if row['barrier_label'] == 1 else 0,
        }
        features.append(feat)
    
    return pd.DataFrame(features)


def train_meta_model(meta_df):
    """
    Train Random Forest Meta-Model with Purged K-Fold CV.
    Returns trained model and performance metrics.
    """
    feature_cols = ['signal', 'vol', 'dist_fast', 'dist_slow', 
                    'ret_5', 'ret_10', 'ret_20', 'vol_ratio', 'vol_sma_ratio']
    
    X = meta_df[feature_cols].fillna(0).values
    y = meta_df['meta_label'].values
    
    # Purged K-Fold Cross-Validation
    cv = PurgedKFold(n_splits=5, embargo_pct=0.02)
    scores = []
    
    print("Training Meta-Model with Purged K-Fold CV...")
    for fold, (train_idx, test_idx) in enumerate(cv.split(X)):
        model = RandomForestClassifier(
            n_estimators=500,
            max_depth=5,
            min_samples_leaf=10,
            class_weight='balanced',
            random_state=42 + fold
        )
        model.fit(X[train_idx], y[train_idx])
        score = accuracy_score(y[test_idx], model.predict(X[test_idx]))
        scores.append(score)
        print(f"  Fold {fold+1}: Accuracy = {score:.4f}")
    
    print(f"  Mean CV Accuracy: {np.mean(scores):.4f} (+/- {np.std(scores):.4f})")
    
    # Train final model on all data
    final_model = RandomForestClassifier(
        n_estimators=500,
        max_depth=5,
        min_samples_leaf=10,
        class_weight='balanced',
        random_state=42
    )
    final_model.fit(X, y)
    
    # Feature importance
    importances = pd.Series(final_model.feature_importances_, index=feature_cols)
    print("\nFeature Importance:")
    for feat, imp in importances.sort_values(ascending=False).items():
        print(f"  {feat}: {imp:.4f}")
    
    return final_model, np.mean(scores)


if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load data from previous step
    signals_path = os.path.join(output_dir, "signals_with_ma.csv")
    labels_path = os.path.join(output_dir, "labeled_data.csv")
    
    if not os.path.exists(signals_path) or not os.path.exists(labels_path):
        print("ERROR: Run 02_primary_model.py first to generate signals and labels.")
        exit(1)
    
    df_signals = pd.read_csv(signals_path, parse_dates=[0], index_col=0)
    labeled = pd.read_csv(labels_path)
    
    # 1. Create Meta-Features
    meta_df = create_meta_features(df_signals, labeled)
    print(f"Created {len(meta_df)} meta-labeled samples")
    print(f"  Win rate: {meta_df['meta_label'].mean():.2%}")
    
    # 2. Train Meta-Model
    model, cv_score = train_meta_model(meta_df)
    
    # 3. Save model
    model_path = os.path.join(output_dir, "meta_model.pkl")
    joblib.dump(model, model_path)
    print(f"\nMeta-Model saved to {model_path}")
    
    # 4. Save meta features for backtesting
    meta_df.to_csv(os.path.join(output_dir, "meta_features.csv"), index=False)
