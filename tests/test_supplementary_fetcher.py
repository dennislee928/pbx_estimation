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
    ncc_taiwan_legacy_decline_series,
    ncc_to_annual_panel,
    taiwan_decline_projection_row,
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

    def _legacy_decline_ncc(self):
        # Two rows per (year, month): a growing total and a declining legacy base.
        rows = []
        legacy = {2012: 6.5e6, 2013: 5.1e6, 2014: 3.2e6, 2015: 2.4e6, 2016: 1.9e6}
        total = {2012: 21e6, 2013: 23e6, 2014: 25e6, 2015: 26e6, 2016: 27e6}
        for yr in legacy:
            for mo in (1, 2):
                rows.append({"country": "tw", "year": yr, "month": mo,
                             "metric": "mobile_subscribers", "value": legacy[yr], "source": "ncc"})
                rows.append({"country": "tw", "year": yr, "month": mo,
                             "metric": "mobile_subscribers", "value": total[yr], "source": "ncc"})
        return pd.DataFrame(rows)

    def test_legacy_decline_series_isolates_declining_base(self):
        series = ncc_taiwan_legacy_decline_series(self._legacy_decline_ncc())
        assert list(series.index) == [2012, 2013, 2014, 2015, 2016]
        # Picks the smaller (legacy) sub-series, which declines.
        assert series.iloc[0] > series.iloc[-1]
        assert series.iloc[0] == pytest.approx(6.5e6)

    def test_taiwan_projection_row_is_declining_and_keyed_twn(self):
        row = taiwan_decline_projection_row(
            self._legacy_decline_ncc(), [2027, 2030, 2045]
        )
        assert row is not None
        assert row["market"] == "TWN"
        # A real decline => penetration shrinks across the horizon, all >= 0.
        assert row["2027"] >= row["2030"] >= row["2045"] >= 0.0

    def test_taiwan_projection_row_none_on_empty(self):
        assert taiwan_decline_projection_row(pd.DataFrame(), [2027]) is None

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
