import pandas as pd
import numpy as np

def get_daily_vol(close, span0=100):
    """
    SNIPPET 3.1: DAILY VOLATILITY ESTIMATES
    Computes volatility using exponentially weighted moving standard deviation of daily returns.
    """
    # Daily returns (log-returns would be more stable for high frequencies)
    df0 = close.index.searchsorted(close.index - pd.Timedelta(days=1))
    df0 = df0[df0 > 0]
    df0 = pd.Series(close.index[df0 - 1], index=close.index[close.shape[0] - df0.shape[0]:])
    df0 = close.loc[df0.index] / close.loc[df0.values].values - 1 # daily returns
    df0 = df0.ewm(span=span0).std()
    return df0

def apply_pt_sl_on_t1(close, events, pt_sl, molecule):
    """
    SNIPPET 3.2: TRIPLE-BARRIER LABELING METHOD
    molecule: subset of event indices to process (for potential parallelization)
    """
    events_ = events.loc[molecule]
    out = events_[['t1']].copy(deep=True)
    if pt_sl[0] > 0:
        pt = pt_sl[0] * events_['trgt']
    else:
        pt = pd.Series(index=events.index) # NaNs
    
    if pt_sl[1] > 0:
        sl = -pt_sl[1] * events_['trgt']
    else:
        sl = pd.Series(index=events.index) # NaNs
        
    for loc, t1 in events_['t1'].fillna(close.index[-1]).items():
        df0 = close[loc:t1] # path prices
        df0 = (df0 / close[loc] - 1) * events_.at[loc, 'side'] # path returns
        out.loc[loc, 'sl'] = df0[df0 < sl[loc]].index.min() # earliest stop loss
        out.loc[loc, 'pt'] = df0[df0 > pt[loc]].index.min() # earliest profit taking
    return out

def get_events(close, t_events, pt_sl, trgt, min_ret, num_threads, t1=False, side=None):
    """
    SNIPPET 3.6: EXPANDING getEvents TO INCORPORATE META-LABELING
    """
    # 1) Get target
    trgt = trgt.loc[t_events]
    trgt = trgt[trgt > min_ret] # minRet
    # 2) Get t1 (max holding period)
    if t1 is False:
        t1 = pd.Series(pd.NaT, index=t_events)
    # 3) Form events object, apply stop loss on t1
    if side is None:
        side_ = pd.Series(1., index=trgt.index)
        pt_sl_ = [pt_sl[0], pt_sl[0]]
    else:
        side_ = side.loc[trgt.index]
        pt_sl_ = pt_sl[:2]
        
    events = pd.concat({'t1': t1, 'trgt': trgt, 'side': side_}, axis=1).dropna(subset=['trgt'])
    
    # Multiplexing placeholder (using single thread for 'from zero' simplicity)
    df0 = apply_pt_sl_on_t1(close, events, pt_sl_, events.index)
    
    events['t1'] = df0.dropna(how='all').min(axis=1) # pd.min ignores nan
    if side is None:
        events = events.drop('side', axis=1)
    return events

def get_bins(events, close):
    """
    SNIPPET 3.7: EXPANDING getBins TO INCORPORATE META-LABELING
    """
    # 1) Prices aligned with events
    events_ = events.dropna(subset=['t1'])
    px = events_.index.union(events_['t1'].values).drop_duplicates()
    px = close.reindex(px, method='bfill')
    # 2) Create out object
    out = pd.DataFrame(index=events_.index)
    out['ret'] = px.loc[events_['t1'].values].values / px.loc[events_.index].values - 1
    if 'side' in events_:
        out['ret'] *= events_['side'] # meta-labeling
    out['bin'] = np.sign(out['ret'])
    if 'side' in events_:
        out.loc[out['ret'] <= 0, 'bin'] = 0 # meta-labeling
    return out

if __name__ == "__main__":
    # Test execution should happen in Phase 4 when models are ready, 
    # but we can verify against dummy data if needed.
    print("Labeling logic refined from AFML Chapter 3.")
