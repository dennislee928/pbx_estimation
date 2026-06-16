"""Tests for the data fetcher module."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import tempfile
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.fetcher import load_config


class TestLoadConfig:
    def test_load_config_returns_dict(self):
        config = load_config("config.yaml")
        assert isinstance(config, dict)
        assert "countries" in config
        assert "model" in config
        assert "data" in config

    def test_countries_loaded(self):
        config = load_config()
        total = sum(len(v) for v in config["countries"].values())
        assert total == 13  # 5 asia + 5 europe + 3 americas

    def test_pstn_switchoff_dates(self):
        config = load_config()
        dates = config["data"]["pstn_switchoff"]
        assert isinstance(dates, dict)
        assert dates["gb"] == 2027  # UK
        assert dates["nl"] == 2019  # Netherlands
        assert dates["tw"] is None  # Taiwan no date


class TestWorldBankFetch:
    def test_fetch_all_returns_real_world_bank_data(self):
        """fetch_all must return real World Bank data, never synthetic."""
        from src.data.fetcher import load_config, fetch_all
        config = load_config()
        result = fetch_all(config, force_refetch=True)
        for key in ("world_bank", "berec_dates", "itu",
                    "uk_parliament", "cept", "ncc"):
            assert key in result
        wb = result["world_bank"]
        assert isinstance(wb, pd.DataFrame)
        # Real data was retrieved (not an empty fabricated fallback).
        assert not wb.empty
        assert "GBR" in set(wb["country"])

    def test_world_bank_failure_raises_not_silently_empty(self):
        """An API failure must raise, never silently return fake/empty data."""
        from src.data.fetcher import fetch_world_bank_single
        with pytest.raises(RuntimeError):
            # Bogus indicator code triggers an API error.
            fetch_world_bank_single("NOT.A.REAL.CODE", ["GBR"], 2019, 2020)

    def test_to_world_bank_codes_maps_iso3_and_drops_taiwan(self):
        from src.data.fetcher import to_world_bank_codes
        assert to_world_bank_codes(["gb", "jp", "us"]) == ["GBR", "JPN", "USA"]
        assert "tw" not in to_world_bank_codes(["tw", "gb"])


class TestLoadConfigInvalidPath:
    def test_load_config_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")


if __name__ == "__main__":
    pytest.main([__file__])
