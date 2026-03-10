import pandas as pd
import numpy as np
import os
import sys
# Add parent directory to path to find engines
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ict_judas_engine import ICTJudasEngine

# Configuration
DATA_PATH = "../../data/BTC_1min_upsampled.csv"
OUTPUT_PATH = "../../data/judas_training_data.csv"

def generate_training_data():
    print(f"📊 Loading data: {DATA_PATH}")
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: {DATA_PATH} not found.")
        return

    df = pd.read_csv(DATA_PATH)
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)

    print("🔍 Generating signals for labeling...")
    engine = ICTJudasEngine(df)
    buy_sig, sell_sig, atr = engine.get_signals(utc_offset=4)
    
    df['buy_sig'] = buy_sig
    df['sell_sig'] = sell_sig
    df['atr'] = atr

    # Features and Labels collection
    features_list = []
    
    # SL/TP parameters for labeling (targets)
    # We want to label if a trade reaches 3.0x ATR (High Reward) before SL (6.5x ATR)
    TARGET_TP_MULT = 3.0
    SL_MULT = 6.5
    LOOKAHEAD = 240 # Check next 4 hours (240 minutes)

    print("🧪 Extracting features and labels from signals...")
    
    # Indices where signals occur
    buy_indices = np.where(buy_sig == 1)[0]
    sell_indices = np.where(sell_sig == 1)[0]

    def get_target(entry_idx, entry_price, sl_price, tp_price, is_long):
        # Scan future candles
        future_data = df.iloc[entry_idx+1 : entry_idx+1+LOOKAHEAD]
        for _, row in future_data.iterrows():
            if is_long:
                if row['low'] <= sl_price: return 0 # Failed
                if row['high'] >= tp_price: return 1 # Success
            else:
                if row['high'] <= tp_price: return 1 # Success
                if row['low'] >= sl_price: return 0 # Failed
        return 0 # Timed out / No clear result

    for idx in np.concatenate([buy_indices, sell_indices]):
        row = df.iloc[idx]
        is_long = row['buy_sig'] == 1
        price = row['close']
        atr_val = row['atr']
        
        if np.isnan(atr_val) or atr_val <= 0: continue

        # Calculate Targets
        if is_long:
            sl = price - (atr_val * SL_MULT)
            tp = price + (atr_val * TARGET_TP_MULT)
        else:
            sl = price + (atr_val * SL_MULT)
            tp = price - (atr_val * TARGET_TP_MULT)

        target = get_target(idx, price, sl, tp, is_long)

        # Extract Features (Snapshot at signal time)
        feat = {
            'is_long': 1 if is_long else 0,
            'price': price,
            'atr': atr_val,
            'volume': row['volume'],
            'long_liquidations': row['long_liquidations'],
            'short_liquidations': row['short_liquidations'],
            # Session relative time
            'minute_of_session': row.name.hour * 60 + row.name.minute - (9 * 60 + 30), # Minutes since 09:30
            # Target
            'target_high_tp': target
        }
        
        # Add HTF context (simple 1h trend proxy using 60-period MA)
        # Note: In a real scenario, we'd use 1h resampled data
        feat['sma_trend_1h'] = 1 if price > df['close'].rolling(60).mean().iloc[idx] else 0
        
        features_list.append(feat)

    training_df = pd.DataFrame(features_list)
    print(f"✅ Generated {len(training_df)} samples. Success rate: {training_df['target_high_tp'].mean():.2%}")
    
    training_df.to_csv(OUTPUT_PATH, index=False)
    print(f"💾 Saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_training_data()
