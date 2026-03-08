import pandas as pd
import numpy as np

class QQEEngine:
    def __init__(self, data: pd.DataFrame, rsi_period=14, smooth_period=5, factor=4.236):
        self.df = data.copy()
        self.rsi_period = rsi_period
        self.smooth_period = smooth_period
        self.factor = factor

    def calculate_qqe(self):
        """
        Calculates Quantitative Qualitative Estimation (QQE) signals.
        """
        df = self.df
        
        # 1. RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 2. RSI Smoothing (EMA)
        df['rsi_ma'] = df['rsi'].ewm(span=self.smooth_period, adjust=False).mean()
        
        # 3. ATR of RSI
        df['rsi_atr'] = abs(df['rsi_ma'] - df['rsi_ma'].shift(1))
        df['wilder_atr'] = df['rsi_atr'].ewm(span=2 * self.rsi_period - 1, adjust=False).mean()
        df['qqe_atr'] = df['wilder_atr'].ewm(span=2 * self.rsi_period - 1, adjust=False).mean() * self.factor
        
        # 4. Trailing Stop (QQES)
        qqes = np.zeros(len(df))
        rsi_ma = df['rsi_ma'].values
        qqe_atr = df['qqe_atr'].values
        
        for i in range(1, len(df)):
            prev_qqes = qqes[i-1]
            curr_rsi = rsi_ma[i]
            prev_rsi = rsi_ma[i-1]
            atr = qqe_atr[i]
            
            if curr_rsi < prev_qqes:
                new_qqes = curr_rsi + atr
                if prev_rsi < prev_qqes and new_qqes > prev_qqes:
                    qqes[i] = prev_qqes
                else:
                    qqes[i] = new_qqes
            elif curr_rsi > prev_qqes:
                new_qqes = curr_rsi - atr
                if prev_rsi > prev_qqes and new_qqes < prev_qqes:
                    qqes[i] = prev_qqes
                else:
                    qqes[i] = new_qqes
            else:
                qqes[i] = prev_qqes
                
        df['qqes'] = qqes
        
        # 5. Signal Generation
        df['qqe_long'] = (df['rsi_ma'] > df['qqes']).astype(int)
        df['qqe_short'] = (df['rsi_ma'] < df['qqes']).astype(int)
        
        # Signal crossover
        df['buy_sig'] = ((df['qqe_long'] == 1) & (df['qqe_long'].shift(1) == 0)).astype(int)
        df['sell_sig'] = ((df['qqe_short'] == 1) & (df['qqe_short'].shift(1) == 0)).astype(int)
        
        return df[['rsi_ma', 'qqes', 'buy_sig', 'sell_sig']]
