# 🏭 Gamyklos SOP: Alfos Tyrimai (Alpha Research & Feature Engineering)

**Tavo virtualus darbuotojas:** „Quant Researcher AI“
**Jo vienintelis tikslas:** Paversti idėjas matematikoje apskaičiuojamais indikatoriais (Features) ir sukurti ML modelius, griežtai vengiant duomenų nutekėjimo (Leakage) ir Overfittingo.

## 📋 Griežtos taisyklės AI asistentui
Kai kuri strategijas ir rodiklius, naudok šį taisyklės šabloną:

> "Act as a Lead Quantitative Researcher at a statistical arbitrage fund. 
> 1. We strictly follow Marcos Lopez de Prado's methodologies (Advances in Financial Machine Learning).
> 2. When creating features, strictly avoid Look-Ahead Bias. Any metric must only use data available AT OR BEFORE the timestamp.
> 3. For ML cross-validation, NEVER use standard K-Fold or Train-Test-Split. ALWAYS use Purged K-Fold Cross Validation.
> 4. We do not care about accuracy; we care about precision, recall, and feature importance.
> 5. When transforming price data, implement Fractional Differentiation rather than simple returns or Integer Differencing."

## 🧩 Dažniausi Užduočių Šablonai (Ką rašyti AI)

### 1 užduotis: Naujo indikatoriaus (Feature) kūrimas
*   **Idejos Aprašymas:** Tarkim, perskaitei straipsnį, kad didelis skirtumas tarp Perpetual Funding ir Spot kainos reiškia apsivertimą.
*   **Tavo Promptas:** *„Aš turiu DataFrame su stulpeliais `btc_funding_rate`, `btc_spot_price` ir `btc_perp_price`. Sukurk man tris naujus matematiškus feature'us, kurie matuotų šios anomalijos jėgą: 1) Momentinis Spreadas (Z-Score per paskutines 7 dienas). 2) Funding rate greitėjimas (Rate of Change per 3h). 3) Kumuliacinis likvidacijų tūris per tą patį langą. Grąžink švarią klasę `FeatureGenerator`, turinčią metodą `add_features(df)`.“*

### 2 užduotis: Modelio Treniravimas ir Feature Importance
*   **Tavo Promptas:** *„Turiu apvalytą DataFrame su 50 features ir Triple-Barrier labeliais (+1, -1, 0). Parašyk LightGBM klasifikavimo modelio pipeline. Integruok PurgedKFold su 1% embargo laiku. Modelyje naudok hiperparametrų paiešką (Optuna), optimizuojant 'F1-score'. Po treniravimo sugeneruok SHAP (SHapley Additive exPlanations) grafiką, kad pamatyčiau, kurie iš 50 features yra nereikalingas triukšmas. Išsaugok rezultatą į .html ataskaitą.“*

### 3 užduotis: Signalų Žymėjimas (Labeling)
*   **Tavo Promptas:** *„Dauguma naudoja fiksuotą Take Profit, bet rinka keičiasi. Parašyk Triple Barrier Method (TBM) funkciją, kuri dinamiškai nustato vertikalius (laikas - po 24h) ir horizontalius (TP/SL) barjerus. TP/SL barjerų plotis turi priklausyti nuo Exponentially Weighted Moving Daily Volatility. Funkcija turi grąžinti -1 (SL), 1 (TP) arba 0 (Time) kiekvienam barui ir išmesti tuos, kur rinka nepakankamai judri eiti į poziciją.“*

## 🛑 Kaip valdyti šį etapą
* Modeliai daromi be komisinių ar portfelio ribojimų – tik grynas, plikas pranašumas (Alpha). 
* Jei modelis vos veikia – atmesk jį greitai. Netvarkyk prasto modelio (Nepradėk optimizuoti *šlamšto*, nes priartėsi prie Overfitting'o). Geriau ieškok geresnių Features (Pirmam žingsnyje).
