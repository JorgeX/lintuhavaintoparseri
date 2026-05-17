import pandas as pd
from datetime import datetime


def main():
    input_file = "ORIG-Table 1.csv"
    output_file = "lintuhavainnot.md"

    print(f"Luetaan tiedostoa {input_file}...")

    # Yritetaan ladata tiedosto yleisimmilla koodauksilla.
    try:
        df = pd.read_csv(input_file, sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(input_file, sep=";", encoding="latin1")

    # --- ESIKASITTELY ---

    # 1) Paivamaarat
    df["dt1"] = pd.to_datetime(df["Pvm1"], format="%d.%m.%y", errors="coerce")
    df["dt2"] = pd.to_datetime(df["Pvm2"], format="%d.%m.%y", errors="coerce")
    df = df.dropna(subset=["dt1"])
    df["month"] = df["dt1"].dt.month
    df["day_of_year"] = df["dt1"].dt.dayofyear

    # 2) Maarat
    df["count_num"] = df["Määrä"].fillna(0).astype(int)
    df["Tila"] = df["Tila"].fillna("").astype(str)

    def format_count_string(row):
        c = row["count_num"]
        t = row["Tila"].strip()
        if c == 0 and not t:
            return ""
        s = str(c) if c > 0 else ""
        if t:
            s += t.replace(" ", "")
        return s

    df["count_str"] = df.apply(format_count_string, axis=1)

    # 3) Kuntalyhenteet
    kunta_map = {
        "Raahe": "RAA",
        "Pyhäjoki": "PYI",
        "Siikajoki": "SII",
        "Oulu": "OUL",
        "Hailuoto": "HAI",
        "Liminka": "LIM",
        "Lumijoki": "LUM",
        "Tyrnävä": "TYR",
        "Kempele": "KEM",
        "Iin": "II",
        "Ii": "II",
        "Kalajoki": "KAL",
        "Merijärvi": "MER",
        "Muhos": "MUH",
        "Utajärvi": "UTA",
        "Vaala": "VAA",
    }

    def get_kunta_abbr(kunta):
        if not isinstance(kunta, str):
            return "UNK"
        k = kunta.strip()
        if k in kunta_map:
            return kunta_map[k]
        return k[:3].upper()

    df["kunta_abbr"] = df["Kunta"].apply(get_kunta_abbr)

    # 4) Paivamaaravalit
    def format_date_range(row):
        d1 = row["dt1"]
        d2 = row["dt2"]
        if pd.isnull(d1):
            return ""
        if pd.isnull(d2) or d1 == d2:
            return f"{d1.day}.{d1.month}."
        if d1.month == d2.month:
            return f"{d1.day}.-{d2.day}.{d1.month}."
        return f"{d1.day}.{d1.month}.-{d2.day}.{d2.month}."

    df["date_str"] = df.apply(format_date_range, axis=1)

    # 5) Havainnoijat ja paikka
    df["Havainnoijat"] = df["Havainnoijat"].fillna("")
    df["Paikka"] = df["Paikka"].fillna("").astype(str)

    def make_obs_str(row):
        observer = row["Havainnoijat"].strip()
        observer_part = f" ({observer})" if observer else ""
        count_part = f" {row['count_str']}" if row["count_str"] else ""
        place = row["Paikka"].strip()
        place_part = f" {place}" if place else ""
        return f"{row['date_str']} {row['kunta_abbr']}{place_part}{count_part}{observer_part}".strip()

    df["obs_full"] = df.apply(make_obs_str, axis=1)

    # --- PARSIMINEN JA MARKDOWN-RAKENNE ---

    print("Käsitellään lajeja...")

    md_lines = []
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    md_lines.append("# Lintuhavainnot")
    md_lines.append("")
    md_lines.append(f"_Generoitu: {now}_")
    md_lines.append("")

    species_list = sorted(df["Laji"].dropna().unique())

    def add_section_with_list(lines, heading, rows, intro=None):
        if rows.empty:
            return
        lines.append(f"### {heading}")
        if intro:
            lines.append("")
            lines.append(intro)
        lines.append("")
        for item in rows["obs_full"].tolist():
            lines.append(f"- {item}")
        lines.append("")

    for sp in species_list:
        sub = df[df["Laji"] == sp].copy()
        sub = sub.sort_values(["dt1", "count_num"])
        if sub.empty:
            continue

        first_date = sub["dt1"].iloc[0]
        last_date = sub["dt1"].iloc[-1]
        total_count = int(sub["count_num"].sum())
        total_obs = len(sub)

        md_lines.append(f"## {str(sp).capitalize()}")
        md_lines.append("")
        md_lines.append(
            f"- Jakso: {first_date.day}.{first_date.month}.-{last_date.day}.{last_date.month}."
        )
        md_lines.append(f"- Yksilömäärä / havaintomäärä: {total_count}/{total_obs}")
        md_lines.append("")

        # 1) Ensimmaiset
        firsts = sub.sort_values(["dt1", "count_num"]).head(5)
        add_section_with_list(md_lines, "Ensimmäiset (max 5)", firsts)

        # 2) Ensimmaiset yli 10
        over10 = sub[sub["count_num"] > 10].sort_values(["dt1"]).head(5)
        add_section_with_list(md_lines, "Ensimmäiset yli 10 yks. (max 5)", over10)

        # 3) Ensimmaiset yli 100
        over100 = sub[sub["count_num"] > 100].sort_values(["dt1"]).head(5)
        add_section_with_list(md_lines, "Ensimmäiset yli 100 yks. (max 5)", over100)

        # 4) Kausimaksimit
        spring = (
            sub[sub["month"].isin([3, 4, 5])]
            .sort_values("count_num", ascending=False)
            .head(5)
        )
        add_section_with_list(md_lines, "Suurimmat määrät maalis-toukokuussa", spring)

        summer = (
            sub[sub["month"].isin([6, 7])]
            .sort_values("count_num", ascending=False)
            .head(5)
        )
        add_section_with_list(md_lines, "Suurimmat määrät kesä-heinäkuussa", summer)

        autumn = (
            sub[sub["month"].isin([8, 9, 10, 11])]
            .sort_values("count_num", ascending=False)
            .head(5)
        )
        add_section_with_list(md_lines, "Suurimmat määrät elo-marraskuussa", autumn)

        # 5) Viimeiset
        lasts = sub.sort_values(["dt1"], ascending=False).head(5).sort_values(["dt1"])
        add_section_with_list(md_lines, "Viimeiset (max 5)", lasts)

        # 6) Talvihavainnot
        winter = sub[sub["month"].isin([12, 1, 2])].sort_values(["dt1"])
        if not winter.empty:
            limit = 30
            if len(winter) > limit:
                intro = f"Talvihavaintoja yhteensä {len(winter)}, näytetään {limit} ensimmäistä."
                add_section_with_list(
                    md_lines, "Talvihavainnot", winter.head(limit), intro=intro
                )
            else:
                add_section_with_list(md_lines, "Talvihavainnot", winter)

        md_lines.append("---")
        md_lines.append("")

    print(f"Kirjoitetaan tulokset tiedostoon {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines).rstrip() + "\n")

    print("Valmis!")


if __name__ == "__main__":
    main()
