# Pairs Trading Strategija 3: ML Meta-Labeling (M. Lopez de Prado Modelis)

Ši strategija apima **Institucinio lygio Machine Learning** integraciją į mūsų anksčiau aprašytas „Pairs Trading“ (Distance arba Cointegration) bazes, remiantis kvantinės finansų inžinerijos (pvz., **Marcos Lopez de Prado**) principais. Jos tikslas – maksimaliai išfiltruoti klaidingus signalus (False Positives) ir išspręsti atviros pozicijos rizikos valdymo problemas.

## 1. Neefektyvus duomenų diskretizavimas (Inefficient Sampling): „Dollar Bars“ vietoje Laiko Barų
Dauguma tyrėjų duomenis renka pagal „chronologinį laikrodį“ (fiksuoja kainas kas 15 min ar 1 val.).
**Problema:** Finansų rinkos informaciją gauna netolygiu greičiu. Imant laiko barus per vidurdienio ramybę sukuriami pertekliniai, beverčiai stebėjimai, atnešantys serijinę koreliaciją, pastovios variancijos trūkumą (heteroskedastiškumą) ir nenormalius skirstinius matematikoje.
- **Sprendimas (Dollar Bars):** Duomenys renkami (generuojamos žvakės) TIK tada, kai rinkoje apyvarta pasiekia tam tikrą piniginę sumą (pvz., kas 10 mln. dolerių).
- **Privalumas:** Kai į rinką ateina informuotas žaidėjas (banginis) ir pradeda agresyviai „mušti“ per Orderbook'ą, Dollar Bars sistema reaguoja greitai ir ten sugeneruoja daugybę žvakių – leisdama ML algoritmui „pasimokyti“ iš tikros banginio informacijos. Naktį išvengiama beprasmiško informacijos triukšmo. Be to, šis barų tipas yra daug atsparesnis už paprastus *Tick bars* prieš HFT (High-Frequency Trading) manipuliacijas.

## 2. Frakcinis diferencijavimas (Fractional Differentiation)
Tradicinė logaritmų grąža ištrina „atmintį“ apie tai, kokiam kainos lygyje (Aukštumose ar Dugne) mes esame.
- **Sluoksnio taikymas:** ML modeliui, kaip *Feature* (kintamasis), bus paduotas ne paprastas `log(price)`, o frakciškai diferencijuota kainos seka (išsauganti atmintį ir padinanti stacionarumą, d dažniausiai 0.2-0.5 intervale).

## 3. Dviejų Modelių Architektūra (Meta-Labeling)
Sistema priima sprendimus per du atskirus modelius:

### A) Pirminis Modelis (Primary Signal) – Bazinis Signalas
Tai mūsų esama Pairs Trading logika:
- Skaičiuojame porų tarpusavio ryšį (*Distance* arba *Cointegration* metodu).
- Generuojame signalą pagal *Z-Score* (kryptis). Galvojame kryptį: eiti Long spread ar Short spread, kai `|z_score| > 2.0`.
- Jis viską daro taip pat, kaip `strategija_1` ar `strategija_2`.

### B) Antrinis Modelis (Meta-Model) – AI Filtracijos (Meta-Labeling) sluoksnis
**Netinkamo duomenų žymėjimo (Wrong Labeling) Problema:** Dažnai kuriami modeliai bando nuspėti „Kokia bus kryptis po 10 dienų?“. Tai vadinama *Fiksuoto laiko horizonto klaida*, nes modelis nemato, kad per tas 10 dienų galėjo įvykti Flash Crash ir portfelis būtų buvęs likviduotas. Ignoruojama „kelio priklausomybė“ (*path dependency*).

**Sprendimas (Meta-Labeling):**
Ant pirminio (Signals) modelio uždedamas atskiras Machine Learning sluoksnis.
1. Jo užduotis **NE** spėlioti kainos kryptį, bet vertinti bazinio *Pairs Trading* algoritmo sprendimus ir spręsti pozicijos dydį (angl. *bet size*).
2. Įvykus pirminiam signalui, meta-modelis paima tūkstančius indikatorių (Funding rates, Orderbook imbalance, Macro signalus) ir Random Forest/XGBoost pagalba generuoja tikimybę (0-100%).
3. Taip padidinamas modelio tikslumas (precision) atsijojant tūkstančius blogų įėjimų (klaidingai teigiamų – false positives).

## 4. „Triple Barrier“ Metodas (Teisingas Pelnų fiksavimas ir Rizikos Valdymas)
Tęsiant apie teisingą mašininio mokymosi žymėjimą, privalome sukurti realistišką išėjimą (Exit) savo bandymuose. Modelis turi reaguoti į riziką iš karto, o ne aklai laukti x periodų.
Kiekvienam Pirminio modelio signalui nustatome 3 Virtualius Barjerus:
1. **Viršutinis horizontalus barjeras (Take Profit):** Pelno fiksavimo lygis.
2. **Apatinis horizontalus barjeras (Stop-Loss):** Nuostolio stabdymo lygis.
3. **Vertikalus barjeras (Time Limit):** Laiko apribojimas, kada pozicija uždaroma priverstinai, bet kokiu atveju (angl. *timeout*).

**Kaip veikia mokymas?**
Stebėjimas žymimas teigiamai (+1), jei pirmiausia pasiekiamas pelno barjeras, neigiamai (-1), jei patiriamas nuostolis, ir paženklinamas nuliu (0), jeigu niekas nepasiekiama ir galiausiai išgelbėjamas tik per vertikalų laiko (time) barjerą. Taip algoritmas išmoksta tikrojo *Path Dependency* – rizikos valdymo dinamikos.

## 5. Duomenų persidengimas ir Stebėjimų Unikalumas (IID problemos sprendimas)
Kuriant „Triple Barrier“ signalus, jie neišvengiamai priklausys nuo tų pačių praeities žvakių. Mašininio mokymosi algoritmai reikalauja, kad stebėjimai būtų nepriklausomi ir identiškai pasiskirstę (IID - Independent and Identically Distributed), antraip modelis per daug išmoks vieną specifišką laikotarpį.
- **Stebėjimų unikalumo kontrolė:** Matuojamas informacijos persidengimas tarp gretimų stebėjimų. Kryžminės patikros (Cross-Validation) metu mėginiai atrenkami atsižvelgiant į jų unikalumo svorį. Tai drastiškai geriau paruošia modelį „realaus pasaulio“ (Out-of-Sample) rezultatams.

## 6. Griežta Kryžminė Patikra (Cross-Validation su Purging ir Embargo)
Finansiniuose dumenyse išlieka serijinė koreliacija, todėl atsiranda „Duomenų nutekėjimas“ (Data Leakage) – algoritmas gali „pasufleruoti“ atsakymą iš ateities. Standartinės ML kryžminės patikros (pvz., Random K-Fold) čia tampa bevertės.
- **Purging (Valymas):** Iš mokymo (Training) rinkinio fiziškai ištrinami visi stebėjimai, kurių laikas bet kiek dalijasi informacija (persidengia) su testavimo (Testing) rinkinio duomenimis.
- **Embargo (Izoliacija):** Taikoma po testavimo rinkinio pabaigos pradedant mokymo rinkinį. Kadangi kainos pokyčiai palieka atgarsius, iš mokymo rinkinio iškerpamas papildomas laiko tarpas iškart po testavimo pabaigos (sudarant savotišką sieną). Taip užtikrinama, kad jokia nutekėjusi informacija nepasiektų mokymosi fazės. 

## 7. Modelio validacija: Deflated Sharpe Ratio (DSR) ir Klasterizacija
Jei mokslininkas ar treideris bandys 1000 skirtingų parametrų, remiantis grynaja statistika – vienas iš jų, dėl atsitiktinumo, parodys puikų rezultatą formuluojantį tradicinį *Sharpe Ratio*. Kad išvengti algoritmų pasitikėjimo vadinamuoju „Statistical Fluke“ (statistiniu atsitiktinumu), M. Lopez de Prado įveda *Defliuotą Sharpe rodiklį*.
1. **Atliktų bandymų (simuliacijų) skaičius ir klasterizacija:** Tarkim, atlikta 1000 testų, tačiau dėl parametrų koreliacijos realiai buvo testuojamos tik 4 iš esmės skirtingos idėjos. M. Lopez de Prado algoritmas sugrupuoja šiuos bandymus į klasterius ir suskaičiuoja TIKRĄJĮ **nepriklausomų bandymų (K) skaičių**.
2. **Deflated Sharpe Ratio (DSR):** Naudojant skaičiavimą iš (K), duomenų asimetriją (skewness), ekscesą (kurtosis) ir paties mėginio ilgį (sample length), apskaičiuojamas *Defliuotas* (nuvertintas) *Sharpe Ratio*. Jis drastiškai sumažina (deflate) backtesto sėkmę, įrodydamas tikrąją strategijos vertę ir atskirdamas laimę nuo solidaus ML modelio.

## Išvada ir Procesas
Ši 3-ioji strategijos versija naudoja *Distance* arba *Cointegration* logiką kaip „Aklą Dviratininką“, o Antrinį (Meta-Labeling) modelį – kaip intelektualų vertintoją, kuris sprendžia KADA važiuoti, KAIP smarkiai minti ir KADA geriau visai nevažiuoti. Tuo pačiu duomenų suveidimas per *Dollar Bars*, *Fractional Differentiation*, *Purging/Embargo* iteracijas bei unikalumo patikras sumažina False Positives kiekį, paverčiant ML sistemą – neatsitiktine, institucine pelno mašina priešingai nei akladarinėse „juodosiose dėžėse“.
