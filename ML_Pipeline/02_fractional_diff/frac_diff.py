"""
Fractional Differentiation (FFD) — Phase 1, Step 2
===================================================
Kovoja prieš Klaida #2: Integer Differentiation

Marcos Lopez de Prado, AFML Ch. 5

KĄ DARO:
  Standartinis diff (d=1) sunaikina kainų atmintį.
  Fractional diff (d=0.1-0.5) padaro kainą stacionarią,
  bet IŠSAUGO dalį atminties, kurią ML modelis gali mokytis.

KAIP VEIKIA:
  1. Paima kainų eilutę (pvz., Dollar Bars close kainas)
  2. Bando skirtingus d koeficientus (0.0, 0.05, 0.1, ..., 1.0)
  3. Kiekvienam d tikrina ADF testą (ar stacionaru?)
  4. Randa MAŽIAUSIĄ d, kuris pasiekia stacionarumą (p < 0.05)
  5. Tai yra tavo optimalus d — naudok jį visur!

NAUDOJIMAS:
  py frac_diff.py --input ../../data/BTCUSDT_2020-01-01_2020-12-31_dollarBars_100000000.csv
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller
import argparse
import os
import warnings
warnings.filterwarnings('ignore')


# ============================================================
# 1. FFD svorių skaičiavimas
# ============================================================
def get_weights_ffd(d, threshold=1e-5):
    """
    Apskaičiuoja Fixed-Width-Window Fractional Differentiation svorius.

    Parametrai:
        d (float): Diferencijavimo laipsnis (0-1).
                    d=0 = originali kaina (nestacionari)
                    d=1 = pilnas diff (prarasta atmintis)
                    d=0.3 = optimalus balansas (dažniausiai)
        threshold: Mažiausias svoris, kurį dar naudojame.
                   Kuo mažesnis, tuo ilgesnis langas (lėčiau, bet tiksliau).

    Grąžina:
        np.array — svorių masyvas
    """
    weights = [1.0]
    k = 1
    while True:
        # Rekursyvi formulė: w_k = -w_{k-1} * (d - k + 1) / k
        w_next = -weights[-1] * (d - k + 1) / k
        if abs(w_next) < threshold:
            break
        weights.append(w_next)
        k += 1
    return np.array(weights[::-1])


# ============================================================
# 2. Fractional Differentiation taikymas
# ============================================================
def frac_diff_ffd(series, d, threshold=1e-5):
    """
    Taiko FFD (Fixed-Width-Window Fractional Differentiation) kainų eilutei.

    Parametrai:
        series (pd.Series): Kainų eilutė (pvz., df['close'])
        d (float): Diferencijavimo laipsnis
        threshold: Svorių nukirpimo riba

    Grąžina:
        pd.Series — frakcinė diferencijuota eilutė
    """
    weights = get_weights_ffd(d, threshold)
    width = len(weights) - 1  # Kiek eilučių prarandame pradžioje
    
    result = {}
    series_values = series.values
    
    for i in range(width, len(series_values)):
        # Svertinis vidurkis: dabartinė kaina * w0 + praeities kainos * w1, w2...
        window = series_values[i - width:i + 1]
        result[series.index[i]] = np.dot(weights, window)
    
    return pd.Series(result)


# ============================================================
# 3. ADF testas (Stacionarumo tikrinimas)
# ============================================================
def adf_test(series):
    """
    Augmented Dickey-Fuller testas.

    Grąžina p-value:
      p < 0.05 = stacionaru (GERAI — ML modelis gali mokytis)
      p > 0.05 = nestacionaru (BLOGAI — kaina turi vieneto šaknį)
    """
    result = adfuller(series.dropna(), maxlag=1, regression='c', autolag=None)
    return result[1]  # p-value


# ============================================================
# 4. AUTOMATINIS optimalaus d paieška
# ============================================================
def find_optimal_d(series, d_values=None, significance=0.05):
    """
    Automatiškai randa mažiausią d, kuris daro kainą stacionarią.

    Parametrai:
        series: Kainų eilutė
        d_values: Kokius d bandyti (default: 0.0, 0.05, 0.10, ..., 1.00)
        significance: p-value slenkstis (default: 0.05)

    Grąžina:
        dict su rezultatais kiekvienam d bandytam
    """
    if d_values is None:
        d_values = np.arange(0, 1.05, 0.05)
    
    results = []
    optimal_d = None
    
    print("\n" + "=" * 60)
    print("  FRACTIONAL DIFFERENTIATION — d PAIESKA")
    print("=" * 60)
    print(f"  {'d':>6} | {'ADF p-value':>12} | {'Stacionaru?':>12} | {'Atmintis':>10}")
    print("-" * 60)
    
    for d in d_values:
        try:
            if d == 0:
                diff_series = series
            else:
                diff_series = frac_diff_ffd(series, d)
            
            if len(diff_series.dropna()) < 20:
                continue
                
            p_val = adf_test(diff_series)
            is_stationary = p_val < significance
            
            # Koreliacijos su originalu skaičiavimas (atminties matas)
            common_idx = series.index.intersection(diff_series.index)
            if len(common_idx) > 10:
                memory = series.loc[common_idx].corr(diff_series.loc[common_idx])
            else:
                memory = float('nan')
            
            status = "TAIP" if is_stationary else "ne"
            marker = " <-- OPTIMALUS" if is_stationary and optimal_d is None else ""
            
            if is_stationary and optimal_d is None:
                optimal_d = d
            
            print(f"  {d:>6.2f} | {p_val:>12.6f} | {status:>12} | {memory:>10.4f}{marker}")
            
            results.append({
                'd': round(d, 2),
                'p_value': p_val,
                'is_stationary': is_stationary,
                'memory_correlation': memory
            })
        except Exception as e:
            print(f"  {d:>6.2f} | {'ERROR':>12} | {str(e)[:30]}")
    
    print("=" * 60)
    
    if optimal_d is not None:
        print(f"\n  REZULTATAS: Optimalus d = {optimal_d:.2f}")
        print(f"  Tai reiškia: kaina STACIONARI, bet išsaugo {results[int(optimal_d/0.05)]['memory_correlation']:.1%} atminties!")
    else:
        print(f"\n  PERSPEJIMAS: Nerastas stacionarus d. Bandyk didesnį diapazoną.")
    
    return results, optimal_d


# ============================================================
# 5. CLI — paleisti per terminalą
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fractional Differentiation (FFD) — AFML Ch.5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pavyzdys:
  py frac_diff.py --input ../../data/BTCUSDT_2020_dollarBars.csv
  py frac_diff.py --input ../../data/BTCUSDT_2020_dollarBars.csv --column close --save
        """
    )
    parser.add_argument("--input", type=str, required=True, 
                        help="Kelias iki Dollar Bars CSV failo")
    parser.add_argument("--column", type=str, default="close", 
                        help="Stulpelio pavadinimas (default: close)")
    parser.add_argument("--save", action="store_true", 
                        help="Issaugoti rezultata i CSV")
    parser.add_argument("--output", type=str, 
                        help="Isvesties failo kelias (default: auto)")
    
    args = parser.parse_args()
    
    # Nuskaitymas
    print(f"\nSkaitau: {args.input}")
    df = pd.read_csv(args.input)
    print(f"Eiluciu: {len(df)}")
    print(f"Stulpeliai: {list(df.columns)}")
    
    if args.column not in df.columns:
        print(f"KLAIDA: Stulpelis '{args.column}' nerastas!")
        print(f"Galimi: {list(df.columns)}")
        exit(1)
    
    series = df[args.column]
    
    # Optimalaus d paieška
    results, optimal_d = find_optimal_d(series)
    
    # Jei rastas d, taikome ir saugome
    if optimal_d is not None and args.save:
        diff_series = frac_diff_ffd(series, optimal_d)
        df_out = df.loc[diff_series.index].copy()
        df_out[f'{args.column}_frac_diff_{optimal_d:.2f}'] = diff_series
        
        out_path = args.output
        if not out_path:
            base, ext = os.path.splitext(args.input)
            out_path = f"{base}_fracdiff_d{optimal_d:.2f}{ext}"
        
        df_out.to_csv(out_path, index=False)
        print(f"\nIssaugota: {out_path}")
    
    print("\nBaigta!")
