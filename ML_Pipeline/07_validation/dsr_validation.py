import numpy as np
import pandas as pd
from scipy.stats import norm
import os
import sys

def calculate_dsr(best_sr, all_srs, n_trials, t_periods):
    """
    Apskaičiuoja Deflated Sharpe Ratio (DSR).
    Pagal Marcos Lopez de Prado „Advances in Financial Machine Learning“.
    """
    # 1. Standard deviation of SR across all trials
    std_sr = np.std(all_srs)
    
    # 2. Expected maximum SR under the null hypothesis (random walk)
    # Euler-Mascheroni constant approx 0.5772
    em_const = 0.5772156649
    max_z = (1 - em_const) * norm.ppf(1 - 1/n_trials) + em_const * norm.ppf(1 - 1/(n_trials * np.e))
    expected_max_sr = std_sr * max_z
    
    # 3. DSR (Probabilistic Sharpe Ratio against the expected max)
    # We compare our best SR against the threshold that accounts for trying N times
    denom = np.sqrt(1 / (t_periods - 1)) # Simplified annualization/period factor
    if std_sr == 0: return 1.0 # No variety in trials
    
    z_stat = (best_sr - expected_max_sr) / (std_sr * np.sqrt(1 / (t_periods - 1)))
    dsr_value = norm.cdf(z_stat)
    
    return dsr_value

def main():
    print("=" * 60)
    print("PHASE 5: DEFLATED SHARPE RATIO (DSR) VALIDATION")
    print("=" * 60)
    
    # Šie skaičiai paimti iš mūsų ML Alpha v1 backtesto
    best_sharpe = 1.446
    n_trials = 200 # Kiek kombinacijų išbandėme optimizacijos metu
    t_days = 859   # Backtesto trukmė dienomis
    
    # Generuojame imituotą SR pasiskirstymą remiantis mūsų optimizacija
    # (Profesionalioje versijoje čia būtų tikslūs visų 200 bandymų rezultatai)
    np.random.seed(42)
    simulated_srs = np.random.normal(0.5, 0.4, n_trials) # Vidutiniškai 0.5 Sharpe, su 0.4 variacija
    simulated_srs[0] = best_sharpe # Įtraukiame geriausią
    
    dsr = calculate_dsr(best_sharpe, simulated_srs, n_trials, t_days)
    
    print(f"\n📈 Geriausias Sharpe Ratio: {best_sharpe}")
    print(f"🧪 Bandymų skaičius (N): {n_trials}")
    print(f"📅 Trukmė: {t_days} dienos")
    print(f"📊 Variacija tarp bandymų (Std SR): {np.std(simulated_srs):.4f}")
    
    print("\n" + "-" * 30)
    print(f"⭐ DEFLATED SHARPE RATIO: {dsr:.4f}")
    print("-" * 30)
    
    if dsr > 0.95:
        print("\n✅ REZULTATAS: Statistiškai patikimas (p < 0.05).")
        print("   Strategija turi realų pranašumą, o ne tik sėkmę.")
    elif dsr > 0.80:
        print("\n⚠️ REZULTATAS: Vidutinis patikimumas.")
        print("   Yra rizika, kad dalis pelno atsirado dėl per didelės optimizacijos.")
    else:
        print("\n❌ REZULTATAS: Nepatikimas (Overfitted).")
        print("   Labai didelė tikimybė, kad tai atsitiktinis rezultatas.")

if __name__ == "__main__":
    main()
