import pandas as pd
import numpy as np
import logging
import joblib 
import os

from continuous_engine import ContinuousPrimaryEngine
from feature_extraction import FeatureExtraction
from meta_model import MetaModelEngine
from hrp_allocation import HRPPortfolioAllocator

class HybridLiveExecutor:
    """
    Live Execution Bot (Inference Mode Only)
    Uses pre-trained Meta-Model and feature definitions from Research Pipeline.
    """
    def __init__(self, model_path="meta_model.pkl", features_path="feature_cols.joblib", symbols=['BTC']):
        self.logger = logging.getLogger(__name__)
        self.symbols = symbols
        
        # Initialize modules
        self.primary_engine = ContinuousPrimaryEngine(window=50, z_threshold=1.5)
        self.feature_extractor = FeatureExtraction()
        self.allocator = HRPPortfolioAllocator()
        
        # Load Pre-trained Meta-Model
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                self.feature_cols = joblib.load(features_path)
                self.logger.info(f"SUCCESS: Loaded Meta-Model with {len(self.feature_cols)} features.")
                self.logger.info(f"Features: {self.feature_cols}")
            except Exception as e:
                self.logger.error(f"Failed to load production model: {e}")
                self.model = None
        else:
            self.logger.warning("No pre-trained model found. Bot will not be able to size trades.")
            self.model = None
            
        self.live_data = {sym: pd.DataFrame() for sym in symbols}
        self.base_weights = {sym: 1.0 / len(symbols) for sym in symbols}
        
    def on_new_bar(self, symbol: str, bar_data: dict, external_features: dict = None):
        """
        Triggered when a new Dollar Bar is constructed.
        'external_features' should contain keys like 'btc_funding_rates', 'btc_open_interest' etc.
        """
        # 1. Update Internal State
        new_bar = pd.DataFrame([bar_data])
        new_bar.set_index('timestamp', inplace=True)
        
        # Merge with external features if provided
        if external_features:
            for k, v in external_features.items():
                new_bar[k] = v
        
        if self.live_data[symbol].empty:
            self.live_data[symbol] = new_bar
        else:
            self.live_data[symbol] = pd.concat([self.live_data[symbol], new_bar])
            
        df = self.live_data[symbol]
        
        # 2. Check for Primary Signal
        signals_df = self.primary_engine.generate_signals(df)
        latest_signal = signals_df['primary_signal'].iloc[-1]
        
        if latest_signal == 0:
            return
            
        self.logger.info(f"[{symbol}] PRIMARY SIGNAL: {latest_signal} @ {df.index[-1]}")
        
        # 3. Extract Features for Meta-Model
        internal_feats = self.feature_extractor.generate_all_features(df)
        # Join internal with external (already in df)
        inference_row = internal_feats.iloc[[-1]].copy()
        for col in self.feature_cols:
            if col in df.columns and col not in inference_row.columns:
                inference_row[col] = df[col].iloc[-1]
        
        # 4. Meta-Inference (Bet Sizing)
        if self.model:
            try:
                # Ensure correct column order
                X = inference_row[self.feature_cols].fillna(0)
                prob = self.model.predict_proba(X)[:, 1][0]
                
                # Use MetaModelEngine's logic for sizing
                temp_engine = MetaModelEngine() # For the sizing function
                bet_size = temp_engine.calculate_bet_size(np.array([prob]))[0]
                
                self.logger.info(f"[{symbol}] Meta-Model Prob: {prob:.2%}, Bet Size: {bet_size:.2f}")
                
                if bet_size > 0:
                    weight = self.base_weights.get(symbol, 0)
                    final_alloc = weight * bet_size
                    self._execute_live_order(symbol, latest_signal, final_alloc)
                else:
                    self.logger.info(f"[{symbol}] TRADE FILTERED: Meta-Model confidence too low.")
            except Exception as e:
                self.logger.error(f"Inference Error: {e}")
        else:
            self.logger.warning("No model loaded. Taking signal with default size 1.0 (DANGEROUS)")
            self._execute_live_order(symbol, latest_signal, self.base_weights.get(symbol, 0))

    def _execute_live_order(self, symbol, direction, target_allocation):
        side = "BUY" if direction == 1 else "SELL"
        self.logger.info(f"*** ORDER SENT: {side} {symbol} | Portfolio Weight: {target_allocation:.2%} ***")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    bot = HybridLiveExecutor(symbols=['BTC'])
    
    # Simulate a few bars with external data inputs
    dummy_time = pd.Timestamp.now()
    for i in range(55): # Need enough for rolling windows
        bar = {'timestamp': dummy_time + pd.Timedelta(minutes=5*i), 'close': 50000 + i*10, 'volume': 100}
        ext = {'btc_funding_rates': 0.0001, 'btc_open_interest': 1000000}
        bot.on_new_bar('BTC', bar, external_features=ext if i > 50 else None)
