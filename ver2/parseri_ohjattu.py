import argparse
import csv
from datetime import datetime
from pathlib import Path

import pandas as pd


DEFAULT_OBSERVATIONS = Path("katsaus data 2023.csv")
DEFAULT_GUIDANCE = Path("katsauslajiohjaus.csv")
DEFAULT_TEXT_OUTPUT = Path("results/lintuhavainnot_ohjattu.txt")
DEFAULT_MARKDOWN_OUTPUT = Path("results/lintuhavainnot_ohjattu.md")

FIRSTS_COLUMN = (
    "Ensimmäiset viisi havaintoa 1.1. alkaen (x), ensimmäinen yli 10 yksilön "
    "havaint (10), enimmäinen yli sadan yksilön havainto (100)  ensimmäinen yli "
    "tuhannen yksilön havainto (1000)"
)
SECRET_COLUMN = (
    "Salatut hvainnot; jos laji on salattu (merkintä salattu TIIIRA-aineistossa) "
    "JA laji tulee lajilistauskeen, merkitään seuraavsti ***SALATTU HAVAINTO ***"
)

KUNTA_MAP = {
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
    "Taivalkoski": "TAI",
    "Pudasjärvi": "PUD",
    "Oulainen": "OULAI",
    "Haapavesi": "HAA",
    "Kärsämäki": "KÄR",
}


def detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;").delimiter
    except csv.Error:
        return ";" if sample.count(";") > sample.count(",") else ","


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            with path.open(encoding=encoding) as handle:
                sample = handle.read(4096)
            delimiter = detect_delimiter(sample)
            return pd.read_csv(path, sep=delimiter, encoding=encoding)
        except UnicodeDecodeError:
            continue
    with path.open(encoding="latin1") as handle:
        sample = handle.read(4096)
    delimiter = detect_delimiter(sample)
    return pd.read_csv(path, sep=delimiter, encoding="latin1")


def clean_value(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def get_kunta_abbr(kunta) -> str:
    name = clean_value(kunta)
    if not name:
        return "UNK"
    return KUNTA_MAP.get(name, name[:3].upper())


def format_date_range(row) -> str:
    d1 = row["dt1"]
    d2 = row["dt2"]
    if pd.isna(d1):
        return ""
    if pd.isna(d2) or d1 == d2:
        return f"{d1.day}.{d1.month}."
    if d1.month == d2.month:
        return f"{d1.day}.–{d2.day}.{d1.month}."
    return f"{d1.day}.{d1.month}.–{d2.day}.{d2.month}."


def format_count_string(row) -> str:
    count = int(row["count_num"]) if not pd.isna(row["count_num"]) else 0
    state = clean_value(row.get("Tila", "")).replace(" ", "")
    count_text = str(count) if count > 0 else ""
    return f"{count_text}{state}" if state else count_text


def make_obs_str(row) -> str:
    place = clean_value(row.get("Paikka", ""))
    observers = clean_value(row.get("Havainnoijat", ""))
    count = clean_value(row.get("count_str", ""))

    parts = [row["date_str"], row["kunta_abbr"]]
    if place:
        parts.append(place)
    if count:
        parts.append(count)

    text = " ".join(part for part in parts if part).strip()
    if observers:
        text = f"{text} ({observers})"
    return text


def prepare_observations(df: pd.DataFrame) -> pd.DataFrame:
    required = ["Lajinumero", "Pvm1", "Kunta", "Paikka", "Määrä", "Tila", "Havainnoijat"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Havaintoaineistosta puuttuu sarakkeita: {', '.join(missing)}")

    df = df.copy()
    df["Lajinumero"] = pd.to_numeric(df["Lajinumero"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["Lajinumero"])
    df["Lajinumero"] = df["Lajinumero"].astype(int)

    df["dt1"] = pd.to_datetime(df["Pvm1"], format="%d.%m.%y", errors="coerce")
    df["dt2"] = pd.to_datetime(df.get("Pvm2", ""), format="%d.%m.%y", errors="coerce")
    df = df.dropna(subset=["dt1"])
    df["month"] = df["dt1"].dt.month
    df["count_num"] = pd.to_numeric(df["Määrä"], errors="coerce").fillna(0).astype(int)
    df["count_str"] = df.apply(format_count_string, axis=1)
    df["kunta_abbr"] = df["Kunta"].apply(get_kunta_abbr)
    df["date_str"] = df.apply(format_date_range, axis=1)
    df["obs_full"] = df.apply(make_obs_str, axis=1)
    df["species_name"] = df.get("suom", df.get("laji", "")).fillna("").astype(str)

    sort_columns = [
        column
        for column in ["Lajinumero", "dt1", "dt2", "count_num", "Kunta", "Paikka", "Havainto id"]
        if column in df.columns
    ]
    return df.sort_values(sort_columns, kind="mergesort")


def prepare_guidance(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Lajinumero"] = pd.to_numeric(df["Lajinumero"], errors="coerce")
    df = df.dropna(subset=["Lajinumero"])
    df["Lajinumero"] = df["Lajinumero"].astype(int)
    return df


def is_marked(value) -> bool:
    return bool(clean_value(value))


def split_guidance_tokens(value) -> list[str]:
    return [token.strip() for token in clean_value(value).replace(",", ";").split(";") if token.strip()]


def format_text_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " ja " + items[-1] + "."


def top_rows(rows: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    return rows.sort_values(["count_num", "dt1"], ascending=[False, True], kind="mergesort").head(limit)


def first_rows(rows: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    return rows.sort_values(["dt1", "count_num"], ascending=[True, True], kind="mergesort").head(limit)


def last_rows(rows: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    return rows.sort_values(["dt1"], ascending=False, kind="mergesort").head(limit).sort_values("dt1")


def rows_for_months(rows: pd.DataFrame, months: set[int]) -> pd.DataFrame:
    return rows[rows["month"].isin(months)].sort_values(["dt1", "count_num"], kind="mergesort")


def rows_for_municipalities(
    rows: pd.DataFrame, municipalities: set[str], include: bool = True
) -> pd.DataFrame:
    names = rows["Kunta"].fillna("").astype(str).str.casefold()
    wanted = {name.casefold() for name in municipalities}
    mask = names.isin(wanted)
    if not include:
        mask = ~mask
    return rows[mask].sort_values(["dt1", "count_num"], kind="mergesort")


def secret_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if "Salattu" not in rows.columns:
        return rows.iloc[0:0]
    return rows[rows["Salattu"].fillna("").astype(str).str.strip().ne("")]


def municipality_counts(rows: pd.DataFrame) -> list[str]:
    if rows.empty:
        return []
    counts = rows.groupby("kunta_abbr", dropna=False).size().sort_values(ascending=False)
    return [f"{kunta}: {count}" for kunta, count in counts.items()]


def first_sections(rows: pd.DataFrame, value: str, header: str) -> list[tuple[str, list[str]]]:
    sections = []
    tokens = split_guidance_tokens(value)
    if any(token.casefold() == "x" for token in tokens):
        selected = first_rows(rows)
        sections.append((header, selected["obs_full"].tolist()))

    for token in tokens:
        if not token.isdigit():
            continue
        threshold = int(token)
        selected = first_rows(rows[rows["count_num"] > threshold])
        sections.append((f"{header} / yli {threshold} yks.", selected["obs_full"].tolist()))
    return sections


def selected_sections(column: str, value: str, rows: pd.DataFrame) -> list[tuple[str, list[str]]]:
    if column == FIRSTS_COLUMN:
        return first_sections(rows, value, column)
    if column == SECRET_COLUMN:
        return [(column, ["***SALATTU HAVAINTO ***"])] if not secret_rows(rows).empty else []

    handlers = {
        "Kaikki Tammikuu, Helmikuu": lambda r: rows_for_months(r, {1, 2}),
        "Viimeiset viisi havaintoa vuoden lopusta": last_rows,
        "Vuoden viisi suurinta määrää": top_rows,
        "Alkuvuoden viisi suurinta määrää, kuukaudet tammikuu – kesäkuu": lambda r: top_rows(
            rows_for_months(r, {1, 2, 3, 4, 5, 6})
        ),
        "Loppuvuoden viisi suurinta määrää, kuukaudet kuukaudet heinäkuu – joulukuu": lambda r: top_rows(
            rows_for_months(r, {7, 8, 9, 10, 11, 12})
        ),
        "Viisi suurinta kevään määrää, kuukaudet maaliskuu – toukokuu": lambda r: top_rows(
            rows_for_months(r, {3, 4, 5})
        ),
        "Viisi kesän suurinta määrää, kuukaudet kesä-elokuu": lambda r: top_rows(
            rows_for_months(r, {6, 7, 8})
        ),
        "Viisi suurinta syyskauden määrää, kuukaudet elokuu - lokakuu": lambda r: top_rows(
            rows_for_months(r, {8, 9, 10})
        ),
        "Viisi talviajan suurinta määrää, kuukaudet tammi-helmikuu ja joulukuu": lambda r: top_rows(
            rows_for_months(r, {1, 2, 12})
        ),
        "kaikki havainnot": lambda r: r.sort_values(["dt1", "count_num"], kind="mergesort"),
        "kaikki kevään havainnot kuukaudet maaliskuu – toukokuu": lambda r: rows_for_months(
            r, {3, 4, 5}
        ),
        "kaikki kesän havainnot kuukauden kesäkuu – elokuu": lambda r: rows_for_months(
            r, {6, 7, 8}
        ),
        "kaikki syksyn havainnot, kuukaudet elokuu – lokakuu": lambda r: rows_for_months(
            r, {8, 9, 10}
        ),
        "Kaikki tammi-helmikuun ja joulukuun havainnot, ei Oulusta": lambda r: rows_for_municipalities(
            rows_for_months(r, {1, 2, 12}), {"Oulu"}, include=False
        ),
        "kaikki havainnot, kunnat Taivalkoski ja Pudasjärvi": lambda r: rows_for_municipalities(
            r, {"Taivalkoski", "Pudasjärvi"}
        ),
        "kaikki havainnot, ei kunnat Taivalkoski ja Pudasjärvi": lambda r: rows_for_municipalities(
            r, {"Taivalkoski", "Pudasjärvi"}, include=False
        ),
        "Kaikki joulukuu": lambda r: rows_for_months(r, {12}),
    }

    if column == "Havaintojen lukumäärä kunnittai kunnan nimi tai  nimilyhenne)":
        return [(column, municipality_counts(rows))]

    handler = handlers.get(column)
    if handler is None:
        print(f"Varoitus: ohjaussarakkeelle ei ole käsittelijää: {column}")
        return []

    selected = handler(rows)
    return [(column, selected["obs_full"].tolist())]


def species_display_name(rule: pd.Series, rows: pd.DataFrame) -> str:
    guided_name = clean_value(rule.get("laji", ""))
    if guided_name:
        return guided_name
    names = rows["species_name"].dropna().astype(str)
    return names.iloc[0] if not names.empty else f"Laji {rule['Lajinumero']}"


def species_header(name: str, rows: pd.DataFrame) -> str:
    first_date = rows["dt1"].min()
    last_date = rows["dt1"].max()
    total_count = int(rows["count_num"].sum())
    total_obs = len(rows)
    return (
        f"{name} ({first_date.day}.{first_date.month}.–{last_date.day}.{last_date.month}., "
        f"{total_count}/{total_obs})"
    )


def build_sections(rule: pd.Series, rows: pd.DataFrame, guidance_columns: list[str]):
    rendered = []
    for column in guidance_columns:
        value = rule.get(column, "")
        if not is_marked(value):
            continue
        for heading, items in selected_sections(column, value, rows):
            if items:
                rendered.append((heading, items))
    return rendered


def render_text(species_reports) -> str:
    lines = []
    for header, sections in species_reports:
        lines.append(header)
        for heading, items in sections:
            lines.append(f"{heading} {format_text_list(items)}".rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(species_reports) -> str:
    lines = ["# Lintuhavainnot", "", f"_Generoitu: {datetime.now():%d.%m.%Y %H:%M}_", ""]
    for header, sections in species_reports:
        name, _, summary = header.partition(" (")
        lines.append(f"## {name}")
        if summary:
            lines.append("")
            lines.append(f"- Yhteenveto: ({summary}")
        for heading, items in sections:
            lines.append("")
            lines.append(f"### {heading}")
            lines.append("")
            lines.extend(f"- {item}" for item in items)
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def create_reports(observations: pd.DataFrame, guidance: pd.DataFrame):
    guidance_columns = [column for column in guidance.columns if column not in {"Lajinumero", "laji"}]
    observation_groups = {number: rows for number, rows in observations.groupby("Lajinumero", sort=False)}
    species_reports = []

    for _, rule in guidance.iterrows():
        species_number = int(rule["Lajinumero"])
        rows = observation_groups.get(species_number)
        if rows is None or rows.empty:
            continue

        rows = rows.sort_values(["dt1", "count_num"], kind="mergesort")
        name = species_display_name(rule, rows)
        sections = build_sections(rule, rows, guidance_columns)
        if sections:
            species_reports.append((species_header(name, rows), sections))

    return species_reports


def parse_args():
    parser = argparse.ArgumentParser(description="Luo ohjattu lintuhavaintoraportti.")
    parser.add_argument("--input", type=Path, default=DEFAULT_OBSERVATIONS)
    parser.add_argument("--guidance", type=Path, default=DEFAULT_GUIDANCE)
    parser.add_argument("--txt-output", type=Path, default=DEFAULT_TEXT_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Luetaan havaintoaineistoa {args.input}...")
    observations = prepare_observations(read_csv_with_fallback(args.input))

    print(f"Luetaan lajiohjausta {args.guidance}...")
    guidance = prepare_guidance(read_csv_with_fallback(args.guidance))

    print("Käsitellään lajeja...")
    species_reports = create_reports(observations, guidance)

    print(f"Kirjoitetaan tekstitulos tiedostoon {args.txt_output}...")
    args.txt_output.parent.mkdir(parents=True, exist_ok=True)
    args.txt_output.write_text(render_text(species_reports), encoding="utf-8")

    print(f"Kirjoitetaan Markdown-tulos tiedostoon {args.md_output}...")
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.write_text(render_markdown(species_reports), encoding="utf-8")

    print(f"Valmis! Lajeja raportissa: {len(species_reports)}")


if __name__ == "__main__":
    main()
