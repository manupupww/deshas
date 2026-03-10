# Professional Risk Manager Features (ML Meta-Model)

Šiame sąraše pateikiami svarbiausi kintamieji, kurie padeda Meta-Modeliui nuspręsti, ar leisti pagrindinei strategijai prekiauti.

## 1. Globali Makro aplinka & FED (The "World" Context)
Šie rodikliai parodo, ar pasaulis yra saugus investuoti į rizikingą turtą (crypto).
*   **DXY (US Dollar Index)**: Pagrindinis crypto priešininkas. DXY kyla = Crypto krenta.
*   **FED (Federal Reserve) Interest Rates**: JAV centrinio banko palūkanų normos. 
    - **Aukštos palūkanos** = Pinigai brangūs, investuotojai traukiasi iš crypto.
    - **Palūkanų mažinimas** = Pinigų "spausdinimas", crypto kyla.
*   **FOMC Meetings**: FED susirinkimų datos. Šiomis dienomis volitiliškumas būna didžiausias.
*   **Nasdaq / S&P 500**: Technologijų akcijų judėjimas. BTC korelacija su "Tech" yra milžiniška.
*   **VIX (Volatility Index)**: Akcijų rinkos baimės indeksas. VIX > 30 reiškia globalų de-riskingą.
*   **Gold (XAU/USD)**: "Saugus prieglobstis". Jei auksas brangsta, o BTC krenta – rinka bijo katastrofos.

## 2. Crypto Išvestinės & Svertas (The "Engine")
BTC kaina juda ten, kur juda svertas (leverage).
*   **Open Interest (OI)**: Kiek iš viso yra atidarytų pozicijų. Didelis OI = pasiruošimas "squeezui".
*   **Funding Rates**: Kiek "Long" moka "Short" pozicijoms. Teigiamas Funding = rinka perka per agresyviai.
*   **Liquidations Delta**: Skirtumas tarp Long ir Short likvidacijų reikšmės (Squeeze indikatorius).
*   **Miner Outflow**: Ar kasėjai pradėjo masiškai pardavinėti savo BTC?
*   **BTC/ETH ETF Flows (Institutional)**: IBIT, FBTC ir kitų fondų pirkimo/pardavimo srautai. Tai „protingi pinigai“ (Smart Money).
*   **OI-to-Volume Ratio**: Ar judėjimą sukelia spekuliantai (aukštas OI), ar realus atsiskaitymas?

## 3. On-Chain & Pinigų srautai (Exchange Netflow)
Tai leidžia matyti, ar pinigai „įeina“ į biržas (pasiruošimas parduoti), ar „išeina“ (pasiruošimas laikyti/HODL).
*   **BTC/ETH Inflow (Įplaukos)**: Kai banginiai perveda BTC į biržas – tai ženklas, kad jie ruošiasi parduoti. Tai didina riziką.
*   **Stablecoin Inflow Velocity**: Kai USDT/USDC plūsta į biržas – tai „šoviniai“ pirkimui. Tai rodo, kad rinka ruošiasi kilimui.
*   **Exchange Netflow (Grynasis srautas)**: Skirtumas tarp Įplaukų ir Išplaukų.
    - **Teigiamas Netflow** (Inflow > Outflow) = Lokalus pavojus (Selling Pressure).
    - **Neigiamas Netflow** (Outflow > Inflow) = Lokalus saugumas (Supply Shock).
*   **Exchange Whale Ratio**: Ar didelės sumos juda į biržas? Jei top 10 įnašų sudaro didelę dalį – bangas kelia milžinai.

## 4. Rinkos Mikrostruktūra (The "Micro")
Matuojama iš dolerinių barų ar Tick duomenų (AFML metodai).
*   **VPIN**: Matuoja "nuodingą" srautą. Jei VPIN kyla – tave "valgo" informuoti algoritmų žaidėjai.
*   **Orderbook Imbalance**: Pirkėjų vs Pardavėjų eilės gylis (Bid vs Ask).
*   **Tick Entropy**: Rinkos informacijos tankis. Maža entropija = nuspėjamas trendas.
*   **Relative Volume (RV)**: Ar dabartinis aktyvumas yra anomalija lyginant su vidurkiu?

## 5. FinBERT & Geopolitinis pulsas (Deep Sentiment)
Kaip Meta-Modelis "mato" karus ar teroro išpuolius per `ProsusAI/finBERT`.
*   **FinBERT Pipeline**: AI modelis skenuoja naujienų antraštes ir priskiria jas vienai iš 3 kategorijų:
    - **Positive** (Geros žinios)
    - **Negative** (Pavojus/Karas/Krizė)
    - **Neutral** (Fonas)
*   **Sentiment Velocity**: Jei per 10 minučių pasirodo 20 "Negative" naujienų – Risk Manager iškart mažina svertą (leverage), net jei kaina dar nepajudėjo.
*   **GPR (Geopolitical Risk)**: Matuoja įtampą pasaulio lygiu (pvz. tarp valstybių).
*   **USDT/CNY Premium**: Jei Kinijoje žmonės masiškai perka USDT brangiau nei dolerį – vadinasi, ten yra panika arba didelis poreikis trauktis iš vietinės valiutos.

## 6. Matematika: Kaip sugeneruoti papildomus kintamuosius?
Kiekvieną iš viršuje paminėtų rodiklių mes paverčiame keliais kintamaisiais taikydami šias transformacijas:
1.  **Velocity (Greitis)**: 1h, 4h, 1d reikšmės pokytis.
2.  **Acceleration (Pagreitis)**: Ar pokytis greitėja?
3.  **Z-Score**: Nukrypimas nuo 20/50 dienų vidurkio (Anomalijos aptikimas).
4.  **FracDiff**: Stacionarumo užtikrinimas išlaikant "atmintį".
5.  **Volatility of Feature**: Ar pats rodiklis (pvz. DXY) pradėjo šokinėti?

---
## 7. Timeframes & Dažnumas (Sampling Strategy)
Kadangi tavo trade'ai trunka nuo 15 min. iki 1 d., kyla klausimas: kokiu dažnumu rinkti duomenis?

### „Ašis“: Dollar Bars (Market Time)
Mes nenaudojame standartinio laiko (1h, 4h), nes jis yra pilnas „triukšmo“. Pagrindinis failas išlieka **Dollar Bars**.
*   **Kodėl?** Doleriniai barai juda tada, kai rinkoje vyksta veiksmas. Naktį (mažas volumas) barų bus mažai, o per didelį dump'ą (didelis volumas) – barų bus daug. Tai leidžia Meta-Modeliui geriau matyti struktūrą.

### Kaip sujungti skirtingus dažnumus?
1.  **Macro (DXY, SPX, FED)**: Šie duomenys keičiasi 1 kartą per dieną. Mes juos „ištęsime“ (Forward Fill) per visus tos dienos dolerinius barus. Tai parodo bendrą tos dienos „foną“.
2.  **On-Chain (Netflow, ETF)**: Keičiasi kas valandą arba dieną. Sukuriame valandinį vidurkį.
3.  **Intraday (OI, Funding, Sentiment)**: Tai jautriausi duomenys (15min - 1h). Jie tiesiogiai sinchronizuojami su artimiausiu doleriniu baru per `merge_asof`.

### Kaip tai pritaikyti tavo trade'ams?
*   **15 min / 1 h trades**: Meta-Modelis žiūri į paskutinius 5–10 dolerinių barų srautą (VPIN, Sentiment Velocity).
*   **4 h / 1 d trades**: Meta-Modelis naudoja **Moving Averages** (slenkančius vidurkius) ant tų pačių kintamųjų, kad „išlygintų“ triukšmą ir matytų ilgalaikę tendenciją.

**Išvada**: Tau nereikia skirtingų „sintetinių“ failų kiekvienam timeframe'ui. Mes naudojame **vieną didelį Datasetą (Dollar Bars)**, o modelio viduje pritaikome „lęšius“: trumpiems trade'ams – „aštrus“ vaizdas, ilgiems – „išlygintas“ (smoothed) vaizdas.
