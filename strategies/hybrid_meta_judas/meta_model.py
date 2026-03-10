import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import logging

class MetaModelEngine:
    """
    ML Meta-Model Training Engine & Evaluator
    Trains a secondary model to predict the probability of success of the Primary Model.
    Outputs are used for continuous Bet Sizing (position sizing) instead of raw 1/-1 signals.
    """
    def __init__(self, n_estimators=100, max_depth=4, n_jobs=-1, random_state=42):
        # We use a robust, bounded complexity Random Forest for the meta-layer 
        # (XGBoost is also an option, but RF is less prone to overfitting without extensive tuning)
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            n_jobs=n_jobs,
            random_state=random_state,
            class_weight='balanced'
        )
        self.logger = logging.getLogger(__name__)
        
    def _purged_embargoed_cv(self, X: pd.DataFrame, y: pd.Series, cv=3, embargo_pct=0.01):
        """
        Generates Purged and Embargoed CV splits to eliminate Data Leakage in time-series (AFML).
        """
        self.logger.info(f"Generating Purged & Embargoed CV splits (cv={cv})...")
        splits = []
        step = len(X) // cv
        for i in range(cv):
            test_start = i * step
            test_end = (i + 1) * step if i != cv - 1 else len(X)
            
            embargo_size = int(len(X) * embargo_pct)
            
            test_idx = np.arange(test_start, test_end)
            train_idx = np.concatenate((
                np.arange(0, max(0, test_start - embargo_size)),
                np.arange(min(len(X), test_end + embargo_size), len(X))
            ))
            splits.append((train_idx, test_idx))
            
        return splits
        
    def train(self, X: pd.DataFrame, y: pd.Series):
        """
        Train the Meta-Model.
        X: AFML features (Fractional Diff, Entropy, VPIN, etc.)
        y: Meta-labels (1 if successful primary signal hitting Take Profit, 0 otherwise)
        """
        self.logger.info("Training Meta-Model...")
        
        # Final training step (Cross Validation metrics should be evaluated externally)
        self.model.fit(X, y)
        self.logger.info("Meta-Model trained successfully.")
        
    def predict_probability(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict probability of primary model success -> P(Meta-Label = 1)
        """
        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)[:, 1]
        return np.zeros(len(X))
        
    def calculate_bet_size(self, probabilities, method='step'):
        """
        Calculate bet sizing based on the probability of success.
        This operates purely as a Risk Manager.
        """
        sizes = np.zeros_like(probabilities)
        
        if method == 'step':
            # Discrete steps for execution
            sizes[probabilities > 0.5] = 0.5
            sizes[probabilities > 0.65] = 1.0
        elif method == 'continuous':
            # Continuous allocation bounds from 0 to 1
            sizes = np.clip((probabilities - 0.5) * 2, 0, 1)
            
        return sizes

    def evaluate_deflated_sharpe_ratio(self, returns, k_trials=100):
        """
        Calculates expected Deflated Sharpe Ratio (DSR)
        Estimates the True Sharpe adjusting for Overfitting (number of K paths tested).
        """
        self.logger.info("Evaluating Deflated Sharpe Ratio (DSR)...")
        # Standard Annualized Sharpe Ratio 
        # Assumption: 252 trading days * N periods per day. Simplified below for daily assumption
        sr_observed = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
        
        # Expected Maximum Sharpe Ratio (EMSR) logic (Bailey and Lopez de Prado)
        euler_mascheroni = 0.5772156649
        emsr = np.sqrt(2 * np.log(k_trials)) + (euler_mascheroni / np.sqrt(2 * np.log(k_trials)))
        
        self.logger.info(f"Observed Sharpe Ratio: {sr_observed:.2f}")
        self.logger.info(f"Expected Max SR (EMSR) for {k_trials} trials: {emsr:.2f}")
        
        passed = sr_observed > emsr
        return passed, sr_observed, emsr

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test Meta Model
    X = pd.DataFrame(np.random.randn(100, 5), columns=['f1', 'f2', 'f3', 'f4', 'f5'])
    y = pd.Series(np.random.randint(0, 2, 100))
    
    model = MetaModelEngine()
    model.train(X, y)
    
    probs = model.predict_probability(X)
    sizes = model.calculate_bet_size(probs, method='continuous')
    
    print(f"Sample Probabilities: {probs[:5]}")
    print(f"Sample Bet Sizes: {sizes[:5]}")

    # Test DSR
    mock_returns = np.random.normal(0.001, 0.02, 1000)
    model.evaluate_deflated_sharpe_ratio(mock_returns, k_trials=100)
