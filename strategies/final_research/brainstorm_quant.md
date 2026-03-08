# Quantitative Alpha Brainstorm: BTC 15min Structural Trading

Šiame dokumente apibendrintos institucinio lygio įžvalgos ir strateginiai modeliai, sukurti bendradarbiaujant su AI („DeepMind“ filosofija).

## 1. Problema: Mažmeninis Triukšmas (Retail Noise)
*   **Indikatorių vėlavimas:** EMA, RSI, MACD yra išvestiniai duomenys. Jie parodo, kas *jau įvyko*, bet ne tai, *kodėl* tai įvyko.
*   **Mokesčių spąstai:** Prekiaujant ant 1 min ar 5 min grafikų, komisiniai (net ir 0.04%) sunaikina pranašumą (Edge), jei laimėjimo procentas nėra >60%.
*   **Fakeouts:** Rinka yra sukurta apgauti paprastus algoritmus, kurie reaguoja į vieną raudoną žvakę ar EMA susikirtimą.

## 2. Rinkos Fizika: Tikrasis Alpha (Signal)
Užuot naudoję indikatorius, mes fokusuojamės į **rinkos mechaniką**:
*   **Likvidavimai (Liquidations):** Tai yra kuras. Dideli likvidavimai sukuria neefektyvumą (Inefficiency), nes kaina nuvaroma žemiau/aukščiau tikrosios vertės dėl priverstinių pardavimų.
*   **Tūrio energija (Volume):** Parodo, ar judesys turi institucinį patvirtinimą.
*   **Kainos geometrija (Path):** 10-ties žvakių seka parodo "pėdsaką". Unikalūs keliai yra triukšmas, pasikartojantys keliai yra struktūra.

## 3. "Stop Hunt Arbitrage" Modelis
Tai modelis, kuris tyko manipuliacijų:
1.  **Squeeze:** Rinka rami, volatilumas žemas.
2.  **The Spike:** Staigus likvidavimo šuolis (Long likvidavimai prieš kilimą).
3.  **Anti-Fakeout Confirm:** Laukiam stiprios priešingos žvakės su tūriu, kuris viršija vidurkį.
4.  **The Trade:** Perkam, kai visi kiti yra išmesti iš rinkos.

## 4. Išėjimo Logika (The Exit Brainstorm)
Vienas sudėtingiausių momentų – kaip išeiti, kad neprarastume pelno, bet ir neleistume pullbacks mus išmesti per anksti.

### A. Smart Exit (65% Win Rate)
*   Išeiti vos pamačius pirmą silpnumo ženklą (priešinga žvakė), jei pelnas jau yra >0.5%.
*   *Pliusas:* Aukštas tikslumas.
*   *Minusas:* Nepagauna didelių (+5%+) judesių.

### B. Pullback Tolerance (Trend Following)
*   Išeiti tik tada, kai kaina "išlaužia" struktūrą (pvz., nukrenta žemiau paskutinių 3 žvakių Low).
*   *Pliusas:* Leidžia laimėtojams laimėti maksimaliai.
*   *Minusas:* Atiduoda dalį pelno atgal per apsisukimą.

### C. Liquidity Wave Climax (Vartotojo idėja) 🚀
*   **Wick Theory:** Didelis wick'as viršūnėje nėra išėjimo signalas. Tai tik pirmas likvidumo surinkimas.
*   **Retest Logic:** Po wick'o kaina dažnai grįžta (retest), suformuoja naujus Short'us ir tada juos "išspaudžia" (Squeeze) dar aukščiau.
*   **Exit Signal:** Išeiti tik po **antros ar trečios** likvidavimo bangos, kai kuras (short'ų stopai) visiškai baigiasi.

## 5. Pažangios Struktūros (BOS & FVG)
*   **BOS (Break of Structure):** Atpažinti tikrą struktūros lūžį (daug "kūno", mažai wick'o).
*   **FVG (Fair Value Gap):** Naudoti kaip impulsų patvirtinimą. Jei judesys palieka FVG, vadinasi, jis yra tikras ir mes turime likti sandoryje.

## 6. Machine Learning Filosofija
*   **Random Forest > LSTM:** Finansų rinkose stabilumas ir rinkos būsenos (State) supratimas yra svarbiau nei sekos prognozavimas. 
*   **Features:** Svarbiausi požymiai modeliui yra likvidavimų Z-Score, Vol_Liq_Ratio ir Path Geometry.

---
*Dokumentas paruoštas tolimesniam algoritmų kūrimui.*
