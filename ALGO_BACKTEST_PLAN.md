# 🎯 Algoritminės Prekybos (Be ML) Backtesting Planas

Šis planas skirtas ištestuoti 13 mokslinių strategijų naudojant **Dollar Bars** duomenis (2020-2025). 
**Griežta taisyklė:** JOKIO ML signalams. ML naudojamas tik vėliau Risk Manager sluoksnyje.

## 📁 Duomenų struktūra
- **Šaltinis:** `C:\Users\Mr. Perfect\tradingbot\data` (Dollar Bars)
- **Formatas:** CSV/Parquet (100M USD Threshold)
- **Laikotarpis:** 2020-2025 m.

## 🛠 Strategijų sąrašas testavimui

### 1 grupė: Mikrostruktūros signalai (High Frequency Logic)
1. **VPIN (Volume-Synchronized Probability of Informed Trading):** Signalas generuojamas, kai pirkimo/pardavimo srautas tampa per daug toksiškas.
2. **Order Flow Imbalance (OFI):** Grynas skirtumas tarp bid/ask agresijos kiekvieno Dollar Bar viduje.
3. **Structural Breaks:** Įėjimas, kai 100M baras užsidaro neįprastai greitai (akceleracija).
4. **Inventory-Based Logic:** Reagavimas į greitą orderbook lygų „išplovimą“.

### 2 grupė: Statistiniai ir Mean Reversion signalai
5. **VWAP Mean Reversion:** Pirkimas/Pardavimas pagal nuokrypį (Standard Deviation) nuo Volume-Weighted Average Price.
6. **Z-Score Statistical Arbitrage:** Įėjimas, kai kaina išeina iš normalaus pasiskirstymo ribų (tik ant Dollar Bars).
7. **Statistics of Dollar Bars (IID Returns):** Strategija, išnaudojanti Dollar Bars grąžos normališkumą.

### 3 grupė: Makro ir Swing Trading (Lėta prekyba)
8. **Dynamic ADV Thresholding:** Slenksčio keitimas pagal paros apyvartą (orientacija į 4h/1d efektą).
9. **Scalable Momentum:** Jėgos matavimas lyginant sunkiasvorius 100M blokus.
10. **Long-term VPIN Accumulation:** Institucinių pirkėjų kaupimo fazių nustatymas.
11. **Optimal Swing Sampling:** Agreguoti Dollar Bars į didesnius makro blokus trendo nustatymui.
12. **Aggregated Order Flow Dynamics:** Prekyba pagal 24-48 valandų pinigų srauto kryptį.
13. **Information-Driven Breakout:** Tikrasis proveržis, kai kaina kerta lygį su milžinišku Dollar Volume patvirtinimu.

## 🚀 Vykdymo žingsniai (Pipeline)

1. **Phase 1: Data Audit:** Patikrinti Dollar Bars failų vientisumą `C:\Users\Mr. Perfect\tradingbot\data`.
2. **Phase 2: Feature Engineering (Matematinis):** Sukurti funkcijas, kurios skaičiuoja VPIN, OFI ir Z-Score be jokių modelių mokymo.
3. **Phase 3: Backtest Execution:** Paleisti kiekvieną strategiją per `backtesting.py`.
4. **Phase 4: Risk Scaling:** Prijungti ML Risk Manager (tik pozicijų dydžiui ir Stop Loss valdymui).
5. **Phase 5: Reporting:** Sugeneruoti Sharpe Ratio, Max Drawdown ir Win Rate ataskaitas kiekvienai iš 13 strategijų.

## 📝 Pastabos
- Vadovautis `zmogaus_atsakomybes.md` – mes esame Quantai, mes valdome matematiką.
- Visas kodas bus rašomas `C:\Users\Mr. Perfect\tradingbot\strategies\custom` aplanke.
