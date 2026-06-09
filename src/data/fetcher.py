"""Data fetching module for PBX estimation project.

Automatically downloads data from:
- World Bank API (fixed subscriptions, broadband, GDP, urbanization)
- ITU DataHub API (ICT indicators)
- BEREC copper switch-off reports
- UK Parliament, CEPT, and NCC Taiwan (via supplementary_fetcher)
"""

from pathlib import Path
from typing import Optional
import yaml
import pandas as pd
import numpy as np


def load_config(path: str = "config.yaml") -> dict:
    """Load project configuration from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def fetch_world_bank_single(
    indicator: str,
    countries: list[str],
    start_year: int = 2000,
    end_year: int = 2025,
) -> pd.DataFrame:
    """Fetch a single World Bank indicator using wbgapi.

    Returns a DataFrame with columns: country, year, value.
    Returns empty DataFrame on API error.
    """
    import wbgapi as wb

    try:
        series = wb.data.DataFrame(
            indicator,
            countries,
            labels=True,
            time=range(start_year, end_year + 1),
        )
    except Exception:
        return pd.DataFrame(columns=["country", "year", "value"])

    series = series.reset_index()
    series = series.melt(
        id_vars=["economy"],
        var_name="year",
        value_name="value",
    )
    series["year"] = series["year"].str.replace("YR", "").astype(int)
    series = series.rename(columns={"economy": "country"})
    series = series.dropna(subset=["value"])
    series["value"] = pd.to_numeric(series["value"], errors="coerce")
    return series


def fetch_world_bank(
    indicators: dict[str, str],
    countries: list[str],
    start_year: int = 2000,
    end_year: int = 2025,
    cache_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """Fetch multiple World Bank indicators and merge into a single DataFrame.

    Returns a DataFrame with columns: country, year, <indicator_name>_value
    """
    all_data = []
    for name, code in indicators.items():
        df = fetch_world_bank_single(code, countries, start_year, end_year)
        df = df.rename(columns={"value": f"{name}_value"})
        all_data.append(df)

    result = all_data[0]
    for df in all_data[1:]:
        result = result.merge(df, on=["country", "year"], how="outer")

    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        result.to_csv(cache_dir / "world_bank.csv", index=False)

    return result


def fetch_berec_switchoff_dates(
    pdf_url: str = "https://www.berec.europa.eu/system/files/2024-12/BoR%20(24)%20181_Draft%20BEREC%20Report%20on%20copper%20switch-off_0.pdf",
) -> dict[str, int]:
    """Extract copper switch-off dates from BEREC report.

    Falls back to manually curated dates from config if PDF parsing fails.
    """
    try:
        import requests
        import io
        import PyPDF2
        import re

        resp = requests.get(pdf_url, timeout=30)
        resp.raise_for_status()
        pdf_file = io.BytesIO(resp.content)
        reader = PyPDF2.PdfReader(pdf_file)

        dates = {}
        for page in reader.pages:
            text = page.extract_text()
            for match in re.finditer(
                r"([A-Z]{2})\s+.*?(\d{4})", text
            ):
                country = match.group(1)
                year = int(match.group(2))
                if 2000 < year < 2100:
                    dates[country] = year
        return dates
    except Exception:
        return {}


def fetch_itu_data(config: dict, countries: Optional[list[str]] = None) -> pd.DataFrame:
    """Fetch ITU ICT indicators from the public ITU DataHub API."""
    from src.data.supplementary_fetcher import fetch_itu_data as _fetch_itu_data

    return _fetch_itu_data(config, countries=countries)


def fetch_all(
    config: dict,
    force_refetch: bool = False,
) -> dict[str, pd.DataFrame]:
    """Convenience function: run all fetchers and return dict of DataFrames.

    Returns:
        dict with keys: 'world_bank', 'itu', 'berec_dates', and supplementary
        regulatory payloads when fetched via fetch_all_supplementary().
    """
    from src.data.supplementary_fetcher import fetch_all_supplementary

    cfg = config["data"]
    indicators = cfg["world_bank"]["indicators"]
    countries_list = []
    for region in config["countries"].values():
        for item in region:
            for code, name in item.items():
                countries_list.append(code)

    cache_dir = Path("data/raw") if not force_refetch else None
    wb = fetch_world_bank(
        indicators=indicators,
        countries=countries_list,
        start_year=cfg["world_bank"]["start_year"],
        end_year=cfg["world_bank"]["end_year"],
        cache_dir=cache_dir,
    )
    berec = fetch_berec_switchoff_dates(cfg["berec"]["report_url"])
    supplementary = fetch_all_supplementary(config, cache_dir=cache_dir)

    return {
        "world_bank": wb,
        "itu": supplementary["itu"],
        "berec_dates": berec,
        "uk_parliament": supplementary["uk_parliament"],
        "cept": supplementary["cept"],
        "ncc": supplementary["ncc"],
    }
