# 🛡️ ML-Powered Risk Manager & Capital Allocation (Koncepcija)

Mašininis mokymasis (ML) rizikos valdymui yra net galingesnis nei signalų generavimui. Signalų modelis (kaip mūsų **ML Alpha v1**) nustato *kryptį* (perkam/parduodam). **Risk Manager** nustato *dydį* (kiek pinigų statom, arba ar išvis statom).

Štai geriausios ir profesionaliausios strategijos pagal **Marcos Lopez de Prado** mokyklą:

---

## 1. Meta-Labeling (Modelis, kuris prižiūri Modelį)
Tai yra pramonės standartas (Hedge Fund).
* **Problema:** Pirmas modelis sako LONG. Bet kaip mes žinome, kad tai nėra klaidingas signalas (False Positive)?
* **Sprendimas (Meta-Labeling):** Mes sukuriame **antrą ML modelį** (Risk Manager). 
  * Pirmojo modelio darbas yra tik pasakyti „LONG" arba „SHORT".
  * Antrojo modelio darbas yra patikrinti pirmojo rezultatus praeityje panašiomis sąlygomis ir pasakyti: **Kokia tikimybė, kad pirmas modelis dabar klysta?**
  * Jei Antras modelis sako: *„Rinkos likvidumas dabar nulinis, pirmas modelis anksčiau čia visada klysdavo“* -> Jis nustato pozicijos dydį (Position Size) lygų **0%** ir blokuoja sandorį.

## 2. Bet Sizing (Statymo Dydis pagal Pasitikėjimą ir Kelly)
Klasikiniai botai visada perka už fiksuotą % (pvz., 5% nuo sąskaitos). Tai klaida.
* **ML Sprendimas:** Mūsų signalas grąžina probabilities (pvz., 0.72).
* **Kaip naudoja Risk Manager:** Jis pritaiko ML pagrįstą *Kelly Criterion*. 
  * Jei modelis yra 90% užtikrintas: Risk Manager įdeda **10%** kapitalo.
  * Jei modelis yra 65% užtikrintas: Risk Manager įdeda tik **2%** kapitalo.
  * Taip maksimalizuojamas grąžos/rizikos santykis (Sharpe Ratio).

## 3. Hierarchical Risk Parity (HRP) - Kapitalo Paskirstymui Portfelyje
Jei ateityje prekiausi ne tik BTC, bet ir ALTS (ETH, SOL, DOGE ir t.t.), kaip paskirstysi $100,000 tarp jų?
* **Pavyzdys:** Padalinkim po lygiai: $50k BTC ir $50k ETH? Ne. Nes jei BTC krenta, ETH irgi kris – tu ne diversification (neskaidai rizikos).
* **ML Sprendimas (HRP):** HRP naudoja *Machine Learning Unsupervised Clustering* (Klasterizaciją). Modelis sugrupuoja panašiai judančias monetas į „šeimas“.
  * Tada Risk Manager apverstai proporcingai paskirsto kapitalą: tos monetos, kurios mažiausiai susijusios su kitomis, gauna daugiausiai svorio. Taip tavo portfolio tampa atsparus bendriems rinkos krachams.

## 4. Volatility-Adjusted ML Stops (Dinaminiai Barjerai)
Vietoje to, kad visada darytum 10% Stop Loss, Risk Manager naudoja ML, kad nuspėtų ateinančios valandos rinkos judrumą (Volatility Prediction).
* Jei rinka rami: SL daromas labai siauras (pvz., 2%). Pasiekiamas geresnis Risk/Reward.
* Jei rinka audringa (pvz., naujienų metas): Risk Manager **išplečia** SL iki 8%, bet **sumažina** pozicijos dydį 4 kartus. Taip apsaugomas tavo $ PnL nuo "išmušimo" dėl triukšmo.

---

## 🛠️ Kaip galėtume tai įgyvendinti praktiškai tavo sistemoje?
Turime jau veikiantį krypties modelį (`best_model.pkl`). Kitas logiškas žingsnis būtų sukurti `risk_manager.py` modulį, kuris:
1. Paima ML Alpha signalą ir jo Confidence score (pvz., 0.75).
2. Paleidžia pro **Bet Sizing matematinį filtrą**, kad nuspręstų kapitalo dalį nuo balanso (pvz., iš $10k balanso – skirti tik $500 šiam sandoriui).
3. Prieš atidarant orderį, visada paima Volatility (VIX ar ATR), kad dinamiškai parinktų, ar tai bus saugu, ir suformuluotų teisingą Leverage/Stop-Loss.
