# 🧹 Polymarket Sweep Tracker (POLswepper.py) – Vartotojo Gidas

Šis dokumentas paaiškina, kaip veikia jūsų Polymarket sandorių sekimo sistema ir kaip ją konfigūruoti.

## 📌 Pagrindinė paskirtis
`POLswepper.py` yra realaus laiko terminalo įrankis, skirtas stebėti didelius statymus (**sweeps**) Polymarket platformoje. Jis padeda matyti, kur „banginiai“ (dideli žaidėjai) deda savo pinigus, prieš tai darant kitiems.

---

## ⚙️ Konfigūracija (Kaip pakeisti nustatymus)
Atidarykite `POLswepper.py` ir viršuje rasite šiuos kintamuosius:

| Kintamasis | Reikšmė | Paaiškinimas |
| :--- | :--- | :--- |
| `MIN_SWEEP_AMOUNT_USD` | `3000` | Minimali suma rodymui. Viskas, kas mažiau, bus ignoruojama. |
| `REFRESH_INTERVAL_SECONDS` | `5` | Kas kiek sekundžių terminalas atnaujina duomenis. |
| `TIME_WINDOW_MINUTES` | `30` | Kiek laiko senumo sandorius rodyti (pvz., paskutinės 30 min). |
| `HIGHLIGHT_MULTIPLIER` | `3` | Jei sandoris > minimumas * šis skaičius (pvz., $9,000), jis bus ryškiai geltonas. |

---

## 📟 Terminalo rodmenys
Skriptas naudoja spalvas, kad greitai suprastumėte situaciją:

1.  **Balta/Normalus tekstas**: Įprasti sandoriai virš $3,000.
2.  **🟡 Geltonas fonas**: „Whale alert“! Labai didelis sandoris (Whale move).
3.  **🟢 Žalia spalva (YES)**: Žaidėjas stato už tai, kad įvykis ATSITIKS.
4.  **🔴 Raudona spalva (NO)**: Žaidėjas stato už tai, kad įvykis NEATSITIKS.

---

## 🛠️ Kaip paleisti?
Prieš leidžiant, įsitikinkite, kad turite visas reikiamas bibliotekas:
```powershell
pip install pandas termcolor colorama pytz
```

Paleidimas:
```bash
python POLswepper.py
```

---

## 💡 Svarbu žinoti
- **Duomenų šaltinis**: Skriptas skaito failą `data/sweeps_database.csv`. Jei šis failas neegzistuoja arba yra tuščias, terminalas rodys „No sweeps yet“.
- **Interaktyvumas**: Jei jūsų terminalas palaiko nuorodas, galite paspausti **„🔗 View Market“**, kad tiesiogiai atsidarytumėte Polymarket puslapį naršyklėje.
- **Wsl/Docker**: Kadangi dirbate Windows sistemoje, rekomenduojama naudoti PowerShell arba Windows Terminal geriausiam spalvų atvaizdavimui.

---

*Parengta Antigravity AI, 2026 m. kovas*
