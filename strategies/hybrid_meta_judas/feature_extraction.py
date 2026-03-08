import numpy as np
import pandas as pd
import logging

class FeatureExtraction:
    """
    Advanced Feature Extraction for the Meta-Model
    Implements AFML concepts: Fractional Differentiation, Entropy, VPIN approximation.
    These features represent the memory and structural state of the market, helping the 
    Meta-Model decide whether to size up or down a primary signal.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def frac_diff_ffd(self, series, d, thres=1e-5):
        """
        Fractionally Differentiated features, Fixed Window (FFD) Method
        Produces a stationary series with maximum memory retention.
        """
        w = [1.0]
        k = 1
        while True:
            w_ = -w[-1] / k * (d - k + 1)
            if abs(w_) < thres:
                break
            w.append(w_)
            k += 1
            
        w = np.array(w[::-1]).reshape(-1, 1)
        width = len(w)
        
        df = {}
        # Apply weights to the series
        for name in series.columns:
            seriesF = series[[name]].bfill().ffill()
            series_res = pd.Series(index=series.index, dtype='float64')
            
            for i in range(width - 1, len(seriesF)):
                series_res.iloc[i] = np.dot(w.T, seriesF.iloc[i - width + 1:i + 1])[0, 0]
                
            df[name] = series_res.copy(deep=True)
            
        df = pd.concat(df, axis=1)
        return df

    def shannon_entropy(self, series, window=50, bins=10):
        """
        Calculate Rolling Shannon Entropy.
        Measures the amount of "information" or randomness in the price series.
        """
        def calculate_entropy(x):
            hist, _ = np.histogram(x, bins=bins, density=True)
            hist = hist[hist > 0]
            return -np.sum(hist * np.log2(hist))
            
        return series.rolling(window=window).apply(calculate_entropy, raw=True)
        
    def calculate_vpin_approximation(self, df, volume_col='volume', price_col='close', window=50):
        """
        Approximate Volume-Synchronized Probability of Informed Trading (VPIN).
        This is a simplified estimation based on tick rule or price changes.
        """
        # Calculate price changes to estimate buy/sell volume direction
        dp = df[price_col].diff()
        
        # Simple tick rule approximation
        buy_volume = np.where(dp > 0, df[volume_col], np.where(dp == 0, df[volume_col] * 0.5, 0))
        sell_volume = np.where(dp < 0, df[volume_col], np.where(dp == 0, df[volume_col] * 0.5, 0))
        
        df_vol = pd.DataFrame({'buy_vol': buy_volume, 'sell_vol': sell_volume}, index=df.index)
        
        # Boxcar/Rolling sum over the volume buckets
        rolling_buy = df_vol['buy_vol'].rolling(window=window).sum()
        rolling_sell = df_vol['sell_vol'].rolling(window=window).sum()
        rolling_total = df[volume_col].rolling(window=window).sum()
        
        # VPIN = |V_buy - V_sell| / V_total
        vpin = np.abs(rolling_buy - rolling_sell) / (rolling_total + 1e-8)
        return vpin
        
    def generate_all_features(self, df, price_col='close', volume_col='volume'):
        """
        Utility module to generate the base set of AFML features.
        """
        self.logger.info("Generating Fractional Differentiation (d=0.35)...")
        price_df = df[[price_col]]
        df['frac_diff_035'] = self.frac_diff_ffd(price_df, d=0.35)[price_col]
        
        self.logger.info("Generating Shannon Entropy...")
        df['entropy_50'] = self.shannon_entropy(df[price_col], window=50)
        
        if volume_col in df.columns:
            self.logger.info("Generating VPIN approximation...")
            df['vpin_50'] = self.calculate_vpin_approximation(df, volume_col=volume_col, price_col=price_col, window=50)
            
        return df

if __name__ == "__main__":
    # Test Feature Extractor
    logging.basicConfig(level=logging.INFO)
    np.random.seed(42)
    dates = pd.date_range(start='2025-01-01', periods=1000, freq='5T')
    prices = np.random.randn(1000).cumsum() + 100
    volumes = np.random.randint(10, 1000, size=1000)
    
    df = pd.DataFrame({'close': prices, 'volume': volumes}, index=dates)
    
    extractor = FeatureExtraction()
    df_features = extractor.generate_all_features(df)
    
    print(df_features.tail())
