# 01 — Dollar Bars (Phase 1, Step 1)

**Kova prieš klaida #3: Inefficient Sampling**

## Kas tai?
Dollar Bars — tai žvakės, kurios susiformuoja ne kas X minučių, o kas $X USD apyvartos.
Kai rinka aktyvi, gaunama DAUGIAU barų. Kai rami — MAŽIAU. Taip kiekviena žvakė turi
vienodą kiekį rinkos informacijos.

## Naudojimas
```bash
py generator.py --input ../../data/aggtrades.csv --threshold 100000000
```

## Statusas: BAIGTA
Tavo duomenys: `data/BTCUSDT_2020-01-01_2020-12-31_dollarBars_100000000.csv` (10,490 barų)
