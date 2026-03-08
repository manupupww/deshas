import pandas as pd
import numpy as np
import logging

class TripleBarrierLabeler:
    """
    Triple-Barrier Method for Labeling
    
    As described in AFML (Marcos Lopez de Prado).
    Labels observations based on whether the first touched barrier is:
    - Upper Barrier (Take Profit)
    - Lower Barrier (Stop Loss)
    - Vertical Barrier (Time elapsed = Timeout)
    """
    def __init__(self, pt_sl_ratios=[1.0, 1.0], timeout_bars=10, min_ret=0.001):
        """
        pt_sl_ratios: [Take Profit ratio, Stop Loss ratio] multiplier applied to volatility target
        timeout_bars: Vertical barrier max holding period
        min_ret: Minimum volatility to process an event
        """
        self.pt_sl_ratios = pt_sl_ratios
        self.timeout_bars = timeout_bars
        self.min_ret = min_ret
        self.logger = logging.getLogger(__name__)

    def get_volatility(self, df: pd.DataFrame, price_col='close', span=100):
        """ Calculate daily/rolling volatility (e.g., exponentially weighted moving std of returns) """
        returns = df[price_col].pct_change()
        volatility = returns.ewm(span=span).std()
        return volatility
        
    def get_events(self, df: pd.DataFrame, signals: pd.Series, target: pd.Series):
        """
        Filters out signals where target volatility is less than min_ret, 
        and extracts the timestamp index for active signal events.
        """
        target = target.loc[target > self.min_ret]
        
        # Keep only events where primary_signal is non-zero
        events = pd.DataFrame(index=signals[signals != 0].index)
        events = events.join(target, how='inner').rename(columns={target.name: 'trgt'})
        events['primary_signal'] = signals.loc[events.index]
        return events

    def apply_barriers(self, df: pd.DataFrame, events: pd.DataFrame, pt_sl: list, price_col='close'):
        """
        events: DataFrame with index as event timestamps and columns:
                - 'primary_signal': 1 or -1
                - 'trgt': target volatility for the event
        """
        out = events[['primary_signal']].copy()
        
        touches = pd.DataFrame(index=events.index, columns=['pt_touch', 'sl_touch', 'timeout'])
        
        for idx in events.index:
            try:
                # Find integer index of the event
                start_i = df.index.get_loc(idx)
                end_i = min(start_i + self.timeout_bars, len(df)-1)
                
                path = df[price_col].iloc[start_i:end_i+1]
                if len(path) == 0:
                    continue
                    
                start_price = path.iloc[0]
                target = events.loc[idx, 'trgt']
                signal = events.loc[idx, 'primary_signal']
                
                # Dynamic Barriers based on target volatility
                if signal == 1:
                    upper_bound = start_price * (1 + target * pt_sl[0])
                    lower_bound = start_price * (1 - target * pt_sl[1])
                    
                    # Touch times
                    pt_touch = path[path >= upper_bound].index.min()
                    sl_touch = path[path <= lower_bound].index.min()
                    
                elif signal == -1:
                    upper_bound = start_price * (1 + target * pt_sl[1]) # Stop loss is above for short
                    lower_bound = start_price * (1 - target * pt_sl[0]) # Take profit is below for short
                    
                    # Touch times
                    pt_touch = path[path <= lower_bound].index.min()
                    sl_touch = path[path >= upper_bound].index.min()
                else:
                    continue
                
                touches.loc[idx, 'pt_touch'] = pt_touch
                touches.loc[idx, 'sl_touch'] = sl_touch
                touches.loc[idx, 'timeout'] = path.index[-1]
                
            except Exception as e:
                self.logger.error(f"Error processing barrier at {idx}: {e}")
                
        # Calculate Final Label
        labels = pd.Series(0, index=events.index)
        
        for idx in events.index:
            pt = touches.loc[idx, 'pt_touch']
            sl = touches.loc[idx, 'sl_touch']
            timeout = touches.loc[idx, 'timeout']
            
            times = []
            if pd.notna(pt): times.append((pt, 1))
            if pd.notna(sl): times.append((sl, -1))
            
            if len(times) > 0:
                first_touch = min(times, key=lambda x: x[0])
                if first_touch[0] <= timeout:
                    labels[idx] = first_touch[1]
                else:
                    labels[idx] = 0
            else:
                labels[idx] = 0
                
        out['label'] = labels
        # Meta-label: 1 if successful (PT hit first, meaning label == 1 regardless of direction), 0 if not
        out['meta_label'] = np.where(out['label'] == 1, 1, 0)
        
        return out

if __name__ == "__main__":
    # Test Triple Barrier Labeler
    np.random.seed(42)
    dates = pd.date_range(start='2025-01-01', periods=1000, freq='5T')
    prices = np.random.randn(1000).cumsum() + 100
    df = pd.DataFrame({'close': prices}, index=dates)
    
    # Generate some dummy signals
    signals = pd.Series(0, index=dates)
    signals.iloc[50] = 1   # Long
    signals.iloc[150] = -1 # Short
    signals.iloc[250] = 1  # Long
    
    # Calculate volatility
    labeler = TripleBarrierLabeler(pt_sl_ratios=[1.0, 1.0], timeout_bars=20, min_ret=0.0001)
    volatility = labeler.get_volatility(df, span=50)
    
    # Get filtered events
    events = labeler.get_events(df, signals, target=volatility)
    
    # Apply barriers
    labels_df = labeler.apply_barriers(df, events, pt_sl=[1.0, 1.0])
    print(labels_df)
