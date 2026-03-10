import pandas as pd
import numpy as np
import os
import glob

# Konfigūracija
MASTER_FILE = r"C:\Users\Mr. Perfect\tradingbot\data\synthetic\BTCUSDT_fracdiff_d0.25_full_universe.csv"
EXTRACTED_DIR = r"C:\Users\Mr. Perfect\tradingbot\ML_Pipeline\03_features\extracted"
OUTPUT_FILE = r"C:\Users\Mr. Perfect\tradingbot\data\synthetic\BTCUSDT_fracdiff_d0.25_full_universe_real_funding.csv"

def merge_funding():
    print(f"Skaitymas master failą: {MASTER_FILE}")
    df_master = pd.read_csv(MASTER_FILE)
    
    # Paverčiame timestamp į datetime
    df_master['dt'] = pd.to_datetime(df_master['timestamp'], unit='ms')
    
    # Surinkti visus funding CSV failus
    funding_files = glob.glob(os.path.join(EXTRACTED_DIR, "*.csv"))
    funding_dfs = []
    
    for f in funding_files:
        temp_df = pd.read_csv(f)
        # Stulpeliai: calc_time, funding_interval_hours, last_funding_rate
        # Pavadiname btc_funding_rates
        temp_df = temp_df[['calc_time', 'last_funding_rate']]
        temp_df.columns = ['timestamp', 'real_funding_rate']
        funding_dfs.append(temp_df)
    
    df_funding = pd.concat(funding_dfs).sort_values('timestamp')
    df_funding['dt'] = pd.to_datetime(df_funding['timestamp'], unit='ms')
    
    print(f"Nuskaityta {len(df_funding)} funding įrašų.")

    # Naudojame merge_asof, kad kiekvienam Dollar Bar priskirtume tuo metu galiojusį funding
    # (Dollar Bar timestamp >= Funding timestamp)
    df_master = df_master.sort_values('dt')
    df_funding = df_funding.sort_values('dt')
    
    merged_df = pd.merge_asof(
        df_master, 
        df_funding[['dt', 'real_funding_rate']], 
        on='dt', 
        direction='backward'
    )
    
    # Pakeičiame seną btc_funding_rates nauju real_funding_rate
    if 'btc_funding_rates' in merged_df.columns:
        print("Pakeičiamas sintetinis btc_funding_rates tikruoju.")
        merged_df['btc_funding_rates'] = merged_df['real_funding_rate']
        # Jei buvo senesnių pavadinimų iš anksčiau
        if 'feature_funding_rate' in merged_df.columns:
            merged_df['feature_funding_rate'] = merged_df['real_funding_rate']
            
    # Ištriname papildomus stulpelius
    merged_df = merged_df.drop(columns=['dt', 'real_funding_rate'])
    
    # Išsaugome
    merged_df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Sėkmingai sujungta! Galutinis failas: {OUTPUT_FILE}")
    
    # Taip pat atnaujiname individualų btc_funding_rates failą synthetic aplanke
    funding_csv_path = r"C:\Users\Mr. Perfect\tradingbot\data\synthetic\synthetic\btc_funding_rates.csv"
    if os.path.exists(funding_csv_path):
        # Sukuriame atskirą failą tik funding
        # Kadangi faile btc_funding_rates.csv paprastai yra tik timestamp ir reikšmė
        # Reikia užtikrinti, kad jis būtų sinchronizuotas su master failo eilutėmis (pagal timestamp)
        df_individual = merged_df[['timestamp', 'btc_funding_rates']]
        df_individual.to_csv(funding_csv_path, index=False)
        print(f"Atnaujintas individualus failas: {funding_csv_path}")

if __name__ == "__main__":
    merge_funding()
