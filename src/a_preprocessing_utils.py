from pathlib import Path
import re
import numpy as np
import pandas as pd


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace(r"[^0-9a-zA-Z_]", "", regex=True)
    )
    return df


def pick_first_existing(df: pd.DataFrame, candidates, required=True):
    for col in candidates:
        if col in df.columns:
            return col
    if required:
        raise KeyError(f"None of these columns were found: {candidates}")
    return None


def parse_date_flex(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def parse_unix_flex(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    non_null = s.dropna()
    if non_null.empty:
        return pd.to_datetime(series, errors="coerce")
    median_val = non_null.median()
    unit = "ms" if median_val > 1e12 else "s"
    return pd.to_datetime(s, unit=unit, errors="coerce")


def to_nullable_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int32")


def extract_season_start_year(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()

    # First try 4-digit year, such as 2021 or 2021/22
    four_digit = s.str.extract(r"(\d{4})", expand=False)
    out = pd.to_numeric(four_digit, errors="coerce")

    # If still missing, try 2-digit season like 21/22 -> 2021
    mask = out.isna()
    two_digit = s[mask].str.extract(r"(\d{2})/\d{2}", expand=False)
    two_digit_num = pd.to_numeric(two_digit, errors="coerce")
    out.loc[mask] = np.where(two_digit_num.notna(), 2000 + two_digit_num, np.nan)

    return out.astype("Int32")


def map_broad_position(raw_position: pd.Series, sub_position: pd.Series = None) -> pd.Series:
    raw = raw_position.fillna("").astype(str).str.lower().str.strip()

    if sub_position is not None:
        sub = sub_position.fillna("").astype(str).str.lower().str.strip()
        txt = (raw + " " + sub).str.strip()
    else:
        txt = raw

    txt = (
        txt.str.replace("/", " ", regex=False)
           .str.replace("-", " ", regex=False)
           .str.replace("_", " ", regex=False)
    )

    gk_mask = txt.str.contains(r"\bgoalkeeper\b|\bkeeper\b", regex=True, na=False)

    defender_mask = txt.str.contains(
        r"defender|centre back|center back|left back|right back|full back|fullback|sweeper",
        regex=True,
        na=False
    )

    midfielder_mask = txt.str.contains(
        r"midfield|midfielder|defensive midfield|attacking midfield|central midfield|left midfield|right midfield",
        regex=True,
        na=False
    )

    forward_mask = txt.str.contains(
        r"forward|striker|winger|attack|centre forward|center forward|second striker|inside forward",
        regex=True,
        na=False
    )

    broad = np.select(
        [gk_mask, defender_mask, midfielder_mask, forward_mask],
        ["Goalkeeper", "Defender", "Midfielder", "Forward"],
        default="Other"
    )

    return pd.Series(broad, index=raw_position.index, dtype="string")


def clean_profiles(df: pd.DataFrame) -> pd.DataFrame:
    df = standardize_columns(df)

    player_id_col = pick_first_existing(df, ["player_id"])
    player_name_col = pick_first_existing(df, ["player_name", "name"], required=False)
    dob_col = pick_first_existing(df, ["date_of_birth", "dob"], required=False)
    position_col = pick_first_existing(df, ["main_position", "position", "player_main_position"], required=False)
    sub_position_col = pick_first_existing(df, ["player_sub_position", "sub_position"], required=False)
    joined_col = pick_first_existing(df, ["joined"], required=False)
    contract_expires_col = pick_first_existing(df, ["contract_expires"], required=False)
    current_club_col = pick_first_existing(df, ["current_club_id"], required=False)

    out = pd.DataFrame({
        "player_id": df[player_id_col].astype("string").str.strip()
    })

    out["player_name"] = df[player_name_col].astype("string").str.strip() if player_name_col else pd.Series(pd.NA, index=df.index, dtype="string")
    out["date_of_birth"] = parse_date_flex(df[dob_col]) if dob_col else pd.NaT
    out["raw_position"] = df[position_col].astype("string").str.strip() if position_col else pd.Series(pd.NA, index=df.index, dtype="string")
    out["raw_sub_position"] = df[sub_position_col].astype("string").str.strip() if sub_position_col else pd.Series(pd.NA, index=df.index, dtype="string")
    out["joined"] = parse_date_flex(df[joined_col]) if joined_col else pd.NaT
    out["contract_expires"] = parse_date_flex(df[contract_expires_col]) if contract_expires_col else pd.NaT
    out["current_club_id"] = df[current_club_col].astype("string").str.strip() if current_club_col else pd.Series(pd.NA, index=df.index, dtype="string")

    out["broad_position"] = map_broad_position(out["raw_position"], out["raw_sub_position"]).astype("category")

    out = out.dropna(subset=["player_id"]).drop_duplicates(subset=["player_id"]).reset_index(drop=True)
    return out


def clean_market_values(df: pd.DataFrame) -> pd.DataFrame:
    df = standardize_columns(df)

    player_id_col = pick_first_existing(df, ["player_id"])
    value_col = pick_first_existing(df, ["value", "market_value", "market_value_eur"], required=False)
    date_col = pick_first_existing(df, ["date"], required=False)
    date_unix_col = pick_first_existing(df, ["date_unix"], required=False)

    out = pd.DataFrame({
        "player_id": df[player_id_col].astype("string").str.strip()
    })

    if date_col:
        out["market_value_date"] = parse_date_flex(df[date_col])
    elif date_unix_col:
        out["market_value_date"] = parse_unix_flex(df[date_unix_col])
    else:
        raise KeyError("No market value date column found.")

    if value_col:
        out["market_value_eur"] = pd.to_numeric(df[value_col], errors="coerce")
    else:
        raise KeyError("No market value column found.")

    out = out.dropna(subset=["player_id", "market_value_date", "market_value_eur"])
    out = out.drop_duplicates(subset=["player_id", "market_value_date", "market_value_eur"])
    out = out.sort_values(["player_id", "market_value_date"]).reset_index(drop=True)

    return out


def clean_performances(df: pd.DataFrame) -> pd.DataFrame:
    df = standardize_columns(df)

    player_id_col = pick_first_existing(df, ["player_id"])
    season_col = pick_first_existing(df, ["season", "season_name"], required=False)
    competition_id_col = pick_first_existing(df, ["competition_id"], required=False)
    competition_name_col = pick_first_existing(df, ["competition_name"], required=False)
    team_id_col = pick_first_existing(df, ["team_id"], required=False)
    team_name_col = pick_first_existing(df, ["team_name"], required=False)

    out = pd.DataFrame({
        "player_id": df[player_id_col].astype("string").str.strip()
    })

    out["season"] = df[season_col].astype("string").str.strip() if season_col else pd.Series(pd.NA, index=df.index, dtype="string")
    out["season_start_year"] = extract_season_start_year(out["season"]) if season_col else pd.Series(pd.NA, index=df.index, dtype="Int32")
    out["competition_id"] = df[competition_id_col].astype("string").str.strip() if competition_id_col else pd.Series(pd.NA, index=df.index, dtype="string")
    out["competition_name"] = df[competition_name_col].astype("string").str.strip() if competition_name_col else pd.Series(pd.NA, index=df.index, dtype="string")
    out["team_id"] = df[team_id_col].astype("string").str.strip() if team_id_col else pd.Series(pd.NA, index=df.index, dtype="string")
    out["team_name"] = df[team_name_col].astype("string").str.strip() if team_name_col else pd.Series(pd.NA, index=df.index, dtype="string")

    numeric_cols = [
        "nb_in_group", "nb_on_pitch", "goals", "own_goals", "assists", "subed_in", "subed_out",
        "yellow_cards", "second_yellow_cards", "direct_red_cards", "penalty_goals",
        "minutes_played", "goals_conceded", "clean_sheets"
    ]

    for col in numeric_cols:
        if col in df.columns:
            out[col] = to_nullable_int(df[col])
        else:
            out[col] = pd.Series(pd.NA, index=df.index, dtype="Int32")

    out = out.dropna(subset=["player_id"]).drop_duplicates().reset_index(drop=True)
    return out


def build_lifecycle_backbone(
    profiles_clean: pd.DataFrame,
    market_clean: pd.DataFrame,
    min_obs_per_player: int = 3,
    min_age: float = 14.0,
    max_age: float = 45.0
) -> pd.DataFrame:
    keep_cols = ["player_id", "player_name", "date_of_birth", "raw_position", "raw_sub_position", "broad_position"]
    prof = profiles_clean[keep_cols].copy()

    df = market_clean.merge(prof, on="player_id", how="inner")

    df["age_days"] = (df["market_value_date"] - df["date_of_birth"]).dt.days
    df["age_years"] = df["age_days"] / 365.25

    df = df[df["market_value_eur"] > 0].copy()
    df = df[df["age_years"].between(min_age, max_age, inclusive="both")].copy()
    df = df[df["broad_position"].isin(["Goalkeeper", "Defender", "Midfielder", "Forward"])].copy()

    df = df.sort_values(["player_id", "market_value_date"]).reset_index(drop=True)
    df["n_market_value_obs"] = df.groupby("player_id")["market_value_date"].transform("size").astype("Int32")
    df = df[df["n_market_value_obs"] >= min_obs_per_player].copy()

    df["market_value_rank_desc"] = (
        df.groupby("player_id")["market_value_eur"]
          .rank(method="dense", ascending=False)
          .astype("Int32")
    )
    df["is_peak_value_obs"] = (df["market_value_rank_desc"] == 1)

    return df.reset_index(drop=True)


def build_data_dictionary() -> pd.DataFrame:
    rows = [
        ["player_profiles_clean.parquet", "player_id", "Player identifier", "string"],
        ["player_profiles_clean.parquet", "player_name", "Player display name", "string"],
        ["player_profiles_clean.parquet", "date_of_birth", "Date of birth", "datetime64[ns]"],
        ["player_profiles_clean.parquet", "raw_position", "Original position field from source", "string"],
        ["player_profiles_clean.parquet", "raw_sub_position", "Original sub-position field if present", "string"],
        ["player_profiles_clean.parquet", "broad_position", "Mapped broad group: Goalkeeper, Defender, Midfielder, Forward, Other", "category"],

        ["player_market_value_clean.parquet", "player_id", "Player identifier", "string"],
        ["player_market_value_clean.parquet", "market_value_date", "Date of market value observation", "datetime64[ns]"],
        ["player_market_value_clean.parquet", "market_value_eur", "Market value in euros", "float64"],

        ["player_performances_clean.parquet", "player_id", "Player identifier", "string"],
        ["player_performances_clean.parquet", "season", "Season label from source", "string"],
        ["player_performances_clean.parquet", "season_start_year", "Parsed first year of season", "Int32"],
        ["player_performances_clean.parquet", "minutes_played", "Minutes played", "Int32"],
        ["player_performances_clean.parquet", "goals", "Goals scored", "Int32"],
        ["player_performances_clean.parquet", "assists", "Assists", "Int32"],
        ["player_performances_clean.parquet", "clean_sheets", "Clean sheets", "Int32"],

        ["player_lifecycle_backbone.parquet", "player_id", "Player identifier", "string"],
        ["player_lifecycle_backbone.parquet", "market_value_date", "Date of market value observation", "datetime64[ns]"],
        ["player_lifecycle_backbone.parquet", "market_value_eur", "Market value in euros", "float64"],
        ["player_lifecycle_backbone.parquet", "date_of_birth", "Date of birth", "datetime64[ns]"],
        ["player_lifecycle_backbone.parquet", "age_days", "Age in days at market value date", "float64"],
        ["player_lifecycle_backbone.parquet", "age_years", "Age in years at market value date", "float64"],
        ["player_lifecycle_backbone.parquet", "broad_position", "Mapped broad position group", "category"],
        ["player_lifecycle_backbone.parquet", "n_market_value_obs", "Number of market value observations for player", "Int32"],
        ["player_lifecycle_backbone.parquet", "is_peak_value_obs", "Whether this row is tied for player peak market value", "bool"],
        ["player_lifecycle_backbone.parquet", "market_value_rank_desc", "Dense descending rank of market value within each player career history", "Int32"],
    ]

    return pd.DataFrame(rows, columns=["dataset", "column_name", "description", "dtype"])
