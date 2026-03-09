from scientific_strategies import load_and_prepare_data, DollarBarStatsStrategy
from backtesting import Backtest
import pandas as pd

def investigate_trades():
    data_path = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020-2025dollarBars_.csv"
    aggregate_factor = 200
    
    df = load_and_prepare_data(data_path, aggregate_factor)
    df = df.loc["2024-01-01":"2024-12-31"]
    
    bt = Backtest(df, DollarBarStatsStrategy, cash=10000, commission=0.0005, margin=0.05)
    stats = bt.run()
    
    # Ištraukiame visus trade'us
    trades = stats['_trades']
    
    print("\n" + "="*90)
    print("🔍 DETALI SANDORIŲ ANALIZĖ (DollarBarStatsStrategy)")
    print("="*90)
    # Atrenkame svarbiausius stulpelius: Įėjimo laikas, Išėjimo laikas, Pelnas/Nuostolis procentais, Tipas
    display_trades = trades[['EntryTime', 'ExitTime', 'Size', 'EntryPrice', 'ExitPrice', 'PnL', 'ReturnPct']]
    print(display_trades.to_string(index=False))
    print("="*90)
    
    # Paaiškinimas apie nesėkmes
    losses = trades[trades['PnL'] < 0]
    print(f"\nIš viso sandorių: {len(trades)}")
    print(f"Laimėjimai: {len(trades[trades['PnL'] > 0])}")
    print(f"Pralaimėjimai: {len(losses)}")
    
    if not losses.empty:
        print("\n⚠️ KUR SUSIMOVĖ:")
        for i, row in losses.iterrows():
            print(f"- Sandoris #{i+1}: Įėjo {row['EntryTime']}, išėjo {row['ExitTime']}.")
            print(f"  Rezultatas: {row['ReturnPct']*100:.2f}% nuostolis.")
            print(f"  Priežastis: Tikriausiai kaina kirto SMA 50 arba suveikė SL/TP logika anksčiau laiko.")

if __name__ == "__main__":
    investigate_trades()
