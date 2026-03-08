import pandas as pd
import numpy as np
import os
import scipy.cluster.hierarchy as sch

def get_ivp(cov, **kargs):
    # Compute the inverse-variance portfolio
    ivp = 1. / np.diag(cov)
    ivp /= ivp.sum()
    return ivp

def get_cluster_var(cov, c_items):
    # Compute variance per cluster
    cov_c = cov.loc[c_items, c_items] # matrix slice
    w_ = get_ivp(cov_c)
    c_var = np.dot(np.dot(w_, cov_c), w_)
    return c_var

def get_quasi_diag(link):
    # Sort clusters by distance
    link = link.astype(int)
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
    num_items = link[-1, 3] # total items in linkage
    while sort_ix.max() >= num_items:
        sort_ix.index = range(0, sort_ix.shape[0] * 2, 2) # double index
        df0 = sort_ix[sort_ix >= num_items] # find clusters
        i = df0.index
        j = df0.values - num_items
        sort_ix[i] = link[j, 0] # item 1
        df0 = pd.Series(link[j, 1], index=i + 1)
        sort_ix = pd.concat([sort_ix, df0])
        sort_ix = sort_ix.sort_index()
        sort_ix.index = range(sort_ix.shape[0])
    return sort_ix.tolist()

def get_hrp_weights(cov, sort_ix):
    # Compute HRP weights
    w = pd.Series(1, index=sort_ix)
    c_items = [sort_ix] # initialize clusters
    while len(c_items) > 0:
        c_items = [i[j:k] for i in c_items for j, k in ((0, len(i) // 2), (len(i) // 2, len(i))) if len(i) > 1] # bi-section
        for i in range(0, len(c_items), 2): # parse in pairs
            c_items0 = c_items[i] # cluster 1
            c_items1 = c_items[i + 1] # cluster 2
            c_var0 = get_cluster_var(cov, c_items0)
            c_var1 = get_cluster_var(cov, c_items1)
            alpha = 1 - c_var0 / (c_var0 + c_var1)
            w[c_items0] *= alpha # weight 1
            w[c_items1] *= 1 - alpha # weight 2
    return w

def main():
    # Load primary signals to see correlations
    signals_path = "../../data/signals/primary_signals.csv"
    if not os.path.exists(signals_path):
        print("Signals file not found")
        return
        
    df = pd.read_csv(signals_path)
    # Strategy columns
    cols = ['signal_max', 'signal_ma', 'signal_bb']
    
    # Calculate returns or signal correlation
    # For HRP we usually use volatility/covariance of returns.
    # Since we don't have separate return streams yet, we use signal correlation as a proxy.
    corr = df[cols].corr()
    cov = df[cols].cov()
    
    print("Strategy Correlation Matrix:")
    print(corr)
    
    # HRP Clustering
    dist = np.sqrt((1 - corr) / 2.)
    link = sch.linkage(dist, 'single')
    sort_ix = get_quasi_diag(link)
    sort_ix = corr.index[sort_ix].tolist() # row/column names
    
    weights = get_hrp_weights(cov, sort_ix)
    print("\n--- HRP Portfolio Weights ---")
    print(weights)

if __name__ == "__main__":
    main()
