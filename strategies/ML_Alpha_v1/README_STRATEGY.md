# 🌲 Strategija: ML Alpha v1 (Regime-Sensing)

Ši strategija yra profesionalus mašininio mokymosi (ML) įrankis, sukurtas 2026 m. kovo mėn. Ji skirta BTC/USDT prekybai, naudojant **Dollar Bars** ir on-chain/rinkos srautų duomenis.

---

## 🧐 Kas tai per strategija?
Tai nėra paprasta trendo sekimo ar reindžo strategija. Tai **Modelių atpažinimo (Pattern Recognition)** sistema. 
Ji veikia kaip „detektyvas“, kuris stebi 30 skirtingų rinkos sluoksnių ir ieško specifinių „nuotaikų“ (režimų), kurie istoriškai lėmė kainos kilimą arba kritimą.

### Esminiai principai:
1. **Dollar Bars:** Prekiauja ne pagal laikrodį, o pagal pinigų apyvartą (100 mln. USD per barą). Tai padeda išvengti triukšmo ramioje rinkoje.
2. **Confidence Filter (0.70):** Strategija yra „snaiperis“. Ji atidaro sandorį tik tada, kai modelis yra **70% užtikrintas** savo prognoze. Jei signalas silpnas – ji stovi nuošalyje (Cash).
3. **Multi-Factor:** Analizuoja ne kainą, o biržų atsargas, Open Interest, likvidacijas ir arbitražo skirtumus tarp biržų.

---

## 📈 Backtesto Rezultatai (2020-07-27 – 2022-12-03)
*   **Grynasis pelnas:** **+1654.51%** (palyginimui: Buy & Hold +58.60%)
*   **Win Rate:** **90.38%** (labai aukštas dėl griežto filtro)
*   **Sharpe Ratio:** **1.446**
*   **Max Drawdown:** **-43.50%**
*   **Sandorių kiekis:** 208 (vidutiniškai 2 sandoriai per savaitę)

---

## 💾 Failų struktūra
* `trainer.py` — Kodas, skirtas modelio pergaminimui su naujais duomenimis.
* `backtest.py` — Kodas, skirtas testuoti strategiją su istoriniais duomenimis.
* `best_model.pkl` — Pats „protingiausias“ modelis (Random Forest).
* `backtest_results.html` — Interaktyvus grafikas su visais sandoriais.

---

## 🛠️ Naudoti parametrai
- **Modelis:** Random Forest (65.59% accuracy)
- **Confidence Threshold:** 0.70
- **Take Profit (TP):** 3%
- **Stop Loss (SL):** 10%
- **Komisiniai:** 0.1%

---

## 🚀 Kaip paleisti?
Jei nori vėl paleisti backtestą:
```bash
py strategies/ML_Alpha_v1/backtest.py
```
Jei nori peržiūrėti grafikus, atidaryk `backtest_results.html` per naršyklę.
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


Jei norime pasiekti +100 rodiklių (features) ribą, kripto pasaulyje tai yra visiškai realu. Norint gauti papildomus 70 rodiklių, turime „spausti“ maksimalią informaciją iš tavo turimų šaltinių (Hyperliquid L4, Binance, Sentiment AI ir t.t.).

Štai sąrašas rodiklių, suskirstytų į kategorijas, kuriuos galime pridėti:

1. Orderbook (L2/L4) Microstructure (15 naujų rodiklių)
Kadangi turi Hyperliquid L4 duomenis, čia slypi didžiausias „Alpha“:

Bid/Ask Imbalance (skirtingais lygiais): Kiek pirkėjų vs pardavėjų stovi 0.1%, 1% ir 5% atstumu nuo kainos.
Slippage Metrics: Kiek dolerių kainuotų pastumti rinką 1% į viršų ar apačią (Market Depth).
Order Cancellation Rate: Kaip greitai algoritmai atšaukia pavedimus (rodo „spofingą“).
Spread Volatility: Kaip stipriai šokinėja skirtumas tarp Buy/Sell.
2. Taker/Maker Flow (10 naujų rodiklių)
Buy/Sell Volume Ratio (Taker): Kas agresyviau perka per rinką (market orders).
Average Trade Size: Ar dabar prekiauja mažmeninė rinka (retail), ar institucijos (dideli sandoriai).
Trade Frequency: Kiek sandorių įvyksta per vieną Dollar Barą (rodo rinkos paniką ar euforiją).
3. Išplėstiniai On-Chain (20 naujų rodiklių)
Naudojant tavo „Golden Mine“ duomenis:

HODL Waves: Kokių amžiaus grupių BTC juda (pvz., ar 5-10 metų „miegančios“ piniginės pradėjo judėti).
SOPR (Spent Output Profit Ratio): Ar žmonės dabar parduoda su pelnu, ar su nuostoliu (nuostolių fiksavimas dažnai rodo dugną).
Active Addresses Momentum: Ar tinkle daugėja naujų vartotojų.
Realized Cap / Market Cap (MVRV): Ar kaina yra pervertinta, lyginant su tuo, už kiek žmonės ją pirko.
4. Sentimentas ir Socialiniai (10 naujų rodiklių)
Iš tavo „Sentiment AI Analyzer“:

News Buzz Score: Naujienų srauto intensyvumas (ne tik sentimentas, bet ir kiekis).
Fear & Greed Index Delta: Kaip greitai keičiasi minios baimės jausmas.
Twitter/X Mention Momentum: Kiek projektas „šviečia“ radaruose.
5. Išvestiniai TA (Technical Analysis) ant Dollar Bars (15 naujų rodiklių)
Dauguma naudoja TA ant laiko žvakių, mes galime pritaikyti tai Dollar Bars:

RSI / MACD / Bollinger Bands: Bet paskaičiuoti būtent mūsų Dollar Bars duomenyse (tai duoda filtravimą nuo triukšmo).
ADX (Trend Strength): Ar dabartinis judėjimas turi jėgos, ar tai tiesiog atsitiktinis svyravimas.
Standard Deviation of Returns: Kintamumo matavimas per informacinius barus.
Kodėl tai naudinga?
Kai modelis turi ne 37, o 100+ rodiklių, jis gali pastebėti labai subtilias koreliacijas. Pvz.:

„Jei Coinbase Premium yra teigiamas, bet Hyperliquid Orderbook rodo stiprų Bid-side imbalance ir Twitter sentimentas krenta – tai 85% atvejų yra lokalaus dugno požymis“.

Klausimas tau: Ar nori, kad pradėtume nuo Orderbook (L4) parametrų išgavimo, ar labiau orientuojamės į On-chain / Sentiment rodiklių plėtimą? L4 duomenys paprastai duoda tiksliausius signalus trumpuoju laikotarpiu.

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #