import pandas as pd
import numpy as np
from sklearn.model_selection import KFold
import os
import argparse

class PurgedKFold:
    """
    Purged K-Fold Cross Validation for Financial Machine Learning.
    Sukurtas pagal Marcos Lopez de Prado principus.
    Apsaugo nuo "Data Leakage" per laiko atmintį (serial correlation).
    """
    def __init__(self, n_splits=5, embargo_pct=0.01):
        self.n_splits = n_splits
        self.embargo_pct = embargo_pct
        
    def split(self, timestamps, end_timestamps):
        """
        timestamps: Series of trade start times (Unix ms)
        end_timestamps: Series of trade end times (Unix ms)
        Returns: Generator of (purged_train_indices, test_indices)
        """
        n = len(timestamps)
        indices = np.arange(n)
        embargo_step = int(n * self.embargo_pct)
        
        # Naudojame standartinį KFold pradiniams testų intervalams gauti
        kf = KFold(n_splits=self.n_splits, shuffle=False)
        
        ts_array = timestamps.values if hasattr(timestamps, 'values') else timestamps
        end_array = end_timestamps.values if hasattr(end_timestamps, 'values') else end_timestamps
        
        for fold, (train_raw, test_idx) in enumerate(kf.split(indices)):
            test_start_t = ts_array[test_idx[0]]
            test_end_t = end_array[test_idx[-1]] # Test period baigiasi, kai baigiasi paskutinis test trade
            
            # Pradiniai treniravimo taškai
            train_idx = np.array(train_raw)
            
            # 1. PURGE: Ištriname treniravimo taškus, kurie laike persidengia su test periodu
            # Kirtimasis vyksta, jei train pradžia <= test pabaiga IR train pabaiga >= test pradžia
            train_starts = ts_array[train_idx]
            train_ends = end_array[train_idx]
            
            overlap_mask = (train_starts <= test_end_t) & (train_ends >= test_start_t)
            
            # 2. EMBARGO: Ištriname taškus iškart po test periodo.
            # Tai leidžia rinkai "atsistatyti" nenaudojant informacijos, kurią įtakojo test events.
            embargo_end_idx = min(n - 1, test_idx[-1] + embargo_step)
            embargo_end_t = ts_array[embargo_end_idx]
            
            # Embargo langas yra nuo test_end_t (testavimo pabaigos) iki embargo_end_t
            embargo_mask = (train_starts > test_end_t) & (train_starts <= embargo_end_t)
            
            # Apjungiame Purge ir Embargo kaukes
            drop_mask = overlap_mask | embargo_mask
            
            # Išvalyti treniravimo indeksai
            purged_train_idx = train_idx[~drop_mask]
            
            yield purged_train_idx, test_idx

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=r"C:\Users\Mr. Perfect\tradingbot\data\labels\BTCUSDT_sample_weights.csv")
    parser.add_argument("--splits", type=int, default=5, help="Number of K-Fold splits")
    parser.add_argument("--embargo", type=float, default=0.01, help="Embargo lango dydis (procentais nuo visų pavyzdžių)")
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"KLAIDA: Failas {args.input} nerastas.")
        return
        
    print(f"Kraunami duomenys Purged CV testui: {args.input}")
    df = pd.read_csv(args.input)
    
    cv = PurgedKFold(n_splits=args.splits, embargo_pct=args.embargo)
    
    print("\nPurged K-Fold CV Statistika:")
    print("-" * 50)
    
    total_samples = len(df)
    for fold, (train_idx, test_idx) in enumerate(cv.split(df['timestamp'], df['end_timestamp'])):
        n_train = len(train_idx)
        n_test = len(test_idx)
        n_dropped = total_samples - n_train - n_test
        
        print(f"Fold {fold+1}:")
        print(f"  Test Set Dydis:   {n_test} ({n_test/total_samples*100:.1f}%)")
        print(f"  Train Set Dydis:  {n_train} ({n_train/total_samples*100:.1f}%)")
        print(f"  Išmesta (Dropped): {n_dropped} pavyzdžiai (Purge + Embargo)")
        print("-" * 50)
        
    print("\n✅ Purged CV logika veikia. Šią klasę galėsime naudoti treniruojant ML modelius (Phase 6).")

if __name__ == "__main__":
    main()
