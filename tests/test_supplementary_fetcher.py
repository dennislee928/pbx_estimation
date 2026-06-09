"""Tests for supplementary public data fetchers."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.fetcher import load_config
from src.data.supplementary_fetcher import (
    _extract_uk_switchoff_from_text,
    _normalize_itu_frame,
    fetch_ncc_taiwan_telecom,
    fetch_uk_pstn_switchoff,
    merge_pstn_switchoff_dates,
    ncc_to_annual_panel,
)


class TestUkSwitchoffParsing:
    def test_extract_january_2027(self):
        text = "By January 2027, landline telephone services in the UK will switch to a fully digital network."
        assert _extract_uk_switchoff_from_text(text) == 2027

    def test_extract_none_without_signal(self):
        assert _extract_uk_switchoff_from_text("No relevant timeline here.") is None


class TestItuNormalization:
    def test_normalize_itu_frame(self):
        raw = pd.DataFrame(
            {
                "entityIso": ["TWN", "USA"],
                "dataYear": [2020, 2020],
                "dataValue": [100.0, 200.0],
            }
        )
        frame = _normalize_itu_frame(raw, "itu_fixed_subs_value")
        assert set(frame["country"]) == {"tw", "us"}
        assert "itu_fixed_subs_value" in frame.columns


class TestMergePstnSwitchoff:
    def test_merge_prefers_existing_config_then_scraped(self):
        config = load_config()
        merged = merge_pstn_switchoff_dates(
            config,
            berec_dates={"gb": 2026},
            uk_result={"country_code": "gb", "switchoff_year": 2027},
            cept_result={"countries": [{"country_code": "de", "mentioned_year": 2019}]},
        )
        assert merged["gb"] == 2027
        assert merged["de"] == 2020


class TestNccParsing:
    def test_ncc_to_annual_panel(self):
        ncc = pd.DataFrame(
            {
                "country": ["tw", "tw"],
                "year": [2024, 2024],
                "month": [1, 2],
                "metric": ["mobile_subscribers", "mobile_subscribers"],
                "value": [100.0, 200.0],
                "source": ["ncc", "ncc"],
            }
        )
        annual = ncc_to_annual_panel(ncc)
        assert len(annual) == 1
        assert annual.iloc[0]["ncc_mobile_subscribers_value"] == 150.0

    @patch("src.data.supplementary_fetcher._get")
    def test_fetch_ncc_taiwan_telecom_parses_mobile_csv(self, mock_get):
        csv_body = (
            "統計期,類別,業者名稱,用戶數\n"
            "11301,4G,中華電信股份有限公司,1000\n"
            "11301,4G,總計,1000\n"
        ).encode("utf-8-sig")
        mobile_response = MagicMock()
        mobile_response.ok = True
        mobile_response.content = csv_body
        mobile_response.raise_for_status = MagicMock()

        numbers_response = MagicMock()
        numbers_response.ok = False

        mock_get.side_effect = [mobile_response, numbers_response]
        config = load_config()
        frame = fetch_ncc_taiwan_telecom(config)
        assert not frame.empty
        assert frame.iloc[0]["metric"] == "mobile_subscribers"
        assert frame.iloc[0]["year"] == 2024


class TestUkFetcherFallback:
    @patch("src.data.supplementary_fetcher._get")
    def test_fetch_uk_uses_config_fallback(self, mock_get):
        mock_get.side_effect = Exception("blocked")
        config = load_config()
        result = fetch_uk_pstn_switchoff(config)
        assert result["fetch_status"] == "fallback_config"
        assert result["switchoff_year"] == 2027


if __name__ == "__main__":
    pytest.main([__file__])
