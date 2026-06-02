"""Tests for the data preprocessor module."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.preprocessor import (
    align_panel,
    impute_missing,
    add_pstn_phaseout_feature,
    add_derived_features,
    build_product_lifetime_table,
)


@pytest.fixture
def sample_panel():
    return pd.DataFrame({
        "country": ["tw", "tw", "tw", "jp", "jp", "jp"],
        "year": [2000, 2005, 2010, 2000, 2005, 2010],
        "fixed_subs_value": [55.0, 50.0, 40.0, 60.0, 55.0, 45.0],
        "broadband_value": [5.0, 15.0, 30.0, 8.0, 20.0, 35.0],
        "gdp_per_capita_value": [20000, 25000, 30000, 35000, 40000, 45000],
        "urban_pop_value": [70.0, 75.0, 80.0, 85.0, 88.0, 90.0],
    })


@pytest.fixture
def panel_with_missing():
    return pd.DataFrame({
        "country": ["tw", "tw", "tw", "jp", "jp", "jp"],
        "year": [2000, 2001, 2002, 2000, 2001, 2002],
        "fixed_subs_value": [55.0, np.nan, 53.0, 60.0, 58.0, np.nan],
        "broadband_value": [5.0, 8.0, np.nan, 10.0, np.nan, np.nan],
    })


class TestAlignPanel:
    def test_align_single_source(self, sample_panel):
        result = align_panel(
            {"wb": sample_panel},
            countries=["tw", "jp"],
            year_range=range(2000, 2011),
        )
        assert not result.empty
        assert "country" in result.columns
        assert "year" in result.columns

    def test_align_filters_countries(self, sample_panel):
        result = align_panel(
            {"wb": sample_panel},
            countries=["tw"],
            year_range=range(2000, 2011),
        )
        assert (result["country"] == "tw").all()

    def test_align_empty_input(self):
        result = align_panel({}, [], range(2000, 2005))
        assert isinstance(result, pd.DataFrame)


class TestImputeMissing:
    def test_linear_imputation(self, panel_with_missing):
        result = impute_missing(panel_with_missing, method="linear")
        assert result["fixed_subs_value"].isnull().sum() == 0

    def test_ffill_imputation(self, panel_with_missing):
        result = impute_missing(panel_with_missing, method="ffill")
        assert result["fixed_subs_value"].isnull().sum() == 0

    def test_max_gap_respected(self, panel_with_missing):
        gap_panel = pd.DataFrame({
            "country": ["tw", "tw", "tw", "tw", "tw"],
            "year": [2000, 2001, 2002, 2003, 2004],
            "fixed_subs_value": [55.0, np.nan, np.nan, np.nan, 50.0],
        })
        result = impute_missing(gap_panel, method="linear", max_gap=2)
        assert result["fixed_subs_value"].isnull().sum() > 0


class TestAddPstnPhaseout:
    def test_phaseout_added(self, sample_panel):
        switchoff = {"tw": 2010, "jp": 2020}
        result = add_pstn_phaseout_feature(sample_panel, switchoff)
        assert "has_pstn_phaseout" in result.columns
        tw_2000 = result[(result["country"] == "tw") & (result["year"] == 2000)]
        assert tw_2000["has_pstn_phaseout"].iloc[0] == 0

    def test_phaseout_after_date(self, sample_panel):
        switchoff = {"tw": 2005}
        result = add_pstn_phaseout_feature(sample_panel, switchoff)
        tw_2010 = result[(result["country"] == "tw") & (result["year"] == 2010)]
        assert tw_2010["has_pstn_phaseout"].iloc[0] == 1

    def test_no_date_country(self, sample_panel):
        switchoff = {"tw": None}
        result = add_pstn_phaseout_feature(sample_panel, switchoff)
        assert result["has_pstn_phaseout"].sum() == 0


class TestAddDerivedFeatures:
    def test_yoy_added(self, sample_panel):
        result = add_derived_features(sample_panel)
        assert "fixed_subs_value_yoy" in result.columns

    def test_ma3_added(self, sample_panel):
        result = add_derived_features(sample_panel)
        assert "fixed_subs_value_ma3" in result.columns


class TestBuildProductLifetime:
    def test_build_lifetime_table(self, sample_panel):
        result = build_product_lifetime_table(
            sample_panel,
            product_intro_year=2000,
            penetration_col="fixed_subs_value",
        )
        assert "country" in result.columns
        assert "market_lifetime" in result.columns
        assert "product_dead" in result.columns

    def test_lifetime_values(self, sample_panel):
        result = build_product_lifetime_table(
            sample_panel,
            product_intro_year=2000,
            penetration_col="fixed_subs_value",
            death_threshold=0.05,
        )
        for _, row in result.iterrows():
            assert row["market_lifetime"] >= 0
            assert row["product_dead"] in (0, 1)


if __name__ == "__main__":
    pytest.main([__file__])
