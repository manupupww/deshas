import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

# Configuration
DATA_PATH = "../../data/judas_training_data.csv"
MODEL_PATH = "judas_model.pkl"

def train_model():
    print(f"📂 Loading training data: {DATA_PATH}")
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: {DATA_PATH} not found. Run judas_features.py first.")
        return

    df = pd.read_csv(DATA_PATH)
    
    # Define Features and Target
    # We drop 'price' and 'atr' because they are absolute values that change with time,
    # better to focus on relative features like liquidations and SMA alignment.
    features = ['is_long', 'volume', 'long_liquidations', 'short_liquidations', 'minute_of_session', 'sma_trend_1h']
    X = df[features]
    y = df['target_high_tp']

    print(f"📊 Dataset size: {len(df)} samples")
    print(f"📈 Class balance (Success=1): {y.mean():.2%}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("🚀 Training Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)

    # Evaluation
    y_pred = model.predict(X_test)
    print("\n📝 Evaluation Report:")
    print(classification_report(y_test, y_pred))

    # Save model
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"✅ Model saved to: {MODEL_PATH}")
    
    # Feature Importance
    importance = pd.DataFrame({'feature': features, 'importance': model.feature_importances_})
    print("\n📊 Feature Importance:")
    print(importance.sort_values(by='importance', ascending=False))

if __name__ == "__main__":
    train_model()
