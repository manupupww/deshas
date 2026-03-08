# ML Alpha v2 - Risk Managed Strategy

Ši strategijos versija apjungia **ML Alpha v1** signalus su **ML Risk Manager** sluoksniu.

## Patobulinimai
1. **Dynamic Bet Sizing:** Pozicijos dydis parenkamas dinamiškai pagal modelio pasitikėjimo lygį (Confidence).
2. **Confidence Filtering:** Sandoriai vykdomi tik tada, kai modelio pasitikėjimas > 70%.
3. **Capital Protection:** Rizika vienam sandoriui apribota iki 2% nuo viso kapitalo.

## Failų Struktūra
* `backtest.py` - Pagrindinis backtesto skriptas (v2).
* `risk_manager.py` - Rizikos valdymo modulis.
* `best_model.pkl` - Apmokytas Random Forest modelis.
* `ml_risk_results.html` - Interaktyvus grafikas su rezultatais.

## Backtest Rezultatai (2020-2022)
* **Equity Final:** $108,146 (+8.14%)
* **Exposure Time:** 1.60% (Labai saugu)
* **Max Drawdown:** ~ -1.5%
* **Win Rate:** ~ 90%

Nors pelnas mažesnis nei v1 (+1654%), ši strategija yra **daug saugesnė**, nes rinkoje praleidžia tik 1.6% laiko ir agresyviai didina statymus tik pajutus „auksines“ progas.

## Kaip paleisti
```bash
py strategies/ML_Alpha_v2_RiskManaged/backtest.py
```
