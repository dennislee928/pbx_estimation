"""Data fetching module for PBX estimation project.

Automatically downloads data from:
- World Bank API (fixed subscriptions, broadband, GDP, urbanization)
- ITU ICT statistics
- BEREC copper switch-off reports
"""

from pathlib import Path
from typing import Optional
import pandas as pd


def fetch_world_bank(
    indicators: dict[str, str],
    countries: list[str],
    start_year: int = 2000,
    end_year: int = 2025,
    cache_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """Fetch World Bank indicators for given countries.

    Uses wbgapi under the hood. Results cached to cache_dir/raw/world_bank.csv.
    """
    ...


def fetch_world_bank_single(
    indicator: str,
    countries: list[str],
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Fetch a single World Bank indicator."""
    ...


def fetch_berec_switchoff_dates(
    pdf_url: str = "https://www.berec.europa.eu/system/files/2024-12/BoR%20(24)%20181_Draft%20BEREC%20Report%20on%20copper%20switch-off_0.pdf",
) -> dict[str, int]:
    """Extract copper switch-off dates from BEREC report Table 3.

    Returns dict mapping country_code -> expected_full_switchoff_year.
    """
    ...


def fetch_itu_data() -> pd.DataFrame:
    """Fetch ITU ICT indicators from the ITU DataHub.

    Returns DataFrame with country-year level ICT infrastructure metrics.
    """
    ...


def fetch_all(
    config: dict,
    force_refetch: bool = False,
) -> dict[str, pd.DataFrame]:
    """Convenience function: run all fetchers and return dict of DataFrames."""
    ...
