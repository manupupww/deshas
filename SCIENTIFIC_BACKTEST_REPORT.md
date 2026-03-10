# 📊 Scientific Backtest Report (2024-2025 BTC Dollar Bars)

Ši ataskaita skirta tavo **8 mokslinių strategijų** backtest rezultatams išsaugoti. Rezultatai gauti naudojant **200x agregaciją** (simuliuojamas ~1 dienos Bitcoin ADV slenkstis).

---

## 📈 Backtest Rezultatų Suvestinė (2024 metai)

| Strategija | Grąža [%] | Sharpe Ratio | Win Rate [%] | Max Drawdown [%] |
| :--- | :--- | :--- | :--- | :--- |
| **DollarBarStatsStrategy** | **+145.18%** | 0.177 | 60.0% | -48.82% |
| **OFIStrategy** | **+46.44%** | 0.420 | 100.0% | -16.48% |
| VPINStrategy | -27.93% | -0.122 | 42.8% | -67.69% |
| StructuralBreakStrategy | -69.45% | -0.865 | 55.5% | -89.69% |
| VWAPReversionStrategy | 0.00% | NaN | NaN | 0.00% |
| MarketIntensityStrategy | -100.00% | 0.00 | 37.5% | -100.00% |
| DollarMomentumStrategy | -100.00% | 0.00 | 42.8% | -100.00% |
| SyntheticFlowStrategy | -100.00% | 0.00 | 50.0% | -100.00% |

---

## 🛠️ Esminiai Pakeitimai ir Rizikos Valdymas

Štai kodo fragmentai ir paaiškinimai, ką pakeitėme, kad rezultatai taptų stabilesni:

### 1. Griežtas Stop Loss (Fixed SL)
Pagal tavo nurodymą, Stop Loss dabar **nejuda**. Jis lieka fiksuotas ties -20% nuo įėjimo kainos.

```python
# Faile: scientific_strategies.py -> RiskManagementMixin
fixed_sl_pct = 0.20  # Griežtas SL (20%)

def check_risk_management(self):
    current_pnl = self.position.pl_pct
    # JEI kaina nukrenta 20% - uždarome poziciją (fiksuotas nejudantis dugnas)
    if current_pnl < -self.fixed_sl_pct:
        self.position.close()
```

### 2. Trailing Take Profit (Profit Protector)
Kad „laimėtojai bėgtų“ ir neprarastume uždirbto pelno, įdiegta **Trailing TP** sistema. Ji užfiksuoja pelną tik tada, kai kaina pasiekia piką ir pradeda kristi.

```python
# Faile: scientific_strategies.py -> RiskManagementMixin
tp_trail_activation = 0.03  # Aktyvuojasi ties +3% pelnu
tp_trail_callback = 0.02    # Uždaro, jei kaina nukrenta 2% nuo pasiekto piko

def check_risk_management(self):
    # Sekame aukščiausią pasiektą pelno tašką (peak_pnl)
    self.peak_pnl = max(self.peak_pnl, current_pnl)

    # Jei buvome pasiekę bent 3% pelną:
    if self.peak_pnl >= self.tp_trail_activation:
        # Jei kaina nukrenta 2% nuo piko (pvz. nuo 15% iki 13%):
        if current_pnl < (self.peak_pnl - self.tp_trail_callback):
            self.position.close() # Fiksuojame pelną
```

### 3. Duomenų Agregacija (Threshold)
Kad gautume „lėtą“ efektą, naudojame **Factor 200**. Tai reiškia, kad botas mato ne 100M USD blokus, o **20B USD** blokus (apytikslė BTC paros apyvarta).

---

## 📝 Kaip redaguoti pačiam?

1.  **Norite didesnio / mažesnio saugumo?**
    *   Keisk `fixed_sl_pct` reikšmę `scientific_strategies.py` faile (pvz. `0.10` bus 10% SL).
2.  **Norite leisti laimėtojams bėgti dar toliau?**
    *   Sumažink `tp_trail_callback` (pvz. `0.01` bus 1% atstumas).
3.  **Norite pakeisti strategijos jautrumą?**
    *   Keisk `aggregate_factor` faile `run_all_scientific.py`. Mažesnis skaičius (pvz. 30) darys strategiją „greitesnę“.

---
*Ataskaita sugeneruota automatiškai Gemini CLI pagal paskutinį sėkmingą backtestą.*
