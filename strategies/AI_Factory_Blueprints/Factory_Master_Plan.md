# 🏭 Vieno Žmogaus AI Quant Gamykla: Master Planas

Kaip vienas žmogus, tu negali daryti visko vienu metu. Konteksto perjungimas (context switching) tarp duomenų valymo ir strategijos kūrimo tave išvargins. Sprendimas: **Tapk Gamyklos Vadovu (CEO/Portfolio Manager), o rutininius darbus deleguok AI.**

Šiame modelyje tu nebesi programuotojas. Tu esi **Architektas**. Tu duodi instrukcijas savo „AI darbuotojams“ pagal griežtus SOP (Standard Operating Procedures).

## 🏢 Gamyklos Struktūra (Tavo AI Komanda)

Suskirstyk savo projektą į 4 nepriklausomus „departamentus“. Niekada nedirbk dviejuose departamentuose tą pačią dieną.

### 1. Duomenų Inžinerijos Departamentas (Data Engineering)
*   **Tavo vaidmuo:** Nuspręsti, KOKIŲ duomenų reikia (pvz., Binance L2 orderbook, Polymarket sweeps).
*   **AI vaidmuo:** Parašyti kodą, kuris tuos duomenis surenka, išvalo, sujungia laiko žymes ir paverčia į **Dollar Bars**.
*   **Tavo AI Promptų stilius:** *„Aš turiu X duomenis CEX_Data aplanke. Parašyk skriptą, kuris pašalintų NaN reikšmes, sugrupuotų pagal minutę ir išsaugotų kaip Parquet. Nenaudok for-loops, naudok Pandas vektorizaciją.“*
*   **SOP failas:** `Factory_SOP_Data_Engineering.md`

### 2. Alfos Tyrimų Departamentas (Alpha Research / Feature Engineering)
*   **Tavo vaidmuo:** Sugalvoti hipotezę (pvz., *„Kai banginiai perka, o retail parduoda – kaina kyla po 5 min“*).
*   **AI vaidmuo:** Paversti šią hipotezę į matematinį kodą (Feature), pridėti jį prie duomenų bazės ir patikrinti koreliaciją.
*   **Tavo AI Promptų stilius:** *„Sukurk naują feature 'Whale_Retail_Divergence'. Tai bus rolling 15 min langas, kur (Whale_Buy_Vol - Retail_Buy_Vol) / Total_Vol. Paskaičiuok šio feature Feature Importance naudojant Random Forest.“*
*   **SOP failas:** `Factory_SOP_Alpha_Research.md`

### 3. Rizikos Valdymo Departamentas (Risk & Portfolio Management)
*   **Tavo vaidmuo:** Nustatyti maksimalaus nuostolio (Drawdown) ribas ir kapitalo priskyrimo strategiją.
*   **AI vaidmuo:** Sukurti **Meta-Labeling** modelius, nustatyti **Dynamic Bet Sizing** (Kelly Criterion), optimizuoti portfelį naudojant **Hierarchical Risk Parity (HRP)**.
*   **Tavo AI Promptų stilius:** *„Mano strategijos prediction yra X, o confidence yra Y. Parašyk Python klasę, kuri pagal Kelly formulę paskaičiuoja rekomenduojamą pozicijos dydį, neviršijant 2% kapitalo rizikos.“*
*   **SOP failas:** `Factory_SOP_Risk_Management.md`

### 4. Vykdymo Departamentas (Execution / Live Trading)
*   **Tavo vaidmuo:** Sukurti API raktus, stebėti serverio sveikatą, prižiūrėti botą.
*   **AI vaidmuo:** Parašyti greitą async kodą, kuris jungiasi prie biržos (Hyperliquid), siunčia pavedimus su mažiausiu latency ir valdo WebSockets.
*   **Tavo AI Promptų stilius:** *„Turiu sign_order() funkciją. Parašyk async wrapperį, kuris klausosi WebSocket 'trades' kanalo ir, gavęs signalą iš modelio, išsiunčia Market orderį. Įtrauk retry logiką, jei gavome HTTP 429 klaidą.“*

---

## 📅 Kaip atrodo tavo darbo savaitė?

*   **Pirmadienis (Data Day):** Dirbi TIK su duomenimis. Žiūri, ar nėra klaidų, prašai AI sukurti naujus parserius duomenų bazėms.
*   **Antradienis / Trečiadienis (Alpha Day):** Testuoji naujas idėjas. Prašai AI generuoti rodiklius (features) ir leidi backtestus.
*   **Ketvirtadienis (Risk Day):** Analizuoji backtestų klaidas. Prašai AI sukurti filtrus, kurie būtų tas klaidas išvengę (Meta-Labeling).
*   **Penktadienis (Code Review & Deploy):** Peržiūri AI parašytą kodą bendrai sistemai (Live Execution), pajungi viską ant popierinių pinigų (Paper Trading).
