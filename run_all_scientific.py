from scientific_strategies import (
    load_and_prepare_data,
    VPINStrategy,
    OFIStrategy,
    StructuralBreakStrategy,
    VWAPReversionStrategy,
    MarketIntensityStrategy,
    DollarBarStatsStrategy,
    DollarMomentumStrategy,
    SyntheticFlowStrategy
)
from backtesting import Backtest
import pandas as pd

def run_all():
    data_path = r"C:\Users\Mr. Perfect\tradingbot\data\BTCUSDT_2020-2025dollarBars_.csv"
    
    # Konfigūracija
    aggregate_factor = 200 # ~1 dienos baras
    
    print(f"Kraunami duomenys (Factor {aggregate_factor})...")
    df = load_and_prepare_data(data_path, aggregate_factor)
    df = df.loc["2024-01-01":"2024-12-31"]
    
    strategies = [
        VPINStrategy, OFIStrategy, StructuralBreakStrategy,
        VWAPReversionStrategy, MarketIntensityStrategy,
        DollarBarStatsStrategy, DollarMomentumStrategy, SyntheticFlowStrategy
    ]
    
    results = []
    
    for strat in strategies:
        print(f"Testuojama: {strat.__name__}...")
        try:
            bt = Backtest(df, strat, cash=10000, commission=0.0005, margin=0.05)
            stats = bt.run()
            results.append({
                'Strategy': strat.__name__,
                'Return [%]': stats['Return [%]'],
                '# Trades': stats['# Trades'],
                'Win Rate [%]': stats['Win Rate [%]'],
                'Sharpe Ratio': stats['Sharpe Ratio'],
                'Max DD [%]': stats['Max. Drawdown [%]']
            })
        except Exception as e:
            print(f"Klaida su {strat.__name__}: {e}")
            
    print("\n" + "="*70)
    print(f"📊 BACKTEST SUVESTINĖ (2024 metai, Factor: {aggregate_factor})")
    print("="*70)
    summary_df = pd.DataFrame(results)
    print(summary_df.to_string(index=False))
    print("="*70)

if __name__ == "__main__":
    run_all()
