import pandas as pd
import numpy as np

class ICTJudasEngine:
    """
    ICT Judas Swing Strategy Engine (Flux Charts)
    
    Logic:
    1. Identify 'Judas Swing' liquidity points (Highest High / Lowest Low) before NY session starts.
    2. During NY session (09:30 - 09:45 AM), look for price to break these liquidity points.
    3. If price breaks ABOVE the high, it's a 'Bearish Judas' -> look for a Bearish FVG to Short.
    4. If price breaks BELOW the low, it's a 'Bullish Judas' -> look for a Bullish FVG to Long.
    """
    def __init__(self, df, swing_length=30):
        self.df = df
        self.swing_length = swing_length

    def get_signals(self, utc_offset=4):
        df = self.df.copy()
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        df['atr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
        
        df['highest_high'] = df['high'].rolling(30).max().shift(1)
        df['lowest_low'] = df['low'].rolling(30).min().shift(1)
        
        ny_start_h, ny_start_m = 9, 30
        ny_end_h, ny_end_m = 9, 45
        
        logic_time = df.index - pd.Timedelta(hours=utc_offset)
        
        # Ensure pd.Series for logical operations
        in_session = pd.Series((logic_time.hour == ny_start_h) & 
                               (logic_time.minute >= ny_start_m) & 
                               (logic_time.minute <= ny_end_m), index=df.index)
        session_start = in_session & (~in_session.shift(1).fillna(False))
        
        buy_signal = np.zeros(len(df))
        sell_signal = np.zeros(len(df))
        
        bullish_fvg = (df['low'] > df['high'].shift(2))
        bearish_fvg = (df['high'] < df['low'].shift(2))
        
        print(f"    [DEBUG] Starting signal calculation. Logic Time Offset: {utc_offset}h")
        state = 'WAIT'
        hh_liq = 0
        ll_liq = 0
        session_count = 0
        trigger_count = 0
        
        for i in range(1, len(df)):
            if session_start.iloc[i]:
                state = 'HUNTING'
                session_count += 1
                hh_liq = df['highest_high'].iloc[i]
                ll_liq = df['lowest_low'].iloc[i]
                
            if state == 'HUNTING' and in_session.iloc[i]:
                if df['close'].iloc[i] > hh_liq:
                    state = 'LOOK_FOR_SHORT'
                    trigger_count += 1
                elif df['close'].iloc[i] < ll_liq:
                    state = 'LOOK_FOR_LONG'
                    trigger_count += 1
                    
            if state == 'LOOK_FOR_SHORT':
                if df['close'].iloc[i] < df['open'].iloc[i] or bearish_fvg.iloc[i]:
                    sell_signal[i] = 1
                    state = 'WAIT'
            elif state == 'LOOK_FOR_LONG':
                if df['close'].iloc[i] > df['open'].iloc[i] or bullish_fvg.iloc[i]:
                    buy_signal[i] = 1
                    state = 'WAIT'
                    
            if not in_session.iloc[i] and state != 'WAIT':
                state = 'WAIT'
                
        print(f"    [DEBUG] Sessions found: {session_count}, Manipulations found: {trigger_count}")
        return buy_signal, sell_signal, df['atr']
