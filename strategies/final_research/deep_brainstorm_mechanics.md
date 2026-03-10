# Deep Market Mechanics Brainstorm: Solving Inefficiency

Šis dokumentas yra skirtas giliųjų rinkos mechanizmų analizei, fokusuojantis į tai, kaip atpažinti tikrąjį trendą ir nepasiduoti manipuliacijoms.

## 1. Struktūrinis Konfliktas: BOS vs. Liquidity Grab
**Problema:** Kaip botui suprasti, ar kainos kirtimas per aukščiausią tašką yra trendo tęsinys (BOS), ar spąstai (Liquidity Grab)?

*   **BOS (Break of Structure) Parašas:**
    *   Žvakė užsidaro **aukščiau** lygio (High).
    *   Kūno ir viso ilgio santykis (Body/Range) > 0.7.
    *   Tūris didelis, bet likvidavimai maži (sveikas judesys).
*   **Liquidity Grab (The Wick) Parašas:**
    *   Kaina kerta lygį, bet grįžta palikdama ilgą dagtį.
    *   Ekstremalus **Short likvidavimų** šuolis.
    *   **Strateginė įžvalga:** Po pirmo wick'o dažnai seka retestas, kuris yra lengvas pelnas, nes rinka "išvalo" naujus šortintojus.

## 2. Inercijos analizė: FVG (Fair Value Gap) vaidmuo
**Idėja:** FVG nėra tiesiog tuščia vieta, tai yra **institucinio impulso įrodymas**.

*   **Kaip naudoti:** Jei po likvidavimo šuolio atsiranda FVG, tai patvirtina, kad atšokimas yra tikras.
*   **Magneto efektas:** Botas turi suprasti, kad kaina gali grįžti užpildyti FVG (retest), ir tai nėra signalas bėgti, o signalas laukti "antros bangos".

## 3. Likvidavimo Bangos (The Wave Theory)
**Problema:** Per ankstyvas išėjimas per pirmąjį likvidavimo piką.

*   **Hipotezė:** Tikrasis trendo apsisukimas įvyksta ne po pirmos, o po **antros ar trečios** likvidavimo bangos.
*   **Logika:** 
    1. Banga 1: Pirminis panikos/stopų išmušimas.
    2. Retestas: Naujų žaidėjų pritraukimas.
    3. Banga 2/3: Galutinis išgryninimas (Climax).
*   **Užduotis:** Sukurti "Counter", kuris skaičiuotų likvidavimo pikus ir neleistų išeiti, kol "kuras" (likvidumai) dar nepasibaigė.

## 4. Absorbcija: Kai kaina "atsitrenkia į sieną"
**Scenarijus:** Kaina kyla, bet Volume yra nenormaliai didelis, o žvakės progresas mažas.

*   **Indikacija:** Čia stovi didelis pardavėjas (Iceberg). 
*   **Sprendimas:** Jei matome Volume augimą be kainos augimo – tai yra tikrasis "Exit" ženklas, daug stipresnis už paprastą raudoną žvakę.

## 5. Fakeout identifikavimo matrica
| Požymis | Tikras Breakout | Fakeout (Spąstai) |
| :--- | :--- | :--- |
| **Volume** | Aukštas ir stabilus | Labai aukštas (spike) arba žemas |
| **Liquidations** | Vidutiniai | Ekstremalūs (Stop Hunt) |
| **Candle Body** | Didelis (Full Body) | Mažas su ilgu Wick |
| **Follow-through** | Sekanti žvakė tęsia kryptį | Sekanti žvakė grįžta į pradinę zoną |

---
**Tikslas:** Sujungti šiuos punktus į vieną "Structural Engine", kuris veiktų be jokių standartinių indikatorių.
