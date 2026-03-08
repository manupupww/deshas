import pandas as pd
import logging
from live_executor import HybridLiveExecutor
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_live_bot():
    logger.info("--- PRODUCTION VERIFICATION: DRY-RUNNING LIVE EXECUTOR ---")
    
    # 1. Initialize Bot with Pre-trained Model
    model_path = "meta_model.pkl"
    feature_path = "feature_cols.joblib"
    
    bot = HybridLiveExecutor(model_path=model_path, features_path=feature_path, symbols=['BTC'])
    
    # 2. Load some real data to simulate a stream
    price_data_path = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020_2022_dollar_bars.csv"
    if not os.path.exists(price_data_path):
        logger.error("Price data not found for verification.")
        return
        
    df = pd.read_csv(price_data_path).head(100) # Only first 100 for verification
    df['timestamp'] = pd.to_datetime(df['datetime'])
    
    # 3. Simulate Feed
    logger.info("Streaming 100 bars through the bot...")
    count = 0
    for idx, row in df.iterrows():
        bar = {
            'timestamp': row['timestamp'],
            'close': row['close'],
            'volume': row['volume']
        }
        # Simulate some external features (constant for demo)
        ext = {
            'btc_funding_rates': 0.0001,
            'btc_open_interest': 1000000000,
            'btc_exchange_reserve': 2000000
        }
        bot.on_new_bar('BTC', bar, external_features=ext)
        count += 1
        
    logger.info(f"Verification stream complete. Processed {count} bars.")
    logger.info("Check logs above for 'PRIMARY SIGNAL' and 'EXECUTE TRADE' events.")

if __name__ == "__main__":
    verify_live_bot()
