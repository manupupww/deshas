# Binance Duomenų Valdymo Dashboard (Planas)

Šio projekto tikslas yra sukurti patogią grafinę sąsają (GUI), skirtą automatizuotam Binance duomenų (Klines, Liquidations, AggTrades) atsisiuntimui ir valdymui.

## 1. Technologijų krūva (Tech Stack)
- **Framework**: [Streamlit](https://streamlit.io/) (Greitas UI kūrimas naudojant Python).
- **Library**: `ccxt` arba `python-binance` (Tiesioginiam API).
- **Data handling**: `pandas` (Duomenų apdorojimui ir CSV saugojimui).
- **Bulk Download**: Logika skirta jungtis prie `data.binance.vision` (istoriniams CSV failams).

## 2. Pagrindinės funkcijos
- **Simbolio pasirinkimas**: Paieška ir pasirinkimas (pvz., BTCUSDT, ETHUSDT).
- **Intervalų pasirinkimas**:
    - Sekundės: `1s`
    - Minutės: `1m`, `3m`, `5m`, `15m`, `30m`
    - Valandos: `1h`, `2h`, `4h`, `6h`, `8h`, `12h`
    - Dienos/Savaitės/Mėnesiai: `1d`, `3d`, `1w`, `1mo`
- **Duomenų tipai**:
    - `Klines` (Žvakių duomenys).
    - `Liquidations` (Likvidavimų istorija).
    - `AggTrades` (Agreguoti sandoriai).
- **Laiko rėmiai**: Kalendoriaus pasirinkimas (Pradžios data - Pabaigos data).
- **Progresas**: Realaus laiko progreso juosta atsisiuntimo metu.

## 3. Planuojama struktūra
```text
dashboard/
├── app.py              # Pagrindinis Streamlit UI kodas
├── downloader.py       # Atsisiuntimo logika (API/Vision crawler)
├── utils.py            # Pagalbinės funkcijos (duomenų formatavimas, valymas)
├── requirements.txt    # Reikalingos bibliotekos
└── data/               # Laikinas aplankalas parsiųstiems duomenims
```

## 4. Įgyvendinimo etapai
1. **Etapas 1**: Streamlit karkaso paruošimas ir Klines atsisiuntimo integracija per CCXT.
2. **Etapas 2**: Išplėstinis atsisiuntimas iš `data.binance.vision` dideliems kiekiams.
3. **Etapas 3**: Likvidavimo duomenų (Liquidations) istorijos surinkimas.
4. **Etapas 4**: Duomenų apjungimas į vieną CSV failą pagal pasirinktus parametrus.
