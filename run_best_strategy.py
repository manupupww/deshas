from scientific_strategies import load_and_prepare_data, DollarBarStatsStrategy
from backtesting import Backtest
import pandas as pd

def run_full_report():
    data_path = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020-2025dollarBars_.csv"
    aggregate_factor = 200 # ~1 dienos baras
    
    print(f"Kraunami duomenys...")
    df = load_and_prepare_data(data_path, aggregate_factor)
    
    # Testuojame 2024 metus
    df = df.loc["2024-01-01":"2024-12-31"]
    
    # Konfigūracija: 10,000 USD pradinė suma, 20x svertas (per margin)
    bt = Backtest(df, DollarBarStatsStrategy, cash=10000, commission=0.0005, margin=0.05)
    stats = bt.run()
    
    # Išvedame PILNĄ ataskaitą
    print("\n" + "="*40)
    print("📜 PILNA BACKTEST ATASKAITA")
    print("="*40)
    print(stats)
    print("="*40)

if __name__ == "__main__":
    run_full_report()
