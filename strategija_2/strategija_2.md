# Pairs Trading Strategija 2: Cointegration Method

Ši strategija paremta **Fil & Kristoufek (2020 IEEE Access)** tyrimu „Pairs Trading in Cryptocurrency Markets“. Tai yra **Cointegration Method** (kointegravimo metodas, naudojant Engle-Granger testą). Nors šis metodas gali sugeneruoti kiek mažesnę grąžą trupuoju laikotarpiu lyginant su Distance metodu, jis istoriškai išsiskiria **gerokai didesniu stabilumu ir nuoseklumu** ilgalaikėje perspektyvoje (geriausiai veikia net ir Daily intervaluose, kur fiksavo +1.36% per mėnesį).

## 1. Duomenų parametrai
- **Šaltinis:** Binance Spot / Futures (OHLCV duomenys).
- **Numeraire (bazinė valiuta):** BTC. Visos poros sudaromos su BTC (pvz., ETH/BTC, SOL/BTC).
- **Visata (Universe):** Top likvidžiausios monetos. 
- **Timeframe (Laiko intervalas):** 15 minučių (15m). Backtestui pradedama nuo 6–12 mėnesių istoriniais duomenimis.

## 2. Periodo skaidymas (Sliding Window)
Strategija naudoja slenkantį langą (Sliding Window), padalinto į dvi dalis:
1. **Formation period (Atrankos periodas):** Laikotarpis statistinio kointegravimo ryšiui rasti. (Pvz. 1-6 mėnesiai).
2. **Trading period (Prekybos periodas):** Laikotarpis sugeneruoti signalams iš stabilių porų. (Pvz. 1-3 mėnesiai).
Lango poslinkis daromas periodiškai (kas savaitę ar mėnesį).

## 3. Porų atrinkimas (Formation Periode)
Poros atrenkamos ieškant statistiškai patvirtinto grįžimo prie vidurkio (stacionarumo):
1. Paimamos visų monetų logaritminės kainos (`log(price)`).
2. Kiekvienai įmanomai porai (Altcoin vs BTC) taikoma **tiesinė regresija (OLS)**:
   `log(price_alt) = α + β × log(price_BTC) + ε`
   Kur `α` yra konstanta, `β` – apsidraudimo koeficientas (hedge ratio), `ε` – liekanos (residuals / spread).
3. Atliekamas **Engle-Granger testas** (dažniausiai Augmented Dickey-Fuller testas ant liekanų serijos `ε`).
4. **Filtravimas:** Tikrinama p-reikšmė. Atrenkamos tik tos poros, kurių liekanos (`ε`) yra **stacionarios** statistiniu lygmeniu (p-value < 0.05). Jei tokių porų labai daug – pasirenkamos Top 20 porų su pačia mažiausia p-reikšme ir aukščiausiu t-statistiku.

## 4. Spread'o skaičiavimas (Trading Periode)
Spread'as realiuoju laiku (Trading periode) yra skaičiuojamas remiantis regresijos formule ir koeficientais gautais atrankos metu:
`spread = ε = log(price_alt) - (α + β × log(price_BTC))`

## 5. Signalų generavimas (Z-Score)
Paskaičiuojamas normalizuotas nuokrypis (Z-score) spread'ui (liekanoms):
`z_score = (spread - mean(spread)) / std(spread)`
* Vidurkis ir standartinis nuokrypis imami iš formation periodo, arba skaičiuojamas slenkantis (rolling) vidurkis ir nuokrypis.*

## 6. Prekybos taisyklės (Entry & Exit)
- **Short Spread (Entry):**
  Jei `z_score > +2.0` 👉 **Short Spread**. 
  Parduodamas (Short) pervertintas aktyvas ir perkamas (Long) nepakankamai įvertintas aktyvas, atsižvelgiant į `β` koeficientą.
- **Long Spread (Entry):**
  Jei `z_score < -2.0` 👉 **Long Spread**.
  Perkamas (Long) per stipriai nukritęs aktyvas ir Parduodamas (Short) atitinkamas proporcingas brangesnis aktyvas.
- **Position Sizing (Hedge Ratio):** Prekybos dydis paskirstomas ne santykiu 1:1 doleriais, o remiantis `β` koeficientu (iš regresijos). Pavyzdžiui, 1 vienetui altcoino yra perkama/parduodama `β` vienetų bazinės valiutos (numeraire).
- **Uždarymas (Exit):**
  Pozicija uždaroma, kai `z_score` kerta vidurkių liniją: `0`.
  Kartais logiška taikyti greitesnį uždarymo filtrą, pvz., `|z_score| < 0.5`. Taip pat atliekamas priverstinis uždarymas (Forced Close) trading periodui pasibaigus.
- **Stop-Loss:** Autorių pastebėjimu, klasikinis stop-loss tik gadina performance. Galima naudoti kritinį lygį kaputuliavimui, pvz., `z=4.0 - 5.0`.

## 7. Rizikos ir vykdymo valdymas
- **Execution Lag (Vykdymo vėlavimas):** Integruojamas 1 periodo (15 min) uždelsimas vykdant pavedimus modeliuojant slippage ir order-book likvidumo problematiką. Jeigu vėlavimas pasiekia daugiau nei kelis periodus, strategijos metinis pajamingumas smarkiai krenta žemyn.
- **Transaction Costs:** Iteruojama su `0.15%` mokesčiais. Jeigu mokesčiai viršija gautą regresijos vidutinį nuokrypį (mean-reversion amplitude), sandoris praleidžiamas arba keičiama birža/paskyra į VIP mokesčių struktūrą.
- **Tvarumas:** Nepavykus surasti kointegruotų porų jokiame lange, prekyba to periodo metu nevykdoma, o kapitalas lieka nerizikingoje pozicijoje (cash).
