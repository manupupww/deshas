# Žmogaus (Quanto) Atsakomybės Kuriant Institucinio Lygio ML Strategiją

Remiantis Marcos Lopez de Prado „Advances in Financial Machine Learning“ (AFML) principais, šios sistemos negalima palikti tiesiog aklo algoritmo savieigai. Automatinis prekybos bot'as (*Execution Bot*) sugeba tik paleisti iš anksto paruoštą strategiją realiu laiku, bet paties **modelio tyrimas, skaičiavimas, vertinimas ir parengimas** (tai, kas sukuria „Edge“ – pranašumą) yra išimtinai TAVO, kaip tyrėjo (Quant'o), rankose. 


---

## 🚫 7 Mirtinos ML Fondų Klaidos (Kurias mes naikiname)
Tavo darbas yra **neleisti** šioms klaidoms sugriauti mūsų kapitalo:
1. **Sizifo paradigma:** Tyrimų infrastruktūros trūkumas (Mes kuriame šį kodo pamatą).
2. **Sveikasis diferencijavimas:** Atminties praradimas dėl stacionarumo (Naudosime **Fractional Diff**).
3. **Neefektyvus samplingas:** Laiko žvakės (Naudojame **Dollar Bars**).
4. **Neteisingas žymėjimas:** Fiksuoti TP/SL (Naudojame **Triple-Barrier**).
5. **Ne-IID pavyzdžių svoriai:** Persidengiantys duomenys (Skaičiuosime **Uniqueness**).
6. **Kryžminės patikros nutekėjimas:** Standartinis K-Fold (Naudosime **Purged & Embargoed CPCV**).
7. **Backtest Overfitting:** Per daug bandymų (Skaičiuosime **Deflated Sharpe Ratio**).
8. **Statistinis silpnumas:** Tikime vienu „idealiu“ keliu (Naudojame **CPCV** paskirstymui).

---

## 1. Duomenų paruošimas tyrimui (Tavo darbas)
Paprastas bot'as maitinasi realaus laiko srautu (stream), bet tu turi paruošti istoriją tyrimams, kuri išmokys ML botą suprasti rinką.
- [ ] **Sukurti „Dollar Bars“:** Tu pats imi istorinius *Tick* ar sekundių *Volume* duomenis ir transformuoji juos į „Dollar Bars“ rinkinį tyrimams. Tu testuoji, koks apimties slenkstis (pvz. 1 mln. USD) geriausiai atspindi informacijos srautą tavo monetoje.
- [ ] **Frakcinis diferencijavimas:** Tu analizuoji kainų eilutes ir ieškai idealaus $d$ koeficiento (tarp 0-1, pvz., 0.35). Tikrini, kada ADF testas patvirtina stacionarumą (p-value < 0.05), o atmintis lieka maksimali. Atlikęs testus – užfiksuoji gautą geriausią $d$, kurį naudosi perleisdamas visas kitas features.
- [ ] **Pažangūs Kvantiniai Indikatoriai (AFML Features):**
    - **Mikrostruktūros Indikatoriai:** Gili Orderbook'o analizė – pvz., VPIN (Volume-Synchronized Probability of Informed Trading) arba Corwin-Schultz spread estimator skaičiavimas, norint išspausti signalą iš pačios rinkos mechanikos.
    - **Entropijos Indikatoriai:** Kainų eilučių informacijos kiekio matavimas (pvz., Lempel-Ziv entropija), siekiant suprasti ar judėjimas yra atsitiktinis triukšmas, ar turi prognozuojamą dėsningumą.
    - **Struktūriniai Lūžiai (Structural Breaks):** Matematinių testų (Chow-Type Dickey-Fuller) taikymas automatiškai nustatyti rinkos režimo pasikeitimus (iš Bull į Bear), dar prieš tai tampant vizualiai akivaizdu.
- [ ] **Indikatorių agregavimas:** Tu surenki visus savo „features“ (Makro duomenis, Funding rates, VPIN, Entropy iš *Base/Master Collector*) ir prijungi juos prie savo vizualiai matomų, teisingų Dollar Bar’ų išsaugotų .csv ar .parquet failų.

## 2. Pirminės strategijos modeliavimas (Atidarymai)
- [ ] **Distance / Cointegration parametrų optimizavimas:** Tu analizuoji, kuri atrankos (Formation) ir prekybos (Trading) slenkamųjų langų dinamika veikia geriausiai tavo atrinktoje 20+ monetų visatoje.
- [ ] **Generuoti Pirminį (Primary) modelį:** Tu skaičiuoji *Z-score* generuodamas išgrynintus hipotetinius (popierinius) įėjimo signalus visam duomenų masyvui. Šiuos signalų ataskaitos taškus (metaduomenis) išsaugai sekančiam ML testavimui.

## 3. Triple-Barrier ir Taikinių Žymėjimas (Labeling)
Tai griežtai analitinis tavo žingsnis. Treidingo bot tiesiog lauks TP/SL pabaigos, bet tu dabar rengi algoritmui „Atsakymų Lapą“.
- [ ] **Barjerų plotis:** Remiantis dienos/savaitės monetos kintamumu (volatility), tu nustatai viršutinio (Take Profit) ir apatinio (Stop Loss) barjero plotį (pvz., +1% viršun, -2% apačion nuo pirkimo kainos).
- [ ] **Triple Barrier simuliacija istorijoje:** Tu praleidi kiekvieną sugeneruotą Atidarymo signalą per laiko eilių istoriją ir užžymi, kurį barjerą kaina palietė pirmiau: `1` jeigu Pelną, `-1` jeigu Nuostolį, `0` jeigu pasibaigė Laikas (Timeout). **Šis stulpelis (Labels) tampa tavo Machine Learning pamatais.**

## 4. Machine Learning modelio mokymas ir (kryžminė) patikra
Štai kur tu praleidi daugiausiai laiko. Modelis tiesiog nuskaito Python failą, kurį tu sukursi. Šiame žingsnyje tavo didžiausias priešas yra **Duomenų nutekėjimas (Data Leakage)** — būtent tai dažniausiai lemia „Backtesto“ iliuziją, kai simuliacijoje laimima, o live prekyboje viskas žlunga dėl serijinės koreliacijos iš ateities.
- [ ] **Kovojimas su duomenų nutekėjimu („Purging“):** Realiame gyvenime, mokant ML modelį, tu rašai kodą, kuris identifikuoja ir TIESIOGIAI IŠTRINA iš mokymo rinkinio visokius stebėjimus, kurie nors menkiausia dalele persidengia su testavimo rinkiniu (overlapping labels).
- [ ] **Aklosios zonos sukūrimas („Embargo“):** Tu užprogramuoji izoliacijos langą tuose atvejuose, kai testavimo duomenys chronologiškai eina iškart PRIES mokymo duomenis. Taip užtikrini, kad finansinė „atmintis“ nespėtų persiduoti į tavo ML treniruotes. Geras „Purging“ ir „Embargo“ kodas atsispindi tuo, jog po jo pritaikymo Sharpe Ratio drastiškai sumažės ir stabilizuosis.
- [ ] **Svorio ir Unikalumo matavimas:** Atpažinus sutampančias žvakes persidengiančiame „Triple Barrier“ procese, tu paskaičiuoji stebėjimų unikalumą ir persveri kiekvieno pavyzdžio svorį algoritme.
- [ ] **Hiperparametrų Optimizavimas su Kryžmine Patikra:** Standartinis `GridSearch` priverčia modelį „persimokyti“ (overfit). Tu skiri laiką ir rašai specifinį *Purged* parametrų paieškos algoritmą (pvz. naudojant CPCV), kad atrastum teisingus medžio gylius ir mokymosi greičius be ateities duomenų nutekėjimo.
- [ ] **Kombinatorinė išvalyta kryžminė patikra (CPCV):** Vietoj vieno statiško testavimo kelio, tu naudoji **CPCV**. Šis metodas sugeneruoja tūkstančius galimų strategijos kelių, todėl modeliui tampa neįmanoma „atsitiktinai“ prisitaikyti. Tu analizuoji ne vieną Sharpe skaičių, o visą jų pasiskirstymą (medianą, asimetriją).
- [ ] **Ansamblio metodai (Bagging ir Boosting):** Tu naudoji **Random Forest** ir **XGBoost** ne kaip paprastus algoritmus, o kaip „nemokamus pietus“ (Free Lunch). Apjungdamas daug medžių prognozių, tu drastiškai sumažini modelio variaciją ir padidini jos robastiškumą.
- [ ] **Meta-Labeling (Korekcinis AI):** Iš gautų `1, 0, -1` žymių tu paverti jas binarinėmis `1` ir `0`. Tai – antras modelio sluoksnis, kuris nuspėja, ar pirminis modelis padarys klaidą. Jis ypač svarbus **Bet Sizingui** (pozicijos dydžio parinkimui) – investuok daugiau tada, kai Meta-Modelis rodo aukštą sėkmės tikimybę.
- [ ] **Feature Importance analizė:** Paleidęs Random Forest/XGBoost, tu tirsi *SHAP Values* ar Features grafiką. Tavo užduotis: pamatyti ar logine prasme indikatoriai, lemiantys „Winnerius“, turi realų ekonominį svorį (pvz., Orderbook imbalance) ar tėra atsitiktinis triukšmas.

## 5. Modelio Vertinimas: ArTaiTikraiVeikia, ArTaiTik„Backtest Overfitting“?
Dažniausia, **didžiausia ir pati svarbiausia klaida kvantinėje finansų inžinerijoje („Backtest Overfitting“)** – nutylimas atliktų tyrimų skaičius (Data Torturing / Duomenų kankinimas). Kadangi praleidus milijoną atsitiktinių testų vienas natūraliai parodys tobulą Sharp Ratio = 5.
- [ ] **Bandymų registracija ir Klasterizacija (K):** Pradedant nuo Pirmos dienos, tu turi fiksuoti KIEK KARTŲ testavai skirtingus parametrus. Sukauptus tūkstančius bandymų tu sugrupuoji į klasterius (nes kai kurie labai panašūs vienas į kitą) ir apskaičiuoji *tikrąjį, nepriklausomų bandymų (K)* skaičių.
- [ ] **Deflated Sharpe Ratio (DSR) skaičiavimas:** Naudojant (K) skaičių, rezultatų asimetriją (skewness), ekscesą ir duomenų imtį, tu apskaičiuoji Defliuotą Sharpe rodiklį. Ši lygtis „nukenkina“ rezultatą nubaudžiant jį už tavo kantrybę bandant milijonus iteracijų. Jeigu Deflated Sharpe Ratio patvirtina, kad išradimas nėra iliuzija/atsitiktinumas — tik tuomet strategija tinkama.
- [ ] **Backtestinimas su Sintetiniais Duomenimis:** Prieš pasitikėdamas strategija, tu privalai ją išbandyti ne tik su istorija, bet ir su tavo sukurtais sintetiniais duomenimis (pvz., Monte Carlo / stochastiniais procesais). Tu tikrini, ar modelis išgyventų visiškai neregėtas rinkos sąlygas.

## 6. Portfelio Valdymas ir Paskirstymas (ML Asset Allocation)
Jeigu tavo strategija prekiauja keliais aktyvais (pvz., Top 30 kriptovaliutų), portfelio svorių parinkimas pagal „Markowitzą“ (MPT) yra atgyvenęs praeities reliktas.
- [ ] **Hierarchical Risk Parity (HRP) taikymas:** Naudodamas mašininį mokymąsi ir klasterizavimo metodus, tu išskaidai monetas į grafų medžius ir perskirstai joms kapitalą taip, kad portfelis taptų maksimaliai atsparus šokams. Tu suformuoji stabilų krepšelį, kurio nekankina koreliacinių matricų nestabilumas.

## 7. Sprendimas: Eksportas Treidingo Botui
Tik kai praeini visus šiuos 6 punktus, strategija patenka į produkciją...
- [ ] Tu perrašai (išsaugai) paruoštus modelių svorius (pvz. iš `XGBoost` *.pkl* / *.onnx* formatu).
- [ ] Tu įsakai realiam, automatiniam „Execution Botui“ (Trading Bot) tiesiog gyvai imti naujausius rinkos duomenis iš CEX/HL, konvertuoti juos į šviežią „Dollar Bar“, ir nusiųsti meta-modeliui nuspėti P-Probability. Tokiu būdu live botas atlieka TIK greitą svorių skaitymą (Inference), o ne intelektualų ML darbą.
