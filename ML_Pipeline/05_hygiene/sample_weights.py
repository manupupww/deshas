import pandas as pd
import numpy as np
import os
import argparse

def compute_num_co_events(timestamps, end_timestamps):
    """
    Skaičiuoja numCoEvents (kiek barų persidengia konkrečiu laiko momentu).
    Naudoja efektyvų laiko juostų metodą.
    """
    n = len(timestamps)
    co_events = np.zeros(n)
    
    print(f"Skaičiuojama numCoEvents {n} eilučių...</")
    
    ts_array = timestamps.values
    end_array = end_timestamps.values
    
    for i in range(n):
        if i % 10000 == 0 and i > 0:
            print(f"Progresas (CoEvents): {i}/{n}")
            
        t0 = ts_array[i]
        t1 = end_array[i]
        
        # Surandame indeksus tarp t0 ir t1
        j = i
        while j < n and ts_array[j] <= t1:
            co_events[j] += 1
            j += 1
            
    return co_events

def compute_sample_weights(timestamps, end_timestamps, co_events):
    """
    Skaičiuoja vidutinį pavyzdžio unikalumą (sample uniqueness) jo gyvavimo laikotarpiu.
    """
    n = len(timestamps)
    weights = np.zeros(n)
    
    ts_array = timestamps.values
    end_array = end_timestamps.values
    
    print("Skaičiuojami Sample Weights...")
    for i in range(n):
        if i % 10000 == 0 and i > 0:
            print(f"Progresas (Weights): {i}/{n}")
            
        t1 = end_array[i]
        
        j = i
        event_uniqueness = []
        while j < n and ts_array[j] <= t1:
            event_uniqueness.append(1.0 / co_events[j])
            j += 1
            
        if event_uniqueness:
            weights[i] = np.mean(event_uniqueness)
            
    return weights

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=r"C:\Users\Mr. Perfect\tradingbot\data\labels\BTCUSDT_labels.csv", help="Path to labels CSV")
    parser.add_argument("--output", type=str, default=r"C:\Users\Mr. Perfect\tradingbot\data\labels\BTCUSDT_sample_weights.csv", help="Output path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"KLAIDA: Failas {args.input} nerastas.")
        return

    print(f"Kraunami label duomenys: {args.input}")
    df = pd.read_csv(args.input)
    
    if 'end_timestamp' not in df.columns:
        print("KLAIDA: 'end_timestamp' stulpelis nerastas. Reikia pergeneruoti labels su atnaujintu labeling.py")
        return
        
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # 1. numCoEvents (persidengimai)
    co_events = compute_num_co_events(df['timestamp'], df['end_timestamp'])
    df['num_co_events'] = co_events
    
    # 2. Sample Weights (Unikalumas)
    weights = compute_sample_weights(df['timestamp'], df['end_timestamp'], co_events)
    df['uniqueness_weight'] = weights
    
    # Išsaugoti rezultatus
    out_dir = os.path.dirname(args.output)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    df[['timestamp', 'end_timestamp', 'num_co_events', 'uniqueness_weight']].to_csv(args.output, index=False)
    
    print(f"\n✅ SĖKMĖ: Uniqueness svoriai išsaugoti į {args.output}")
    print("\nStatistika:")
    print(f"Vidutinis persidengimas (numCoEvents): {df['num_co_events'].mean():.2f} barai")
    print(f"Vidutinis unikalumas (Weight): {df['uniqueness_weight'].mean():.4f} (Max: 1.0 = visiškai unikalus)")

if __name__ == "__main__":
    main()
