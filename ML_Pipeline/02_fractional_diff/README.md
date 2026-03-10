# 02 — Fractional Differentiation (Phase 1, Step 2)

**Kova prieš Klaida #2: Integer Differentiation**

---

## Problema (Kodėl reikia?)

Kai tu nori ML modeliui paduoti kainą, turi problemą:

| Kas | Stacionaru? | Atmintis? | ML modelis gali mokytis? |
|---|---|---|---|
| **Originali kaina** (close) | NE | TAIP | NE — kaina eina tik aukštyn/žemyn, modelis mato tik trendą |
| **Returns** (`price.diff()`, d=1) | TAIP | NE | BLOGAI — prarado visą informaciją apie tai, kur kaina buvo |
| **Fractional Diff** (d=0.3) | TAIP | DALINAI | IDEALIAI — stacionari + atsimena praeities kryptį |

### Analogija
Įsivaizduok, kad kaina yra kaip knyga:
- **d=0** (originali) — skaitai visą knygą nuo pradžios. Per ilga, modelis pasimeta.
- **d=1** (diff) — skaitai tik paskutinį žodį. Per trumpa, prarandi kontekstą.
- **d=0.3** (frac diff) — skaitai paskutinius kelis skyrius. Pakanka suprasti istoriją!

---

## Naudojimas

### 1. Rasti optimalų d (pirmas žingsnis)
```bash
py frac_diff.py --input ../../data/BTCUSDT_2020-01-01_2020-12-31_dollarBars_100000000.csv
```

Skriptas tau parodys lentelę su visais d nuo 0.00 iki 1.00 ir pažymės,
kuris yra **OPTIMALUS** — t.y. mažiausias d, kuris pasiekia stacionarumą.

### 2. Išsaugoti rezultatą
```bash
py frac_diff.py --input ../../data/BTCUSDT_2020_dollarBars.csv --save
```

Sukurs naują CSV su papildomu stulpeliu `close_frac_diff_0.XX`.

---

## Ko tikėtis?

Tipinės BTC reikšmės:
- **d = 0.25–0.40** — dažniausiai pasitaikantis optimalus diapazonas
- **Memory correlation > 0.90** — reiškia, kad modelis vis dar „prisimena" 90% kainų judėjimo tendencijų

## Statusas: VYKDOMA
