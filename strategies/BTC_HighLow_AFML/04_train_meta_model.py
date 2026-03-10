import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

if __name__ == "__main__":
    output_dir = r"C:\Users\Mr. Perfect\tradingbot\strategies\BTC_HighLow_AFML"
    data_path = os.path.join(output_dir, "labeled_ml_data.csv")
    
    if not os.path.exists(data_path):
        print(f"ERROR: Data file {data_path} not found. Run 01-03 first.")
        exit(1)
        
    print(f"Loading labeled data from {data_path}...")
    df = pd.read_csv(data_path, index_col=0, parse_dates=True)
    
    # Define features
    # 'close_fd' is the frac-diff version of close
    # 'vol' is the volatility
    # 'dist_max', 'dist_min' are distances from breakouts
    feature_cols = ['close_fd', 'vol', 'dist_max', 'dist_min']
    
    X = df[feature_cols].dropna()
    y = df.loc[X.index, 'label']
    
    print(f"Training on {len(X)} samples. Win rate in data: {y.mean():.2%}")
    
    # Train Random Forest
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X, y)
    
    y_pred = model.predict(X)
    print("\nModel Performance (In-Sample):")
    print(classification_report(y, y_pred))
    
    # Save model
    model_path = os.path.join(output_dir, "meta_model.pkl")
    joblib.dump(model, model_path)
    print(f"Meta-model saved to {model_path}")
    
    # Save feature names
    joblib.dump(feature_cols, os.path.join(output_dir, "features.pkl"))
