import pandas as pd
import numpy as np
import os
import argparse

def load_real_data(binance_dir):
    # 1. Load Funding Rates
    all_funding = []
    for f in os.listdir(binance_dir):
        if "fundingRate" in f and f.endswith(".csv"):
            tmp = pd.read_csv(os.path.join(binance_dir, f))
            if not tmp.empty:
                # Force numeric before appending to avoid object-type concat
                # Binance columns: calc_time, last_funding_rate
                tmp['timestamp'] = pd.to_numeric(tmp['calc_time'], errors='coerce')
                all_funding.append(tmp[['timestamp', 'last_funding_rate']])
    
    if not all_funding:
        df_funding = pd.DataFrame(columns=['timestamp', 'last_funding_rate'])
    else:
        df_funding = pd.concat(all_funding).dropna(subset=['timestamp']).sort_values("timestamp")

    # 2. Load Premium Index (1h)
    all_premium = []
    for f in os.listdir(binance_dir):
        if "-1h-" in f and f.endswith(".csv"):
            # Headerless CSV
            tmp = pd.read_csv(os.path.join(binance_dir, f), header=None, 
                              names=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'not', 'tbb', 'tbq', 'ignore'])
            if not tmp.empty:
                tmp['timestamp'] = pd.to_numeric(tmp['timestamp'], errors='coerce')
                all_premium.append(tmp[['timestamp', 'close']])
    
    if not all_premium:
        df_premium = pd.DataFrame(columns=['timestamp', 'real_premium'])
    else:
        df_premium = pd.concat(all_premium).dropna(subset=['timestamp']).sort_values("timestamp")
        df_premium.rename(columns={'close': 'real_premium'}, inplace=True)

    return df_funding, df_premium

def generate_synthetic_features(input_file, output_file):
    print(f"Ieskoma failo: {input_file}")
    if not os.path.exists(input_file):
        print(f"KLAIDA: Failas [{input_file}] nerastas!")
        return

    # Nuskaityti Dollar Bars duomenis
    # AFML UPGRADE: Handling headerless BTC Dollar Bars
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'dollar_volume']
    df = pd.read_csv(input_file, names=cols, header=None)
    
    # Konvertuojame datetime string -> unix ms
    print("Konvertuojami laikrodis i unix ms...")
    df['timestamp_orig'] = df['timestamp'] 
    
    # Isitikiname, kad timestamp yra skaicius (ms) ir SVEIKAS SKAICIUS (int64)
    # AFML FIX: Robust string to unix ms conversion
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    df['timestamp'] = (df['timestamp'].view('int64') // 10**6).astype(np.int64)
    
    df = df.sort_values("timestamp")
    print(f"Nuskaityta {len(df)} eiluciu.")

    # Įkelti TIKRUS duomenis jei jie egzistuoja
    binance_dir = r"C:\Users\Mr. Perfect\tradingbot\data\binance_vision"
    real_funding = pd.DataFrame(columns=['timestamp', 'last_funding_rate'])
    real_premium = pd.DataFrame(columns=['timestamp', 'real_premium'])
    
    if os.path.exists(binance_dir):
        print("Kraunami tikri Binance duomenys...")
        real_funding, real_premium = load_real_data(binance_dir)

    # Merginame tikrus duomenis
    if not real_funding.empty:
        real_funding['timestamp'] = pd.to_numeric(real_funding['timestamp'], errors='coerce')
        real_funding = real_funding.dropna(subset=['timestamp'])
        real_funding['timestamp'] = real_funding['timestamp'].astype(np.int64)
        real_funding = real_funding.sort_values('timestamp')
        df = pd.merge_asof(df, real_funding, on='timestamp', direction='backward')
    else:
        df['last_funding_rate'] = 0

    if not real_premium.empty:
        real_premium['timestamp'] = pd.to_numeric(real_premium['timestamp'], errors='coerce')
        real_premium = real_premium.dropna(subset=['timestamp'])
        real_premium['timestamp'] = real_premium['timestamp'].astype(np.int64)
        real_premium = real_premium.sort_values('timestamp')
        df = pd.merge_asof(df, real_premium, on='timestamp', direction='backward')
    else:
        df['real_premium'] = df['close'] 

    # Konvertuojame i Datetime objektus tolimesniems skaiciavimams
    dt = pd.to_datetime(df['timestamp'], errors='coerce')
    df['dt'] = dt
    
    # Režimų kaukės (Masks) naudojant Datetime
    is_bull_run = (df['dt'] >= '2020-10-01') & (df['dt'] <= '2021-11-15')
    is_luna_crash = (df['dt'] >= '2022-05-01') & (df['dt'] <= '2022-05-31')
    is_ftx_crash = (df['dt'] >= '2022-11-01') & (df['dt'] <= '2022-11-30')
    is_bear_market = (df['dt'] >= '2022-01-01') & (df['dt'] <= '2022-12-31') & ~is_luna_crash & ~is_ftx_crash

    # Baziniai pagalbiniai kintamieji
    returns = np.log(df['close'] / df['close'].shift(1)).fillna(0)
    
    # 32 Rodikliu apibrezimai su ISTORINIU REZIMU LOGIKA
    
    # Whales - Netflow (Luna/FTX metu massive inflows to sell)
    base_netflow = np.where(returns < -0.01, np.random.uniform(500, 2000, len(df)), np.random.uniform(-1000, 500, len(df)))
    base_netflow = np.where(is_luna_crash | is_ftx_crash, base_netflow + 15000, base_netflow)
    
    # Whales - Reserves (Bull run metu mazeja, bear market metu dideja)
    reserve_trend = np.where(is_bull_run, -2000, np.where(is_bear_market, 1000, 0))
    base_reserve = 2_400_000 + np.cumsum(reserve_trend) - (returns.cumsum() * 1000) + np.random.normal(0, 1000, len(df))

    # Whales - Whale Ratio (per panikas banginiai siuncia daugiausia)
    whale_ratio = 0.35 + (returns.rolling(50).mean() * 3) + np.random.normal(0, 0.05, len(df))
    whale_ratio = np.where(is_luna_crash | is_ftx_crash, whale_ratio + 0.4, whale_ratio)

    # Miners - MPI (Bull run virsuneje masiskai parduoda)
    mpi = np.where(returns.shift(-10) < -0.05, np.random.uniform(2, 6, len(df)), np.random.uniform(0, 1, len(df)))
    mpi = np.where(is_bull_run & (dt > '2021-03-01'), mpi + 2.0, mpi)
    
    # Derivatives - Open Interest (Iki 2021 virsunes kyla, po to crashina)
    oi_trend = np.where(is_bull_run, 2000000, np.where(is_bear_market, -1000000, 500000))
    oi = 300_000_000 + np.cumsum(oi_trend) + np.random.normal(0, 5_000_000, len(df))
    # Crashes wipe out OI
    oi = np.where(is_luna_crash, oi * 0.6, oi)
    oi = np.where(is_ftx_crash, oi * 0.7, oi)

    # Derivatives - Liquidations (Per panikas kosminiai likvidavimai)
    liq_multiplier = np.where(is_luna_crash | is_ftx_crash, 500, 50)
    long_liq = np.where(returns < 0, (df['dollar_volume'] * 0.001) * np.abs(returns) * liq_multiplier, (df['dollar_volume'] * 0.001) * 0.1)
    short_liq = np.where(returns > 0, (df['dollar_volume'] * 0.001) * np.abs(returns) * liq_multiplier, (df['dollar_volume'] * 0.001) * 0.1)

    # Marketplace - MVRV (Synthetic realized value)
    mvrv = 1.5 + (returns.cumsum() * 0.05) + np.random.normal(0, 0.1, len(df))
    mvrv = np.clip(mvrv, 0.5, 4.5) # Riba realistiškumui

    # Strategy Indicators Addition
    # 1. 10-day MAX strategy (assuming hourly data -> 240 periods, if daily -> 10 periods)
    # To be safe for any timeframe, we will calculate based on raw periods.
    # The thesis discusses 20-period moving average on hourly data for Bollinger Bands.
    # We will compute columns for 10, 20, 50, 240 periods.
    rolling_max_240 = df['close'].rolling(240).max()  # roughly 10 days of hourly data
    rolling_max_10 = df['close'].rolling(10).max()    # strictly 10 periods (for daily data)
    
    sma_20 = df['close'].rolling(20).mean()
    sma_50 = df['close'].rolling(50).mean()
    
    std_20 = df['close'].rolling(20).std()
    bb_upper = sma_20 + (2 * std_20)
    bb_lower = sma_20 - (2 * std_20)

    # Balvers & Wu (2006) - Momentum and Mean Reversion
    log_p = np.log(df['close'])
    bw_mr = -(log_p - log_p.rolling(500).mean()).fillna(0)
    bw_mom = log_p.diff(12).fillna(0)
    bw_indicator = bw_mr + bw_mom

    metrics = {
        "bw_mean_reversion": bw_mr,
        "bw_momentum": bw_mom,
        "bw_indicator": bw_indicator,
        
        # New Strategy Features
        "rolling_max_10": rolling_max_10,
        "rolling_max_240": rolling_max_240,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "btc_exchange_netflow": base_netflow,
        "btc_exchange_reserve": base_reserve,
        "btc_exchange_reserve_usd": np.nan, 
        "btc_exchange_inflow_total": np.random.uniform(1000, 5000, len(df)) + np.where(is_luna_crash, 20000, 0),
        "btc_exchange_outflow_total": np.nan, 
        "btc_exchange_whale_ratio": whale_ratio,
        "btc_exchange_stablecoins_ratio": 10 + (returns.cumsum() * 0.1) + np.random.normal(0, 1, len(df)),
        "btc_exchange_stablecoins_ratio_usd": np.nan, 
        "stablecoin_exchange_netflow": np.random.uniform(-50_000_000, 50_000_000, len(df)),
        "stablecoin_exchange_reserve": 1_000_000_000 + (returns.cumsum() * -5_000_000),
        "stablecoin_exchange_inflow_total": np.random.uniform(10_000_000, 100_000_000, len(df)),
        "stablecoin_exchange_outflow_total": np.nan, 
        
        "btc_miners_position_index": mpi,
        "btc_miner_netflow_total": np.random.uniform(-500, 500, len(df)),
        "btc_puell_multiple": 1.2 + (returns.rolling(200).sum() * 1.5) + np.random.normal(0, 0.2, len(df)),
        
        "btc_funding_rates": df['last_funding_rate'].ffill().fillna(0),
        "btc_open_interest": oi,
        "btc_taker_buy_sell_ratio": 1.0 + (returns * 8) + np.random.normal(0, 0.05, len(df)),
        "btc_long_liquidations": long_liq,
        "btc_long_liquidations_usd": np.nan, 
        "btc_short_liquidations": short_liq,
        "btc_short_liquidations_usd": np.nan, 
        
        "btc_mvrv_ratio": mvrv,
        
        "btc_exchange_supply_ratio": 0.15 - (returns.cumsum() * 0.001),
        "btc_fund_flow_ratio": 0.05 + np.random.normal(0, 0.01, len(df)),
        "stablecoin_exchange_supply_ratio": 20 + (returns.cumsum() * 0.5),
        
        "btc_coinbase_premium_index": pd.to_numeric(df['real_premium'], errors='coerce').ffill().fillna(0) * 100, 
        "btc_coinbase_premium_gap": np.nan, 
        "btc_korea_premium_index": np.random.uniform(-1, 5, len(df))
    }

    # Sukuriame stulpelius df
    for name, values in metrics.items():
        df[name] = values
            
    # Suskaiciuojame isvestinius
    df['btc_exchange_reserve_usd'] = df['btc_exchange_reserve'] * df['close']
    df['btc_exchange_outflow_total'] = df['btc_exchange_inflow_total'] - df['btc_exchange_netflow']
    df['btc_exchange_stablecoins_ratio_usd'] = df['btc_exchange_stablecoins_ratio'] * 1_000_000
    df['stablecoin_exchange_outflow_total'] = df['stablecoin_exchange_inflow_total'] - df['stablecoin_exchange_netflow']
    df['btc_long_liquidations_usd'] = df['btc_long_liquidations'] * df['close']
    df['btc_short_liquidations_usd'] = df['btc_short_liquidations'] * df['close']
    df['btc_coinbase_premium_gap'] = pd.to_numeric(df['btc_coinbase_premium_index'], errors='coerce') * 0.8

    # Nuimame laikinus stulpelius
    df.drop(columns=['last_funding_rate', 'real_premium'], inplace=True, errors='ignore')

    # Isitikiname, kad visi stulpeliai (isskyrus timestamp) yra skaiciai pries apvalinima
    for col in df.columns:
        if 'timestamp' not in col:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Sutvarkome apvalinimus
    for col in df.columns:
        if 'timestamp' in col: continue
        if any(x in col for x in ['liquidations', 'volume', 'interest', 'reserve', 'netflow', 'inflow', 'outflow', 'gap']):
            df[col] = df[col].round(2)
        elif 'rate' in col:
            df[col] = df[col].round(8)
        else:
            df[col] = df[col].round(4)

    # Išsaugome 32 ATSKIRUS failus i data/synthetic
    dir_name = r"C:\Users\Mr. Perfect\tradingbot\data\synthetic"
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    else:
        # Isvalome senus failus, kad nebutu siuksliu (tik .csv)
        print(f"Valomas katalogas: {dir_name}")
        for f in os.listdir(dir_name):
            f_path = os.path.join(dir_name, f)
            if os.path.isfile(f_path) and f.endswith(".csv"):
                os.remove(f_path)

    print("\n📁 Generuojami individualūs rodiklių failai...")
    
    # Saugome visus stulpelius (isskyrus techninius) kaip atskirus CSV
    exclude_cols = ['timestamp_numeric', 'open', 'high', 'low', 'close', 'volume', 'dollar_volume', 'datetime']
    
    saved_count = 0
    for col in df.columns:
        if col == 'timestamp' or col in exclude_cols:
            continue
            
        path = os.path.join(dir_name, f"{col}.csv")
        df[['timestamp', col]].to_csv(path, index=False)
        saved_count += 1
            
    print(f"\n✅ REZULTATAS: Sugeneruoti {saved_count} individualūs failai.")
    print(f"📂 Visi duomenys randasi: {dir_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Path to Fractional Diff CSV")
    parser.add_argument("--output", type=str, help="Output master features.csv")
    args = parser.parse_args()

    out = args.output
    if not out:
        base, ext = os.path.splitext(args.input)
        out = f"{base}_master_features{ext}"

    generate_synthetic_features(os.path.abspath(args.input), os.path.abspath(out))
