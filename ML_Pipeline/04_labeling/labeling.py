import pandas as pd
import numpy as np
import os
import argparse

def get_daily_vol(close, span0=100):
    # Supaprastintas kintamumo skaičiavimas:
    # Skaičiuojame log-returns tarp barų ir tada EWM standartinį nuokrypį
    df0 = np.log(close / close.shift(1)).fillna(0)
    df0 = df0.ewm(span=span0).std()
    return df0

def apply_triple_barrier(df, vol, pt_sl=[2, 2], t1=None):
    """
    df: DataFrame su 'close' ir 'timestamp'
    vol: Series su volatility reikšmėmis
    pt_sl: Profit Take ir Stop Loss koeficientai
    t1: Vertical barrier (laiko riba bars skaičiumi)
    """
    # Naudojame paprastą integer indeksavimą, kad išvengtume pandas datetime klaidų
    close = df['close'].values
    ts = df['timestamp'].values
    v_arr = vol.fillna(vol.mean()).values
    n = len(df)
    
    labels = np.zeros(n)
    end_timestamps = np.zeros(n, dtype=np.int64)
    
    print(f"Vykdomas Triple Barrier klasifikavimas ({n} eilučių)...")
    
    for i in range(n - 1):
        if i % 10000 == 0 and i > 0:
            print(f"Progresas: {i}/{n}")
            
        target_vol = v_arr[i]
        upper_barrier = close[i] * (1 + target_vol * pt_sl[0])
        lower_barrier = close[i] * (1 - target_vol * pt_sl[1])
        
        # Horizontas yra i + t1 arba n-1
        horizon = i + t1 if t1 is not None else n - 1
        horizon = min(horizon, n - 1)
        
        hit = False
        for j in range(i + 1, int(horizon) + 1):
            if close[j] >= upper_barrier:
                labels[i] = 1
                end_timestamps[i] = ts[j]
                hit = True
                break
            elif close[j] <= lower_barrier:
                labels[i] = -1
                end_timestamps[i] = ts[j]
                hit = True
                break
                
        if not hit:
            end_timestamps[i] = ts[int(horizon)]
            
    # Paskutinė eilutė gauna savo timestamp
    end_timestamps[n-1] = ts[n-1]
                
    return labels, end_timestamps
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Path to Dollar Bars / FracDiff CSV")
    parser.add_argument("--output_dir", type=str, default="data/labels", help="Output directory")
    parser.add_argument("--pt", type=float, default=2.5, help="Profit Take multiplier")
    parser.add_argument("--sl", type=float, default=1.0, help="Stop Loss multiplier")
    parser.add_argument("--horizon", type=int, default=100, help="Vertical barrier (bars)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"KLAIDA: Failas {args.input} nerastas.")
        return

    print(f"Kraunami duomenys: {args.input}")
    df = pd.read_csv(args.input)
    
    # Ruošiame indeksą volatility skaičiavimui
    df['datetime'] = pd.to_datetime(df['timestamp'], errors='coerce')
    # Jei tai unix ms, timestamp bus NaN po to_datetime be unit, todel bandom vel:
    if df['datetime'].isna().all():
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
    df.set_index('datetime', inplace=True)
    # Isitikiname, kad turime ms stulpeli integer formatu tolimesniam naudojimui
    df['timestamp'] = (df.index.view('int64') // 10**6).astype(np.int64)
    
    # 1. Skaičiuojame kintamumą
    print("Skaičiuojamas kintamumas (Daily Volatility)...")
    vol = get_daily_vol(df['close'])
    
    # 2. Taikome Triple Barrier Method
    labels, end_timestamps = apply_triple_barrier(df, vol, pt_sl=[args.pt, args.sl], t1=args.horizon)
    
    df['label'] = labels
    df['end_timestamp'] = end_timestamps
    
    # 3. Išsaugome rezultatus
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        
    out_path = os.path.join(args.output_dir, "BTCUSDT_labels.csv")
    
    # Saugome su end_timestamp laukais
    df_labels = df.reset_index()[['timestamp', 'end_timestamp', 'label']]
    df_labels.to_csv(out_path, index=False)
    
    print(f"\n✅ SĖKMĖ: Sugeneruotas failas {out_path}")
    print("\nKlasių pasiskirstymas:")
    print(df['label'].value_counts(normalize=True))

if __name__ == "__main__":
    main()
