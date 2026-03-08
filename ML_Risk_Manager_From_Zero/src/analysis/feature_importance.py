import pandas as pd
import numpy as np
import os
import sys
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Add src to path for imports
sys.path.append(os.path.abspath("src"))
from labeling.labeling import get_daily_vol, get_events, get_bins

def run_feature_analysis(primary_signals_path, features_path):
    print(f"Running Advanced Feature Analysis...")
    
    # 1. Load Data
    signals_df = pd.read_csv(primary_signals_path)
    features_df = pd.read_csv(features_path)
    
    signals_df['datetime'] = pd.to_datetime(signals_df['timestamp'], unit='ms')
    signals_df = signals_df.set_index('datetime')
    
    features_df['datetime'] = pd.to_datetime(features_df['timestamp'], unit='ms')
    features_df = features_df.set_index('datetime')
    
    # 2. Generate Meta-Labels
    print("Generating labels for analysis...")
    # Increase vertical barrier to 24 hours to capture more events in dollar bars
    t1 = pd.Series(signals_df.index + pd.Timedelta(hours=24), index=signals_df.index)
    
    vol = get_daily_vol(signals_df['close'])
    trgt = vol.reindex(signals_df.index).ffill().dropna()
    t_events = trgt.index # Only use points where we have volatility
    pt_sl = [1, 1]
    side = signals_df.loc[t_events, 'side']
    
    events = get_events(signals_df['close'], t_events, pt_sl, trgt, 0, 1, t1=t1, side=side)
    labels = get_bins(events, signals_df['close'])
    y = labels['bin']
    
    # 3. Align features and labels
    # Inner join to ensure we only have overlapping rows
    # We use features_df which now contains all 38+ features
    data = pd.concat([features_df, y.rename('label')], axis=1, join='inner').dropna()
    
    print(f"Data points after alignment: {len(data)}")
    if len(data) < 10:
        print("WARNING: Very small dataset. MDI/MDA might be unstable.")
    
    # Dynamically identify feature columns (exclude timestamp and label)
    feature_cols = [c for c in features_df.columns if c not in ['timestamp', 'datetime']]
    X = data[feature_cols]
    y = data['label']
    
    X_train = X.iloc[:int(len(X)*0.8)]
    y_train = y.iloc[:int(len(y)*0.8)]
    X_test = X.iloc[int(len(X)*0.8):]
    y_test = y.iloc[int(len(y)*0.8):]
    
    # 4. MDI (Mean Decrease Impurity)
    print("Calculating MDI (Global Importance)...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    clf.fit(X_train, y_train)
    mdi_importances = pd.Series(clf.feature_importances_, index=X.columns).sort_values(ascending=False)
    
    # 5. MDA (Mean Decrease Accuracy / Permutation Importance)
    print("Calculating MDA (Out-of-Sample Importance)...")
    result = permutation_importance(clf, X_test, y_test, n_repeats=10, random_state=42)
    mda_importances = pd.Series(result.importances_mean, index=X.columns).sort_values(ascending=False)
    
    # 6. PCA (Principal Component Analysis)
    print("Calculating PCA (Explained Variance)...")
    pca = PCA()
    pca.fit(X)
    evr = pca.explained_variance_ratio_
    cumulative_evr = np.cumsum(evr)
    
    # 7. Summary Report
    print("\n" + "="*50)
    print("FEATURE IMPORTANCE REPORT")
    print("="*50)
    
    report = pd.DataFrame({
        'MDI (In-Sample)': mdi_importances,
        'MDA (Out-of-Sample)': mda_importances
    }).sort_values(by='MDA (Out-of-Sample)', ascending=False)
    
    print(report)
    
    print("\n" + "="*50)
    print("PCA ANALYSIS (Redundancy Check)")
    print("="*50)
    print(f"Top 3 components explain {cumulative_evr[2]:.2%} of total variance.")
    print(f"Number of components to explain 95% variance: {np.argmax(cumulative_evr >= 0.95) + 1}")
    
    # Save report
    os.makedirs("data/analysis", exist_ok=True)
    report.to_csv("data/analysis/feature_importance.csv")
    print(f"\n✅ Analysis complete. Results saved to data/analysis/feature_importance.csv")

if __name__ == "__main__":
    # Use the newly merged features file with correct relative path
    run_feature_analysis("data/processed/primary_signals.csv", "../data/merged_features.csv")
