# 💰 Dollar Bars Standalone Project

Šis aplankas skirtas Dollar Bars (informacijos barų) kūrimui iš Binance AggTrades duomenų.

## Kodėl Dollar Bars?
Tradiciškai prekybos duomenys renkami kas X minučių. Tačiau rinkos aktyvumas yra netolygus. Dollar Bars užtikrina:
1. **Geresnes statistines savybes:** Barai turi pastovesnę varianciją (mažesnis heteroskedastiškumas).
2. **Normalesnį paskirstymą:** Grąžos (returns) skirstinys tampa artimesnis Gausio (normaliajam) skirstiniui.
3. **Informacinį efektyvumą:** Barai formuojasi tada, kai vyksta realus "judesys", o ne tiesiog praeina laikas.

## Kaip naudotis
Naudokite `generator.py` skriptą nurodydami AggTrades CSV failą:

```bash
python generator.py --input path/to/aggtrades.csv --threshold 1000000
```

### Parametrai:
- `--input`: Kelias iki Binance AggTrades CSV failo.
- `--threshold`: Dolerių suma, kurią pasiekus uždaromas baras (numatyta: 1,000,000).
- `--output`: (Nebūtina) Kelias, kur išsaugoti rezultatą.

## Duomenų šaltinis
AggTrades duomenis galite atsisiųsti naudodami pagrindinį dashboardą (**Binance Data Dashboard**) pasirinkę "AggTrades" tipą.
