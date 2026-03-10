# 🏭 Gamyklos SOP: Duomenų Inžinerija (Data Engineering)

**Tavo virtualus darbuotojas:** „Data Janitor AI“
**Jo vienintelis tikslas:** Užtikrinti, kad duomenys būtų švarūs, sinchronizuoti laike ir paruošti laiko eilutės (time-series) formatu be iškraipymų.

## 📋 Griežtos taisyklės AI asistentui
Kai dirbi su duomenimis, visada pradėk promptą nuo šių instrukcijų arba įklijuok šį tekstą:

> "Act as a Senior Quant Data Engineer. Your job is to process financial time-series data. 
> 1. NEVER use `for` loops for row-by-row iteration in Pandas. ALWAYS use vectorized operations.
> 2. Always check for and handle missing values (NaN, Inf) explicitly. Forward-fill price data, zero-fill volume data.
> 3. Standardize timestamps to Unix epoch (milliseconds) integer format across all datasets.
> 4. Use `pd.merge_asof` when aligning data with different sampling frequencies. NEVER use generic `merge` without nearest-neighbor matching for financial data.
> 5. Make sure no future data leaks into the past during grouping/rolling window operations. Only use `shift().rolling()`."

## 🧩 Dažniausi Užduočių Šablonai (Ką rašyti AI)

### 1 užduotis: Prijungti naują duomenų šaltinį
*   **Tavo Promptas:** *„Turiu naują CSV failą su Polymarket sweep informacija: timestamp, bet_size, outcome. Turiu master failą su BTC Dollar Bars. Parašyk skriptą, kuris importuoja Polymarket duomenis, paverčia laiko žymes į sutampantį standartą ir sujungia su Dollar Bars naudojant `merge_asof`, kad žinotume, koks buvo paskutinis Polymarket sweepas kiekvienos BTC žvakės metu.“*

### 2 užduotis: Paversti laiko žvakes į Information Bars
*   **Tavo Promptas:** *„Aš turiu 1-minutės OHLCV žvakes iš Binance per visus 2023 metus. Parašyk optimalų Python kodą (naudojant Numba arba Vectorized pandas), kuris šias laiko žvakes paverstų į Volume Bars (vienas baras = 1000 BTC traded volume) ir į Dollar Bars (vienas baras = $10M traded volume). Grąžink dviejų funkcijų kodą.“*

### 3 užduotis: Atminties (RAM) optimizacija
*   **Tavo Promptas:** *„Mano Parquet failas užima 15 GB, ir Pandas lūžta ('Out of Memory'). Parašyk skriptą naudojant Polars (vietoj Pandas) ir Dask, kuris užkrauna šį failą chunks'ais (dalimis), atlieka agregaciją (kas valandą) ir išsaugo kaip naują, mažesnį Parquet failą.“*

## 🛑 Kaip valdyti šį etapą
* Niekada neprašyk šio „AI darbuotojo“ daryti išvadų, spėlioti kainos, generuoti buy/sell signalų.
* Baigus šį etapą, rezultatą visada išsaugok atskirame aplanke (pvz., `data/processed/clean_stage_1.parquet`).
