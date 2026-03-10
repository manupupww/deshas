# Pairs Trading Strategija 1: Distance Method

Ši strategija paremta **Fil & Kristoufek (2020 IEEE Access)** tyrimu „Pairs Trading in Cryptocurrency Markets“. Tai yra **Distance Method** (atstumų / mažiausių kvadratų metodas), kuris tyrimo metu parodė ypač gerus rezultatus trumpesniuose laiko intervaluose (pvz., +11.61% per mėnesį 5 min intervale). Šis metodas yra paprastesnis skaičiavimo prasme, bet itin efektyvus kriptovaliutų rinkoje.

## 1. Duomenų parametrai
- **Šaltinis:** Binance Spot / Futures (OHLCV duomenys).
- **Numeraire (bazinė valiuta):** BTC. Visos poros sudaromos su BTC (pvz., ETH/BTC, SOL/BTC, BNB/BTC).
- **Visata (Universe):** Top likvidžiausios monetos (pvz., Top 20-30 pagal prekybos apimtį).
- **Timeframe (Laiko intervalas):** 15 minučių (15m). Pradžiai testuojama su 6–12 mėnesių istoriniais duomenimis.

## 2. Periodo skaidymas (Sliding Window)
Strategija naudoja slenkantį langą (Sliding Window), padalintą į dvi dalis:
1. **Formation period (Atrankos periodas):** skirtas porų atrankai ir parametrų skaičiavimui. Pvz., 1-6 mėn.
2. **Trading period (Prekybos periodas):** periodas, kurio metu generuojami signalai ir vykdoma prekyba atrinktomis poromis. Pvz., 1-3 mėnesiai.
Pasibaigus Trading periodui, langas paslenkamas (pvz., per 1 savaitę ar 1 mėnesį) ir procesas kartojamas.

## 3. Porų atrinkimas (Formation Periode)
Poros atrenkamos tik atrankos periodo metu:
1. Paimamos visų atrinktų monetų **logaritminės kainos** (`log(price)`).
2. Kainos **normalizuojamos** (z-score principu atrankos periode):
   `norm_price = (log(price) - mean(log(price))) / std(log(price))`
3. Visoms galimoms altcoinų ir BTC poroms skaičiuojamas **SSD** (Sum of Squared Deviations – kvadratinių nuokrypių suma):
   `SSD = ∑ (norm_price_alt - norm_price_BTC)²`
4. **Filtravimas:** Atrenkama **Top 20 porų**, turinčių mažiausią SSD reikšmę. Tai reiškia, kad šios monetos juda labiausiai sinchroniškai.

## 4. Spread'o skaičiavimas (Trading Periode)
Kiekvienai atrinktai porai skaičiuojamas skirtumas (Spread) realiu laiku:
`spread = norm_price_alt - norm_price_BTC`
*(Pastaba: kainoms normalizuoti prekybos periode naudojami atrankos periodo vidurkiai ir standartiniai nuokrypiai, arba slenkantis vidurkis/nuokrypis).*

## 5. Signalų generavimas (Z-Score)
Paskaičiuojamas Spread'o Z-score, kad nustatytume, ar kainos išsiskyrė pakankamai toli:
`z_score = (spread - rolling_mean(spread)) / rolling_std(spread)`
*(Naudojamas atrankos periodo mean/std arba slenkantis langas).*

## 6. Prekybos taisyklės (Entry & Exit)
- **Short Spread (Entry):**
  Jei `z_score > +2.0` 👉 **Short Spread**. 
  *(Parduodame/Short altcoiną, Perkam/Long BTC).*
- **Long Spread (Entry):**
  Jei `z_score < -2.0` 👉 **Long Spread**.
  *(Perkam/Long altcoiną, Parduodam/Short BTC).*
- **Uždarymas (Exit):**
  Pozicija uždaroma, kai `z_score` grįžta prie `0` (arba arti `0.5`, jei norima užfiksuoti pelną anksčiau).
  Taip pat pozicijos priverstinai uždaromos pasibaigus Trading periodui.
- **Stop-Loss:** Tyrimo autoriai nurodo, kad stop-loss kenkia rezultatams, todėl klasikinio stop-loss nėra. Kaip saugiklis gali būti nustatomas labai platus SL (pvz., `z=4.0` arba `5.0`).
- **Position Sizing:** Kiekvienos poros „kojos“ (altcoin ir BTC) apimtis doleriais turi būti lygi (Dollar-neutral).

## 7. Rizikos ir vykdymo valdymas
- **Execution Lag (Vykdymo vėlavimas):** Skaičiuojant backtestus būtina įtraukti 1 periodo (15 min) vykdymo uždelsimą nustačius signalą. Tai imituoja „slippage“ ir bid/ask spread'ą, apsaugodama nuo nerealaus pelno.
- **Transaction Costs (Mokesčiai):** Į backtestą būtina įtraukti `0.15%` round-trip mokestį (arba Binance Spot mokesčių standartą), nes strategija itin jautri komisiniams ir gali prarasti pelningumą, jei base mokesčiai yra >0.2%.
- **Drawdown:** Maksimalus istoriškai stebėtas daily drawdown yra iki 26%, todėl portfelio dydžio valdymas ir limitavimas iki max 20 aktyvių porų vienu metu yra kritiškai svarbus.
