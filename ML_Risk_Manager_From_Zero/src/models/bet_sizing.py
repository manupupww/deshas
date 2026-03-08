import pandas as pd
import numpy as np
from scipy.stats import norm

def bet_size_probability(prob, num_classes=2):
    """
    SNIPPET 10.1: FROM PROBABILITIES TO BET SIZE
    Calculates bet size based on predicted success probability.
    """
    # Inverse of the CDF of a standard normal distribution
    # z = (p - 1/n) / sqrt(p*(1-p))
    z = (prob - 1/num_classes) / (prob * (1 - prob))**0.5
    size = 2 * norm.cdf(z) - 1
    return size

def apply_bet_sizing(input_path, output_path):
    print(f"Applying bet sizing to {input_path}...")
    df = pd.read_csv(input_path)
    
    # Apply probabilistic bet sizing
    df['bet_size'] = df['meta_prob'].apply(lambda x: bet_size_probability(x))
    
    # Thresholding: only take bets where the meta-model is more confident than 50%
    df['filtered_signal'] = 0
    df.loc[df['meta_prob'] > 0.5, 'filtered_signal'] = 1
    
    # Actual trade size (probabilistic weight * max position)
    max_position = 1.0 # 100% of allocated capital
    df['trade_weight'] = df['bet_size'] * max_position
    
    df.to_csv(output_path, index=False)
    print(f"✅ Bet sizing complete. Results saved to {output_path}")
    
    print("\nBet Size Stats:")
    print(df['bet_size'].describe())
    return df

if __name__ == "__main__":
    apply_bet_sizing("data/processed/meta_results.csv", "data/processed/final_bets.csv")
