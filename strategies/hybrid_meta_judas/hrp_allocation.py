import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform
import logging

class HRPPortfolioAllocator:
    """
    Hierarchical Risk Parity (HRP)
    Divides portfolio weights based on cluster distance/correlation, completely independent 
    of the daily signal direction to ensure portfolio robustness against shocks.
    Replaces static Markowitz allocations.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_distance_matrix(self, corr_matrix):
        """ Convert correlation matrix to distance matrix (AFML 16.3) """
        dist = np.sqrt(np.clip(0.5 * (1 - corr_matrix), 0, 1))
        return dist
        
    def get_quasi_diag(self, link):
        """ Sort clustered items by distance """
        link = link.astype(int)
        sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
        num_items = link[-1, 3]
        while sort_ix.max() >= num_items:
            sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
            df0 = sort_ix[sort_ix >= num_items]
            i = df0.index
            j = df0.values - num_items
            sort_ix[i] = link[j, 0]
            df0 = pd.Series(link[j, 1], index=i + 1)
            sort_ix = pd.concat([sort_ix, df0]).sort_index()
        return sort_ix.tolist()
        
    def get_cluster_var(self, cov_matrix, cluster_items):
        """ Compute inverse variance weighting per cluster """
        cov_slice = cov_matrix.loc[cluster_items, cluster_items]
        ivp = 1.0 / np.diag(cov_slice)
        ivp /= ivp.sum()
        w = ivp.reshape(-1, 1)
        cluster_var = np.dot(np.dot(w.T, cov_slice), w)[0, 0]
        return cluster_var
        
    def get_rec_bipart(self, cov_matrix, sort_ix):
        """ Compute HRP allocation recursively """
        weights = pd.Series(1.0, index=sort_ix)
        clusters = [sort_ix]
        while len(clusters) > 0:
            clusters_tup = [i[j:k] for i in clusters for j, k in ((0, len(i) // 2), (len(i) // 2, len(i))) if len(i) > 1]
            clusters = clusters_tup
            for i in range(0, len(clusters), 2):
                cluster_left = clusters[i]
                cluster_right = clusters[i + 1]
                var_left = self.get_cluster_var(cov_matrix, cluster_left)
                var_right = self.get_cluster_var(cov_matrix, cluster_right)
                alpha = 1 - var_left / (var_left + var_right)
                weights[cluster_left] *= alpha
                weights[cluster_right] *= (1 - alpha)
        return weights

    def allocate(self, returns_df: pd.DataFrame) -> pd.Series:
        """
        Calculate HRP weights from historical returns.
        returns_df: DataFrame where columns are coin symbols and rows are historical time periods
        """
        self.logger.info("Extracting HRP Base Allocations...")
        corr = returns_df.corr()
        cov = returns_df.cov()
        dist = self.get_distance_matrix(corr)
        
        np.fill_diagonal(dist.values, 0)
        
        p_dist = squareform(dist)
        link = linkage(p_dist, 'single')
        sort_ix = self.get_quasi_diag(link)
        sort_ix = corr.index[sort_ix].tolist()
        
        # Reorder covariance matrix
        cov = cov.loc[sort_ix, sort_ix]
        
        hrp_weights = self.get_rec_bipart(cov, sort_ix)
        self.logger.info("HRP Allocation complete.")
        return hrp_weights

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test HRP Allocator
    np.random.seed(42)
    asset_returns = pd.DataFrame(np.random.randn(1000, 5), columns=['BTC', 'ETH', 'SOL', 'AVAX', 'LINK'])
    
    allocator = HRPPortfolioAllocator()
    weights = allocator.allocate(asset_returns)
    print("Base Portfolio Weights based on Hierarchical Risk Parity:")
    print(weights)
