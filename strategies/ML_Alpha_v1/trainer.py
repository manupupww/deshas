"""
ML Pipeline — Phase 5: Modelio Treniravimas
=============================================
Šis skriptas:
1. Sujungia FracDiff Dollar Bars + 30 sintetinių rodiklių + Labels + Sample Weights.
2. Treniruoja Random Forest (baseline) ir XGBoost (galingesnis) su Purged K-Fold CV.
3. Parodo Feature Importance (Top 15 svarbiausių rodiklių).
4. Eksportuoja geriausią modelį kaip .pkl failą backtesteriui.
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

# Pridedame 05_hygiene kelią, kad galėtume importuoti PurgedKFold
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '05_hygiene'))
from purged_cv import PurgedKFold

# ============================================================
# 1. DUOMENŲ SUJUNGIMAS
# ============================================================
def load_and_merge_data(data_dir):
    """
    Sujungia visus duomenų šaltinius į vieną DataFrame:
    - FracDiff Dollar Bars (kainos)
    - 30 sintetinių rodiklių (features)
    - Labels (Triple Barrier Method)
    - Sample Weights (Uniqueness)
    """
    print("=" * 60)
    print("1. DUOMENŲ SUJUNGIMAS")
    print("=" * 60)
    
    # --- A. FracDiff Dollar Bars ---
    bars_path = os.path.join(data_dir, "BTCUSDT_2020_2022_dollar_bars_fracdiff_d0.10.csv")
    print(f"\n📊 Kraunami Dollar Bars: {bars_path}")
    bars = pd.read_csv(bars_path)
    bars['timestamp'] = pd.to_numeric(bars['timestamp']).astype(np.int64)
    bars = bars.sort_values('timestamp').reset_index(drop=True)
    print(f"   Eilutės: {len(bars)}, Stulpeliai: {list(bars.columns)}")
    
    # Pasirenkame tik naudingus stulpelius iš bars (features)
    # open, high, low, close, volume jau yra geri features patys savaime
    base_features = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'dollar_volume', 'close_frac_diff_0.10']
    df = bars[base_features].copy()
    
    # --- B. Sintetiniai Rodikliai (30 CSV failų) ---
    synthetic_dir = os.path.join(data_dir, "synthetic")
    csv_files = sorted(glob.glob(os.path.join(synthetic_dir, "*.csv")))
    print(f"\n📈 Kraunami {len(csv_files)} sintetiniai rodikliai iš {synthetic_dir}/")
    
    for csv_path in csv_files:
        fname = os.path.basename(csv_path)
        feat = pd.read_csv(csv_path)
        feat['timestamp'] = pd.to_numeric(feat['timestamp']).astype(np.int64)
        feat = feat.sort_values('timestamp').reset_index(drop=True)
        
        # Gauname feature stulpelio pavadinimą (ne timestamp)
        feat_cols = [c for c in feat.columns if c != 'timestamp']
        
        # merge_asof: sulyginame pagal artimiausią timestamp
        df = pd.merge_asof(df, feat, on='timestamp', direction='nearest', tolerance=1000000)
        
    print(f"   Po sujungimo: {df.shape[0]} eilučių, {df.shape[1]} stulpelių")
    
    # --- C. Labels ---
    labels_path = os.path.join(data_dir, "labels", "BTCUSDT_labels.csv")
    print(f"\n🏷️  Kraunami Labels: {labels_path}")
    labels = pd.read_csv(labels_path)
    labels['timestamp'] = pd.to_numeric(labels['timestamp']).astype(np.int64)
    labels['end_timestamp'] = pd.to_numeric(labels['end_timestamp']).astype(np.int64)
    labels = labels.sort_values('timestamp').reset_index(drop=True)
    
    df = pd.merge_asof(df, labels, on='timestamp', direction='nearest', tolerance=1000000)
    
    # --- D. Sample Weights ---
    weights_path = os.path.join(data_dir, "labels", "BTCUSDT_sample_weights.csv")
    print(f"⚖️  Kraunami Sample Weights: {weights_path}")
    weights = pd.read_csv(weights_path)
    weights['timestamp'] = pd.to_numeric(weights['timestamp']).astype(np.int64)
    weights = weights.sort_values('timestamp').reset_index(drop=True)
    
    # Sujungiame tik uniqueness_weight (num_co_events jau nereikalingas modeliui)
    df = pd.merge_asof(df, weights[['timestamp', 'uniqueness_weight']], on='timestamp', direction='nearest', tolerance=1000000)
    
    # --- E. Valymas ---
    # Pašaliname eilutes be label (pvz., jei timestamp nesutapo)
    before = len(df)
    df = df.dropna(subset=['label'])
    # Pašaliname neutralius signalus (label == 0)
    df = df[df['label'] != 0].reset_index(drop=True)
    after = len(df)
    print(f"\n🧹 Pašalinta {before - after} eilučių be label arba su label=0")
    print(f"   Galutinis dataset: {after} eilučių, {df.shape[1]} stulpelių")
    
    # Label -> int (1 = Long, 0 = Short)
    df['label'] = (df['label'] == 1).astype(int)
    
    print(f"\n📊 Klasių pasiskirstymas:")
    print(f"   Long (1): {(df['label'] == 1).sum()} ({(df['label'] == 1).mean()*100:.1f}%)")
    print(f"   Short (0): {(df['label'] == 0).sum()} ({(df['label'] == 0).mean()*100:.1f}%)")
    
    return df

# ============================================================
# 2. FEATURE PARUOŠIMAS
# ============================================================
def prepare_features(df):
    """
    Paruošia X (features), y (labels), w (weights), ir meta duomenis CV.
    """
    # Stulpeliai, kurie NĖRA features (meta-duomenys)
    meta_cols = ['timestamp', 'end_timestamp', 'label', 'uniqueness_weight', 'datetime']
    
    feature_cols = [c for c in df.columns if c not in meta_cols]
    
    X = df[feature_cols].copy()
    y = df['label'].values
    w = df['uniqueness_weight'].fillna(1.0).values
    timestamps = df['timestamp']
    end_timestamps = df['end_timestamp']
    
    # Užpildome NaN su mediana (saugiau nei vidurkis dėl outlierių)
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    X = X.fillna(X.median())
    
    print(f"\n📋 Features sąrašas ({len(feature_cols)} stulpeliai):")
    for i, col in enumerate(feature_cols):
        print(f"   {i+1:2d}. {col}")
    
    return X, y, w, timestamps, end_timestamps, feature_cols

# ============================================================
# 3. MODELIO TRENIRAVIMAS SU PURGED CV
# ============================================================
def train_with_purged_cv(X, y, w, timestamps, end_timestamps, model_class, model_params, model_name, n_splits=5):
    """
    Treniruoja modelį su Purged K-Fold Cross Validation.
    Grąžina vidutinį tikslumą ir geriausio fold'o modelį.
    """
    print(f"\n{'=' * 60}")
    print(f"TRENIRAVIMAS: {model_name}")
    print(f"{'=' * 60}")
    
    cv = PurgedKFold(n_splits=n_splits, embargo_pct=0.01)
    
    fold_accuracies = []
    fold_models = []
    
    for fold, (train_idx, test_idx) in enumerate(cv.split(timestamps, end_timestamps)):
        # Paruošiame duomenis šiam foldui
        X_train = X.iloc[train_idx].values
        y_train = y[train_idx]
        w_train = w[train_idx]
        
        X_test = X.iloc[test_idx].values
        y_test = y[test_idx]
        
        n_dropped = len(X) - len(train_idx) - len(test_idx)
        
        # Treniruojame modelį
        model = model_class(**model_params)
        model.fit(X_train, y_train, sample_weight=w_train)
        
        # Testuojame
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        fold_accuracies.append(acc)
        fold_models.append(model)
        
        print(f"  Fold {fold+1}: Accuracy = {acc:.4f} | Train: {len(train_idx)} | Test: {len(test_idx)} | Dropped: {n_dropped}")
    
    mean_acc = np.mean(fold_accuracies)
    std_acc = np.std(fold_accuracies)
    best_fold = np.argmax(fold_accuracies)
    best_model = fold_models[best_fold]
    
    print(f"\n  📊 Vidutinis Accuracy: {mean_acc:.4f} ± {std_acc:.4f}")
    print(f"  🏆 Geriausias Fold: {best_fold + 1} (Accuracy: {fold_accuracies[best_fold]:.4f})")
    
    return best_model, mean_acc, std_acc

# ============================================================
# 4. FEATURE IMPORTANCE
# ============================================================
def show_feature_importance(model, feature_cols, model_name, top_n=15):
    """
    Parodo svarbiausius rodiklius pagal modelio feature importance.
    """
    print(f"\n{'=' * 60}")
    print(f"FEATURE IMPORTANCE: {model_name} (Top {top_n})")
    print(f"{'=' * 60}")
    
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    for rank, idx in enumerate(indices[:top_n]):
        bar = "█" * int(importances[idx] * 200)
        print(f"  {rank+1:2d}. {feature_cols[idx]:40s} {importances[idx]:.4f} {bar}")
    
    return importances

# ============================================================
# 5. MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="ML Pipeline Phase 5: Modelio Treniravimas")
    parser.add_argument("--data-dir", type=str, default=r"C:\Users\Mr. Perfect\tradingbot\data", help="Duomenų katalogas")
    parser.add_argument("--splits", type=int, default=5, help="K-Fold splits skaičius")
    parser.add_argument("--output-dir", type=str, default=r"C:\Users\Mr. Perfect\tradingbot\data\models", help="Modelio išsaugojimo vieta")
    args = parser.parse_args()
    
    # 1. Sujungiame duomenis
    df = load_and_merge_data(args.data_dir)
    
    # 2. Paruošiame features
    X, y, w, timestamps, end_timestamps, feature_cols = prepare_features(df)
    
    # 3. Random Forest (Baseline)
    rf_params = {
        'n_estimators': 500,        # 500 medžių "miškas"
        'max_depth': 6,             # Ribojame gylį, kad nepersimoktų
        'min_samples_leaf': 50,     # Min 50 pavyzdžių lape
        'max_features': 'sqrt',     # Kiekvienas medis mato tik sqrt(n) features
        'n_jobs': -1,               # Naudojame visus CPU branduolius
        'random_state': 42
    }
    rf_model, rf_acc, rf_std = train_with_purged_cv(
        X, y, w, timestamps, end_timestamps,
        RandomForestClassifier, rf_params, "Random Forest 🌲",
        n_splits=args.splits
    )
    
    # 4. XGBoost 
    try:
        from xgboost import XGBClassifier
        xgb_params = {
            'n_estimators': 500,
            'max_depth': 4,             # Mažesnis gylis nei RF (XGB mokosi iš klaidų, todėl greičiau persimoko)
            'learning_rate': 0.05,      # Lėtesnis mokymasis = stabilesnis
            'min_child_weight': 50,
            'subsample': 0.8,           # Naudoja tik 80% duomenų kiekvienam medžiui
            'colsample_bytree': 0.8,    # Naudoja tik 80% features kiekvienam medžiui
            'reg_alpha': 1.0,           # L1 regularizacija
            'reg_lambda': 1.0,          # L2 regularizacija
            'use_label_encoder': False,
            'eval_metric': 'logloss',
            'n_jobs': -1,
            'random_state': 42
        }
        xgb_model, xgb_acc, xgb_std = train_with_purged_cv(
            X, y, w, timestamps, end_timestamps,
            XGBClassifier, xgb_params, "XGBoost 🚀",
            n_splits=args.splits
        )
        has_xgb = True
    except ImportError:
        print("\n⚠️  XGBoost nerastas (pip install xgboost). Naudojamas tik Random Forest.")
        has_xgb = False
    
    # 5. Pasirenkame geriausią modelį
    print(f"\n{'=' * 60}")
    print("REZULTATŲ PALYGINIMAS")
    print(f"{'=' * 60}")
    print(f"  🌲 Random Forest:  {rf_acc:.4f} ± {rf_std:.4f}")
    
    best_model = rf_model
    best_name = "Random Forest"
    best_acc = rf_acc
    
    if has_xgb:
        print(f"  🚀 XGBoost:        {xgb_acc:.4f} ± {xgb_std:.4f}")
        if xgb_acc > rf_acc:
            best_model = xgb_model
            best_name = "XGBoost"
            best_acc = xgb_acc
    
    print(f"\n  🏆 NUGALĖTOJAS: {best_name} (Accuracy: {best_acc:.4f})")
    
    # 6. Feature Importance
    show_feature_importance(best_model, feature_cols, best_name)
    
    # 7. Eksportuojame modelį
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    model_path = os.path.join(args.output_dir, "best_model.pkl")
    joblib.dump({
        'model': best_model,
        'model_name': best_name,
        'accuracy': best_acc,
        'feature_cols': feature_cols,
    }, model_path)
    
    print(f"\n💾 Modelis išsaugotas: {model_path}")
    print(f"   Naudojimas backtesteryje:")
    print(f"   >>> data = joblib.load('{model_path}')")
    print(f"   >>> model = data['model']")
    print(f"   >>> features = data['feature_cols']")
    print(f"   >>> prediction = model.predict(X[features])")
    print(f"\n✅ Phase 5 BAIGTA!")

if __name__ == "__main__":
    main()
