"""Data preprocessing module.

Aligns country-year panel data, imputes missing values, creates derived features.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional


def align_panel(
    data_sources: dict[str, pd.DataFrame],
    countries: list[str],
    year_range: range,
) -> pd.DataFrame:
    """Merge multiple DataFrames into a single country-year panel.

    Inner join on (country, year) index.
    """
    panel = None
    for name, df in data_sources.items():
        if df.empty:
            continue
        if panel is None:
            panel = df.copy()
        else:
            panel = panel.merge(df, on=["country", "year"], how="outer")
    if panel is None:
        panel = pd.DataFrame({"country": [], "year": []})

    panel = panel[panel["country"].isin(countries)]
    panel = panel[panel["year"].isin(year_range)]
    return panel.reset_index(drop=True)


def impute_missing(
    panel: pd.DataFrame,
    method: str = "linear",
    max_gap: int = 3,
) -> pd.DataFrame:
    """Impute missing values in panel data.

    Args:
        method: 'linear', 'ffill', 'bfill', or 'cubic'
        max_gap: Maximum consecutive NaN values to impute.

    Returns:
        DataFrame with imputed values.
    """
    result = panel.copy()
    value_cols = [c for c in result.columns if c not in ("country", "year")]

    for col in value_cols:
        for country in result["country"].unique():
            mask = result["country"] == country
            series = result.loc[mask, col]

            if method in ("ffill", "bfill"):
                result.loc[mask, col] = series.fillna(method=method)
            elif method in ("linear", "cubic"):
                interpolated = series.interpolate(
                    method=method, limit=max_gap
                )
                result.loc[mask, col] = interpolated

            result.loc[mask, col] = result.loc[mask, col].bfill().ffill()

    return result


def add_pstn_phaseout_feature(
    panel: pd.DataFrame,
    switchoff_dates: dict[str, int | None],
    country_col: str = "country",
) -> pd.DataFrame:
    """Add binary has_pstn_phaseout covariate.

    has_pstn_phaseout = 1 in years >= switchoff_year for that country.
    Countries with no announced date get 0 for all years.
    """
    result = panel.copy()
    result["has_pstn_phaseout"] = 0

    for country, year in switchoff_dates.items():
        if year is None or pd.isna(year):
            continue
        mask = result[country_col] == country
        result.loc[mask & (result["year"] >= year), "has_pstn_phaseout"] = 1

    return result


def add_derived_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add computed features like YoY change, 3-year moving avg."""
    result = panel.copy()
    value_cols = [c for c in result.columns if c not in ("country", "year")]

    for col in value_cols:
        result[f"{col}_yoy"] = result.groupby("country")[col].pct_change()
        result[f"{col}_ma3"] = (
            result.groupby("country")[col]
            .transform(lambda s: s.rolling(3, min_periods=1).mean())
        )

    return result


def build_product_lifetime_table(
    panel: pd.DataFrame,
    product_intro_year: int,
    penetration_col: str = "fixed_subs_value",
    death_threshold: float = 0.05,
) -> pd.DataFrame:
    """Build survival analysis dataset from market penetration data.

    Defines product "death" as year when penetration < death_threshold * peak.
    Returns DataFrame with columns: country, market_lifetime, product_dead, covariates.
    """
    records = []
    for country in panel["country"].unique():
        ctry = panel[panel["country"] == country].sort_values("year")
        peak = ctry[penetration_col].max()
        if pd.isna(peak) or peak <= 0:
            continue
        death_val = death_threshold * peak

        intro_mask = ctry["year"] >= product_intro_year
        post_intro = ctry[intro_mask]
        if post_intro.empty:
            continue

        last_year = post_intro["year"].max()
        last_val = post_intro[penetration_col].iloc[-1]

        if last_val < death_val:
            dead_rows = post_intro[post_intro[penetration_col] < death_val]
            death_year = dead_rows["year"].iloc[0]
            product_dead = 1
        else:
            death_year = last_year
            product_dead = 0

        lifetime = death_year - product_intro_year

        covariate_cols = [
            c for c in ctry.columns
            if c not in ("country", "year")
            and "_value" in c
            and c != penetration_col
        ]
        covariate_row = ctry.loc[ctry["year"] == product_intro_year, covariate_cols]
        covariates = {}
        if not covariate_row.empty:
            for c in covariate_cols:
                covariates[c] = covariate_row[c].values[0]

        records.append({
            "country": country,
            "market_lifetime": max(lifetime, 0),
            "product_dead": product_dead,
            "peak_penetration": peak,
            **covariates,
        })

    result = pd.DataFrame(records)
    if "has_pstn_phaseout" in panel.columns:
        phaseout_map = (
            panel[panel["year"] >= product_intro_year]
            .groupby("country")["has_pstn_phaseout"]
            .max()
            .to_dict()
        )
        result["has_pstn_phaseout"] = result["country"].map(phaseout_map).fillna(0)

    return result


def save_processed(panel: pd.DataFrame, path: str = "data/processed/panel_data.csv") -> None:
    """Save processed panel data to CSV."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(path, index=False)
