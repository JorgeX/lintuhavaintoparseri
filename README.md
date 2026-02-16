# lintuhavaintoparseri

Tyokalu lintuhavaintojen CSV-aineiston muuntamiseen valmiiksi raporttitekstiksi.

## Mitä projektissa on

- `parseri.py`: tuottaa tekstitiedoston `lintuhavainnot.txt`
- `parseri_md.py`: tuottaa Markdown-raportin `lintuhavainnot.md`
- `ORIG-Table 1.csv`: syotedata (CSV, erotin `;`)

## Vaatimukset

- Python 3.9+ (toimii myos uudemmilla)
- Python-kirjastot:
  - `pandas`

Asenna riippuvuudet:

```bash
python3 -m pip install pandas
```

## Kaytto

Suorita projektin juuressa:

### 1) TXT-raportti

```bash
python3 parseri.py
```

Tuloste:

- `lintuhavainnot.txt`

### 2) Markdown-raportti

```bash
python3 parseri_md.py
```

Tuloste:

- `lintuhavainnot.md`

## Miten data kasitellaan lyhyesti

Skriptit:

- lukevat CSV:n (`;` erotin, UTF-8 tai latin1)
- normalisoivat paivamaarat ja maarat
- muodostavat havaintorivit (paiva, kunta, paikka, maara, havainnoijat)
- ryhmittelevat lajeittain
- kokoavat kategoriat, kuten:
  - ensimmaiset havainnot
  - ensimmaiset yli 10 / yli 100 yksiloa
  - kausimaksimit (kevat, kesa, syksy)
  - viimeiset havainnot
  - talvihavainnot

## Huomioita

- Skriptit odottavat, etta syotetiedoston nimi on `ORIG-Table 1.csv`.
- Jos haluat vaihtaa tiedostonimea, muuta muuttujaa `input_file` skriptin alussa.
