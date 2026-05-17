import pandas as pd
import numpy as np
import sys

def main():
    input_file = 'ORIG-Table 1.csv'
    output_file = 'lintuhavainnot.txt'

    print(f"Luetaan tiedostoa {input_file}...")
    
    # Yritetään ladata tiedosto, huomioidaan yleiset koodaukset
    try:
        df = pd.read_csv(input_file, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(input_file, sep=';', encoding='latin1')

    # --- ESIKÄSITTELY ---

    # 1. Päivämäärät: Muunnetaan Pvm1 ja Pvm2 aikaleimoiksi
    # Oletusformaatti on päivä.kuukausi.vuosi (esim. 18.11.22)
    df['dt1'] = pd.to_datetime(df['Pvm1'], format='%d.%m.%y', errors='coerce')
    df['dt2'] = pd.to_datetime(df['Pvm2'], format='%d.%m.%y', errors='coerce')
    
    # Poistetaan rivit, joissa ei ole kelvollista aloituspäivää
    df = df.dropna(subset=['dt1'])
    
    # Lisätään apusarakkeita lajittelua varten
    df['month'] = df['dt1'].dt.month
    df['day_of_year'] = df['dt1'].dt.dayofyear

    # 2. Määrät: Varmistetaan että on numeroita vertailuja varten
    # Erotellaan numero ja mahdollinen tilakoodi (esim. "14p")
    # CSV:ssä 'Määrä' näyttää olevan numeerinen ja 'Tila' erillinen sarake
    df['count_num'] = df['Määrä'].fillna(0).astype(int)
    df['Tila'] = df['Tila'].fillna('').astype(str)

    # Funktio määrä-tekstin luomiseen (esim. "14p")
    def format_count_string(row):
        c = row['count_num']
        t = row['Tila'].strip()
        
        # Jos määrä on 0 ja tila tyhjä, palauta tyhjä
        if c == 0 and not t: return ""
        
        s = str(c) if c > 0 else ""
        if t:
            # Poistetaan turhat välilyönnit tilakoodeista (esim. "p, kiert" -> "p,kiert")
            s += t.replace(" ", "")
        return s

    df['count_str'] = df.apply(format_count_string, axis=1)

    # 3. Paikkakunnat: Lyhennetään (RAA, OUL, jne.)
    kunta_map = {
        'Raahe': 'RAA', 'Pyhäjoki': 'PYI', 'Siikajoki': 'SII', 'Oulu': 'OUL',
        'Hailuoto': 'HAI', 'Liminka': 'LIM', 'Lumijoki': 'LUM', 'Tyrnävä': 'TYR',
        'Kempele': 'KEM', 'Iin': 'II', 'Ii': 'II', 'Kalajoki': 'KAL', 'Merijärvi': 'MER',
        'Muhos': 'MUH', 'Utajärvi': 'UTA', 'Vaala': 'VAA'
    }
    
    def get_kunta_abbr(kunta):
        if not isinstance(kunta, str): return "UNK"
        k = kunta.strip()
        # Tarkistetaan onko mapissa, muuten otetaan 3 ekaa kirjainta isolla
        if k in kunta_map: return kunta_map[k]
        return k[:3].upper()

    df['kunta_abbr'] = df['Kunta'].apply(get_kunta_abbr)

    # 4. Päivämääräteksti (käsittelee välit, esim. 14.–16.4.)
    def format_date_range(r):
        d1 = r['dt1']
        d2 = r['dt2']
        
        if pd.isnull(d1): return ""
        
        # Yksittäinen päivä (Pvm2 puuttuu tai on sama)
        if pd.isnull(d2) or d1 == d2:
            return f"{d1.day}.{d1.month}."
        
        # Aikaväli saman kuun sisällä
        if d1.month == d2.month:
            return f"{d1.day}.–{d2.day}.{d1.month}."
        else:
            # Aikaväli kuun vaihtuessa
            return f"{d1.day}.{d1.month}.–{d2.day}.{d2.month}."

    df['date_str'] = df.apply(format_date_range, axis=1)

    # 5. Havainnoijat
    df['Havainnoijat'] = df['Havainnoijat'].fillna('')

    # Luodaan valmis riviteksti: "Pvm KUN Paikka Määrä (Havainnoijat)"
    # Esim: "21.3. RAA Lupaluoto 14p (Matti Meikäläinen)"
    def make_obs_str(row):
        return f"{row['date_str']} {row['kunta_abbr']} {row['Paikka']} {row['count_str']} ({row['Havainnoijat']})"

    df['obs_full'] = df.apply(make_obs_str, axis=1)

    # --- PARSIMINEN ---

    print("Käsitellään lajeja...")
    
    all_output = []
    
    # Käydään läpi kaikki uniikit lajit
    # Järjestys: voidaan määritellä aakkosjärjestys tai systemaattinen jos data sallii.
    # Nyt mennään aakkosjärjestyksessä.
    species_list = sorted(df['Laji'].unique())
    
    for sp in species_list:
        sub = df[df['Laji'] == sp].copy()
        
        # Lajitellaan aikajärjestykseen
        sub = sub.sort_values(['dt1', 'count_num'])
        
        if len(sub) == 0: continue

        # Header-tiedot: (Eka Pvm - Vika Pvm, Yksilösumma/Havaintosumma)
        first_date = sub['dt1'].iloc[0]
        last_date = sub['dt1'].iloc[-1]
        total_count = sub['count_num'].sum()
        total_obs = len(sub)
        
        header = f"{sp.capitalize()} ({first_date.day}.{first_date.month}.–{last_date.day}.{last_date.month}., {total_count}/{total_obs})"
        all_output.append(header)
        
        # Apufunktio listan muotoiluun (pilkut ja "ja"-sana)
        def format_list(rows):
            if rows.empty: return ""
            items = rows['obs_full'].tolist()
            if len(items) == 1: return items[0]
            return ", ".join(items[:-1]) + " ja " + items[-1] + "."

        # KATEGORIA 1: Ensimmäiset (5 kpl)
        firsts = sub.sort_values(['dt1', 'count_num']).head(5)
        all_output.append("Ensimmäiset " + format_list(firsts))

        # KATEGORIA 2: Ensimmäiset yli 10 yks (5 kpl)
        over10 = sub[sub['count_num'] > 10].sort_values(['dt1']).head(5)
        if not over10.empty:
            all_output.append("Ensimmäiset yli 10 yks. " + format_list(over10))

        # KATEGORIA 3: Ensimmäiset yli 100 yks (5 kpl)
        over100 = sub[sub['count_num'] > 100].sort_values(['dt1']).head(5)
        if not over100.empty:
            all_output.append("Ensimmäiset yli 100 yks. " + format_list(over100))

        # KATEGORIA 4: Kausimaksimit (Top 5 per kausi)
        # Kevät: Maalis-Touko (3,4,5)
        spring = sub[sub['month'].isin([3,4,5])].sort_values('count_num', ascending=False).head(5)
        if not spring.empty:
            all_output.append("Suurimmat määrät maalis-toukokuussa " + format_list(spring))
            
        # Kesä: Kesä-Heinä (6,7)
        summer = sub[sub['month'].isin([6,7])].sort_values('count_num', ascending=False).head(5)
        if not summer.empty:
            all_output.append("Suurimmat määrät kesä-heinäkuussa " + format_list(summer))

        # Syksy: Elo-Marras (8,9,10,11)
        autumn = sub[sub['month'].isin([8,9,10,11])].sort_values('count_num', ascending=False).head(5)
        if not autumn.empty:
            all_output.append("Suurimmat määrät elo-marraskuussa " + format_list(autumn))

        # KATEGORIA 5: Viimeiset (5 kpl)
        # Otetaan viimeiset aikajärjestyksessä (sort desc), mutta käännetään tulostukseen kronologiseksi
        lasts = sub.sort_values(['dt1'], ascending=False).head(5)
        lasts_chronological = lasts.sort_values(['dt1'])
        all_output.append("Viimeiset " + format_list(lasts_chronological))

        # KATEGORIA 6: Talvihavainnot (Joulu, Tammi, Helmi)
        # Huom: Listataan kaikki tai max 20, aikajärjestyksessä.
        winter = sub[sub['month'].isin([12, 1, 2])].sort_values(['dt1'])
        if not winter.empty:
            limit = 30 # Rajoitetaan ettei tule sivukaupalla tekstiä jos laji on yleinen talvella
            if len(winter) > limit:
                all_output.append(f"Talvihavainnot (yht {len(winter)}, näytetään {limit} ensimmäistä) " + format_list(winter.head(limit)))
            else:
                all_output.append("Talvihavainnot " + format_list(winter))
        
        # Tyhjä rivi lajien väliin
        all_output.append("")

    # --- TALLENNUS ---
    
    print(f"Kirjoitetaan tulokset tiedostoon {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(all_output))
        
    print("Valmis!")

if __name__ == "__main__":
    main()