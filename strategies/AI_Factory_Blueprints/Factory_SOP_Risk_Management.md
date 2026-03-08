# 🏭 Gamyklos SOP: Rizikos Valdymas ir Portfelis (Risk & Portfolio)

**Tavo virtualus darbuotojas:** „Risk Manager AI“
**Jo vienintelis tikslas:** Apsaugoti tavo kapitalą ("Don't lose money") ir optimizuoti grąžos/rizikos santykį, kontroliuojant *kiek* investuojama į kiekvieną signalą.

## 📋 Griežtos taisyklės AI asistentui
Kai kuri rizikos ar kapitalo paskirstymo logikas, naudok šį prompto šabloną:

> "Act as a Quantitative Chief Risk Officer (CRO). 
> 1. We prioritize capital preservation over return generation. 
> 2. Implement Kelly Criterion (or fractional Kelly) for dynamic bet sizing based on the probability distribution of the ML classifier. Do not use strict 1-size-fits-all percentages.
> 3. Use Hierarchical Risk Parity (HRP) for portfolio allocation instead of standard Mean-Variance Optimization, to avoid instability from covariance matrix inversions.
> 4. We use Meta-Labeling for trade filtering. A secondary ML model must assess the probability of the primary model's success.
> 5. Incorporate dynamic volatility (e.g., ATR or VIX) to scale position sizes inversely to market turbulence."

## 🧩 Dažniausi Užduočių Šablonai (Ką rašyti AI)

### 1 užduotis: Kapitalo paskirstymas per HRP (Hierarchical Risk Parity)
*   **Tavo Promptas:** *„Turiu 10 kriptovaliutų valandinių grąžų DataFrame. Nenoriu naudoti paprasto '10% per coin' paskirstymo. Parašyk HRP (Hierarchical Risk Parity) kodą, kuris suklasterizuotų šias monetas pagal jų koreliacijas ir priskirtų portfolio svorius taip, kad panašiai judančios monetos nedvigubintų rizikos. Išvesk svorių pyragą (Pie Chart).“*

### 2 užduotis: Bet Sizing (Statymo dydis) pagal modelio pasitikėjimą
*   **Tavo Promptas:** *„Mano ML (Random Forest) modelis grąžina signalą (+1 arba -1) ir tikimybę (Probability/Confidence) nuo 0.50 iki 1.00. Parašyk bet-sizing klasę Python'e, kuri konvertuoja šią tikimybę į rekomenduojamą pozicijos dydį (nuo 0 iki 2% viso balanso). Jei tikimybė < 60%, grąžink 0$ dydį. Jei > 90%, grąžink maksimalų leistiną (2% kapitalo). Sukurk tam logaritmizuotą kreivę.“*

### 3 užduotis: Meta-Labeling Modelis
*   **Tavo Promptas:** *„Pirmas mano ML modelis turi +1400% grąžą backteste, bet stiprius Drawdown'us. Turiu CSV lentelę, kurioje įrašyti visi to modelio istoriniai treidai (1 laimėtas, 0 pralaimėtas), ir tų dienų rinkos sąlygos (VIX, Funding Rate, Volume). Sukurk **antrą**, RandomForest klasifikatorių, kuris mokytųsi nuspėti, MADA pirmasis modelis padarys klaidą. Grąžink kodą, kuris išspausdintų šio 'Sargo' Precision score.“*

## 🛑 Kaip valdyti šį etapą
* **Risk Manager** niekada negeneruoja signalų (Enter Long/Short).
* Šis departamentas stovi kaip „filtras“ tarp tavo turimo signalo ir biržos.
* Nepradėk šio etapo, kol tavo „Alpha Research“ neturi tvirto, valdyto modelio. AI turi testuoti tik kapitalo apsaugos metodus.
