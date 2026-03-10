"""
ML Backtest — Random Forest Strategija su backtesting.py
=========================================================
Naudoja mūsų treniruotą ML modelį (best_model.pkl) vietoj MA crossover'ių.
Modelis sprendžia: Long (1) arba Short (0), o backtesting.py vykdo sandorius.

Pritaikyta iš Moon Dev's MA Reversal Strategy šablono.
"""

import pandas as pd
import numpy as np
import os
import sys
import glob
import joblib
from backtesting import Backtest, Strategy

# ============================================================
# 1. DUOMENŲ PARUOŠIMAS (Features + OHLCV + ML Predictions)
# ============================================================
def prepare_backtest_data(data_dir, model_path):
    """
    Sujungia Dollar Bars OHLCV + 30 sintetinių rodiklių + ML modelio prognozės.
    Grąžina DataFrame, paruoštą backtesting.py bibliotekai.
    """
    print("=" * 60)
    print("1. DUOMENŲ PARUOŠIMAS BACKTESTUI")
    print("=" * 60)
    
    # --- A. Pakrauname Dollar Bars (OHLCV + FracDiff) ---
    bars_path = os.path.join(data_dir, "BTCUSDT_2020_2022_dollar_bars_fracdiff_d0.10.csv")
    print(f"\n📊 Kraunami Dollar Bars: {bars_path}")
    bars = pd.read_csv(bars_path)
    bars['timestamp'] = pd.to_numeric(bars['timestamp']).astype(np.int64)
    bars = bars.sort_values('timestamp').reset_index(drop=True)
    
    # --- B. Sintetiniai Rodikliai ---
    synthetic_dir = os.path.join(data_dir, "synthetic")
    csv_files = sorted(glob.glob(os.path.join(synthetic_dir, "*.csv")))
    print(f"📈 Kraunami {len(csv_files)} sintetiniai rodikliai...")
    
    df = bars.copy()
    for csv_path in csv_files:
        feat = pd.read_csv(csv_path)
        feat['timestamp'] = pd.to_numeric(feat['timestamp']).astype(np.int64)
        feat = feat.sort_values('timestamp').reset_index(drop=True)
        df = pd.merge_asof(df, feat, on='timestamp', direction='nearest', tolerance=1000000)
    
    print(f"   Sujungta: {df.shape[0]} eilučių, {df.shape[1]} stulpelių")
    
    # --- C. Pakrauname ML Modelį ---
    print(f"\n🤖 Kraunamas ML modelis: {model_path}")
    model_data = joblib.load(model_path)
    model = model_data['model']
    feature_cols = model_data['feature_cols']
    model_name = model_data['model_name']
    accuracy = model_data['accuracy']
    print(f"   Modelis: {model_name} (Accuracy: {accuracy:.4f})")
    print(f"   Features: {len(feature_cols)} stulpeliai")
    
    # --- D. Generuojame ML Prognozes ---
    print("\n🔮 Generuojamos ML prognozės...")
    
    # Paruošiame features matricą
    meta_cols = ['timestamp', 'end_timestamp', 'label', 'uniqueness_weight', 'datetime']
    X = df[feature_cols].copy()
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    X = X.fillna(X.median())
    
    # Prognozės: 1 = Long, 0 = Short
    predictions = model.predict(X)
    # Tikimybės (confidence): kuo arčiau 1.0, tuo labiau modelis tikras
    probabilities = model.predict_proba(X)
    confidence = np.max(probabilities, axis=1)
    
    df['ML_Signal'] = predictions           # 1 = Long, 0 = Short
    df['ML_Confidence'] = confidence         # 0.5 - 1.0 tikimybė
    
    long_count = (df['ML_Signal'] == 1).sum()
    short_count = (df['ML_Signal'] == 0).sum()
    print(f"   Long signalai: {long_count} ({long_count/len(df)*100:.1f}%)")
    print(f"   Short signalai: {short_count} ({short_count/len(df)*100:.1f}%)")
    print(f"   Vidutinė tikimybė (Confidence): {df['ML_Confidence'].mean():.4f}")
    
    # --- E. Formatuojame backtesting.py bibliotekai ---
    # backtesting.py reikalauja: DatetimeIndex + Open, High, Low, Close, Volume (su didžiosiomis raidėmis)
    bt_df = pd.DataFrame({
        'Open': df['open'].values,
        'High': df['high'].values,
        'Low': df['low'].values,
        'Close': df['close'].values,
        'Volume': df['volume'].values,
        'ML_Signal': df['ML_Signal'].values,
        'ML_Confidence': df['ML_Confidence'].values,
    }, index=pd.to_datetime(df['datetime']))
    
    bt_df = bt_df.sort_index(ascending=True)
    
    # Pašaliname duplikatus (jei keli barai tuo pačiu laiku)
    bt_df = bt_df[~bt_df.index.duplicated(keep='first')]
    
    print(f"\n✅ Backtest duomenys paruošti: {len(bt_df)} eilučių")
    print(f"   Laikotarpis: {bt_df.index[0]} → {bt_df.index[-1]}")
    
    return bt_df

# ============================================================
# 2. ML STRATEGIJA (backtesting.py)
# ============================================================
class MLStrategy(Strategy):
    """
    ML-Powered Strategija.
    Vietoj MA crossover'ių naudoja Random Forest modelio prognozes.
    
    Parametrai (optimizuojami):
    - confidence_threshold: minimali tikimybė, kad modelis būtų pakankamai tikras
    - take_profit: pelno fiksavimo riba (%)
    - stop_loss: nuostolio ribojimo riba (%)
    """
    # Optimizuojami parametrai
    confidence_threshold = 0.60    # Min 60% tikimybė
    take_profit = 0.08             # 8% pelnas
    stop_loss = 0.05               # 5% nuostolis
    
    def init(self):
        # Išsaugome ML signalus kaip indikatorius (matysis grafike)
        self.ml_signal = self.I(lambda: self.data.ML_Signal, name='ML Signal', overlay=False)
        self.ml_confidence = self.I(lambda: self.data.ML_Confidence, name='ML Confidence', overlay=False)
    
    def next(self):
        price = self.data.Close[-1]
        signal = self.data.ML_Signal[-1]
        confidence = self.data.ML_Confidence[-1]
        
        # Tik jei modelis pakankamai tikras
        if confidence < self.confidence_threshold:
            return
        
        # Jei neturime pozicijos
        if not self.position:
            if signal == 1:  # LONG signalas
                self.buy(
                    sl=price * (1 - self.stop_loss),
                    tp=price * (1 + self.take_profit)
                )
            elif signal == 0:  # SHORT signalas
                self.sell(
                    sl=price * (1 + self.stop_loss),
                    tp=price * (1 - self.take_profit)
                )
        else:
            # Jei turime Long poziciją, bet modelis sako Short — uždarome
            if self.position.is_long and signal == 0 and confidence >= self.confidence_threshold:
                self.position.close()
            # Jei turime Short poziciją, bet modelis sako Long — uždarome
            elif self.position.is_short and signal == 1 and confidence >= self.confidence_threshold:
                self.position.close()

# ============================================================
# 3. MAIN — Backtesto paleidimas
# ============================================================
def main():
    data_dir = r"C:\Users\Mr. Perfect\tradingbot\data"
    model_path = os.path.join(data_dir, "models", "best_model.pkl")
    
    if not os.path.exists(model_path):
        print(f"❌ KLAIDA: Modelis nerastas: {model_path}")
        print("   Pirma paleisk: py ML_Pipeline/06_ml_training/train.py")
        return
    
    # 1. Paruošiame duomenis
    data = prepare_backtest_data(data_dir, model_path)
    
    # 2. Paleidžiame pradinį backtestą
    print("\n" + "=" * 60)
    print("🌙 ML STRATEGIJOS PRADINIS BACKTESTAS")
    print("=" * 60)
    
    bt = Backtest(
        data, 
        MLStrategy,
        cash=100_000,           # $100,000 pradinis kapitalas
        commission=0.001,       # 0.1% komisiniai (Binance standartinis)
        exclusive_orders=True,  # Viena pozicija vienu metu
        trade_on_close=True     # Sandoriai vykdomi bar'o uždarymo kaina
    )
    
    stats = bt.run()
    print(stats)
    
    # 3. Optimizacija
    print("\n" + "=" * 60)
    print("🚀 ML STRATEGIJOS OPTIMIZACIJA")
    print("=" * 60)
    print("Optimizuojami parametrai: confidence_threshold, take_profit, stop_loss...")
    
    opt_stats = bt.optimize(
        confidence_threshold=[0.55, 0.60, 0.65, 0.70, 0.75],
        take_profit=[0.03, 0.05, 0.08, 0.10, 0.15],
        stop_loss=[0.02, 0.03, 0.05, 0.08, 0.10],
        maximize='Equity Final [$]',
        max_tries=200,
        random_state=42
    )
    
    print("\n🏆 OPTIMIZUOTI REZULTATAI:")
    print("=" * 60)
    print(opt_stats)
    
    print("\n✨ Geriausi parametrai:")
    print(f"   Confidence Threshold: {opt_stats._strategy.confidence_threshold}")
    print(f"   Take Profit: {opt_stats._strategy.take_profit:.0%}")
    print(f"   Stop Loss: {opt_stats._strategy.stop_loss:.0%}")
    
    # 4. Grafikas
    print("\n📊 Generuojamas grafikas...")
    output_path = os.path.join(data_dir, "models", "ml_backtest_results.html")
    bt_optimized = Backtest(data, MLStrategy, cash=100_000, commission=0.001, exclusive_orders=True, trade_on_close=True)
    final_stats = bt_optimized.run(
        confidence_threshold=opt_stats._strategy.confidence_threshold,
        take_profit=opt_stats._strategy.take_profit,
        stop_loss=opt_stats._strategy.stop_loss
    )
    bt_optimized.plot(filename=output_path, open_browser=False)
    print(f"   Grafikas išsaugotas: {output_path}")
    print(f"\n✅ ML BACKTESTAS BAIGTAS!")

if __name__ == "__main__":
    main()
