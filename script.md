# Ohjatun parserin ajaminen

Tämä ohje koskee skriptiä `ver2/parseri_ohjattu.py`. Skripti lukee havaintoaineiston ja lajikohtaisen ohjaustiedoston, ja kirjoittaa raportin sekä teksti- että Markdown-muodossa.

## Vaatimukset

- Python 3
- `pandas`

Asenna tarvittaessa:

```sh
python3 -m pip install pandas
```

## Oletusajo

Aja komento projektin juurikansiosta:

```sh
python3 ver2/parseri_ohjattu.py
```

Oletuksena skripti käyttää näitä tiedostoja:

- Havaintoaineisto: `katsaus data 2023.csv`
- Lajiohjaus: `katsauslajiohjaus.csv`
- Tekstitulos: `results/lintuhavainnot_ohjattu.txt`
- Markdown-tulos: `results/lintuhavainnot_ohjattu.md`

## Ajo eri tiedostoilla

Voit antaa syöte- ja tulostiedostot komentoriviltä:

```sh
python3 ver2/parseri_ohjattu.py \
  --input "lajidataexample - Sheet1.csv" \
  --guidance katsauslajiohjaus.csv \
  --txt-output results/lintuhavainnot_testi.txt \
  --md-output results/lintuhavainnot_testi.md
```

## Valitsimet

- `--input`: havaintoaineiston CSV-tiedosto.
- `--guidance`: lajikohtainen ohjaus-CSV.
- `--txt-output`: luotavan tekstitiedoston polku.
- `--md-output`: luotavan Markdown-tiedoston polku.

## Mitä skripti tekee

Skripti tunnistaa CSV-erottimen automaattisesti, lukee yleisimmillä merkistökoodauksilla, järjestää havainnot `Lajinumero`- ja päivämäärätietojen mukaan, ja tuottaa lajikohtaiset raporttiosiot `katsauslajiohjaus.csv`-tiedoston merkintöjen perusteella.
