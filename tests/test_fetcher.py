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


class TestWorldBankFallback:
    def test_fetch_all_fallback(self):
        """Test that fetch_all produces fallback data when API is unavailable."""
        from src.data.fetcher import load_config, fetch_all
        config = load_config()
        result = fetch_all(config, force_refetch=True)
        assert "world_bank" in result
        assert "berec_dates" in result
        assert "itu" in result
        assert "uk_parliament" in result
        assert "cept" in result
        assert "ncc" in result
        # Even if API fails, we get empty DataFrames
        assert isinstance(result["world_bank"], pd.DataFrame)


class TestLoadConfigInvalidPath:
    def test_load_config_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")


if __name__ == "__main__":
    pytest.main([__file__])
