# 🧠 Ateities Tyrimai: Causal Discovery (Priežastingumo nustatymas)

Šis dokumentas skirtas **Phase 3: Advanced Feature Selection** etapui. Tikslas – nustatyti, kurie iš mūsų 30 rodiklių yra tikrosios kainos judėjimo *priežastys*, o ne tik atsitiktinės koreliacijos.

---

## 🧐 Kodėl mums to reikia? (The „Correlation Trap“)
Dauguma ML modelių (kaip ir mūsų dabartinis) mato, kad du dalykai juda kartu, bet nežino, kuris kurį stumia.
*   **Pavyzdys:** Galbūt pastebėjome, kad kai perka pietų korėjiečiai (Kimchi Premium), kaina kyla. Bet ar tai *priežastis*, ar tiesiog abiejų įvykių pasekmė?
*   **PC (Peter-Clark) algoritmas** padeda nubraižyti „priežastingumo žemėlapį“ naudojant **Directed Acyclic Graphs (DAGs)**.

---

## 🛠️ PC Algoritmo Logika
1.  **Skeleton Discovery:** Pirmiausia surandamos visos stiprios sąsajos tarp rodiklių.
2.  **Independence Testing:** Algoritmas bando „izoliuoti“ rodiklius. Pavyzdžiui: „Jei mes žinome *Open Interest* reikšmę, ar mums dar reikia žinoti *Funding Rate*, kad nuspėtume kainą?“. 
    * Jei atsakymas NE – tai reiškia, kad *Funding Rate* yra tik tarpinis kintamasis, o ne tiesioginė priežastis.
3.  **V-structures:** Nustatomos strėlių kryptys (kas ką veikia).

---

## 🎯 Tikslas: Alfa Filtravimas
Panaudoję šį metodą, mes galėtume:
*   **Sumažinti triukšmą:** Išmesti rodiklius, kurie tik dubliuoja informaciją.
*   **Padidinti stabilumą:** Tikrosios priežastys (Causal factors) veikia ilgiau ir stabiliau nei laikinos koreliacijos.
*   **DSR gerinimas:** Mažiau rodiklių = mažiau bandymų (Trials) = aukštesnis **Deflated Sharpe Ratio**.

---

## 📋 Veiksmų planas (Ateičiai)
1. Įdiegti `causal-learn` arba `pcalg` Python bibliotekas.
2. Atlikti visų 30 rodiklių priežastingumo analizę 2020–2022 m. duomenyse.
3. Sukurti filtrą, kuris paliktų tik „šaknies“ priežastis prekybai.
