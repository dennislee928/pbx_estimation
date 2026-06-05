"""Tests for the logistic growth model module."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.logistic_growth import (
    logistic,
    fit_country,
    fit_all_countries,
    predict_years,
    summarize_results,
)


class TestLogisticFunction:
    def test_logistic_shape(self):
        t = np.array([2000, 2005, 2010, 2015, 2020])
        result = logistic(t, K=50, r=0.3, t0=2010)
        assert len(result) == 5
        assert all(r >= 0 for r in result)
        assert all(r <= 50 for r in result)

    def test_logistic_inflection(self):
        t = np.array([2000, 2010, 2020])
        result = logistic(t, K=100, r=0.5, t0=2010)
        # At t=t0, P = K/2
        assert abs(result[1] - 50) < 1

    def test_logistic_empty_input(self):
        result = logistic(np.array([]), K=50, r=0.3, t0=2010)
        assert len(result) == 0


class TestFitCountry:
    def test_fit_perfect_s_curve(self):
        np.random.seed(42)
        years = np.arange(2000, 2025)
        true_K, true_r, true_t0 = 60, 0.25, 2008
        penetration = logistic(years, true_K, true_r, true_t0)
        penetration += np.random.normal(0, 0.5, len(years))

        result = fit_country(years, penetration)
        assert result["converged"]
        assert abs(result["K"] - true_K) < 10
        assert abs(result["r_squared"] - 1.0) < 0.1

    def test_fit_insufficient_data(self):
        years = np.array([2000, 2001])
        penetration = np.array([50, 49])
        result = fit_country(years, penetration)
        assert not result["converged"]

    def test_fit_with_nan(self):
        years = np.arange(2000, 2025)
        penetration = logistic(years, 50, 0.3, 2010)
        penetration[5:10] = np.nan
        result = fit_country(years, penetration)
        assert "converged" in result

    def test_growth_only_has_no_death_year(self):
        # A pure growth/saturating curve has not peaked-and-declined, so a
        # death_year must NOT be invented; a saturation_year should exist.
        years = np.arange(2000, 2030)
        penetration = logistic(years, 40, 0.2, 2010)
        result = fit_country(years, penetration)
        assert result["converged"]
        assert result["phase"] in ("growing", "flat")
        assert np.isnan(result.get("death_year", np.nan))
        assert not np.isnan(result.get("saturation_year", np.nan))

    def test_decline_death_year_in_decline_phase(self):
        # Rise-then-fall series: death_year must land in the declining phase
        # (after the observed peak), not on the way up.
        rise = np.array([5, 12, 25, 40, 52, 58, 60], dtype=float)
        fall = np.array([58, 50, 38, 25, 14, 7, 3], dtype=float)
        penetration = np.concatenate([rise, fall])
        years = np.arange(2000, 2000 + len(penetration), dtype=float)
        result = fit_country(years, penetration, death_threshold=0.05)
        assert result["converged"]
        assert result["phase"] == "declining"
        assert not np.isnan(result["death_year"])
        assert result["death_year"] >= result["peak_year"]


class TestFitAllCountries:
    def test_fit_all_countries(self):
        panel = pd.DataFrame({
            "country": ["tw", "tw", "tw", "jp", "jp", "jp"],
            "year": [2000, 2005, 2010, 2000, 2005, 2010],
            "fixed_subs_value": [55, 50, 40, 60, 55, 45],
        })
        results = fit_all_countries(panel)
        assert len(results) == 2  # two countries
        assert "country" in results.columns
        assert "K" in results.columns
        assert "r" in results.columns
        assert "t0" in results.columns

    def test_fit_all_death_threshold(self):
        panel = pd.DataFrame({
            "country": ["tw", "tw", "tw", "tw", "tw"],
            "year": [2000, 2005, 2010, 2015, 2020],
            "fixed_subs_value": [60, 50, 30, 10, 2],
        })
        results = fit_all_countries(panel, death_threshold=0.05)
        assert results.iloc[0]["death_threshold"] == 0.05


class TestPredictYears:
    def test_predict_years(self):
        params = {"K": 50, "r": 0.3, "t0": 2010}
        years = np.arange(2000, 2030)
        pred = predict_years(params, years)
        assert len(pred) == len(years)
        assert np.all(pred >= 0)

    def test_predict_years_nan_params(self):
        params = {"K": np.nan, "r": 0.3, "t0": 2010}
        years = np.arange(2000, 2030)
        pred = predict_years(params, years)
        assert np.all(np.isnan(pred))


class TestSummarizeResults:
    def test_summarize(self):
        df = pd.DataFrame({
            "country": ["tw"],
            "K": [50.123],
            "r": [0.3456],
            "t0": [2010.5],
            "death_year": [2025.0],
            "r_squared": [0.9876],
            "rmse": [1.234],
            "converged": [True],
            "death_threshold": [0.05],
        })
        summary = summarize_results(df)
        assert summary["K"].iloc[0] == 50.12


if __name__ == "__main__":
    pytest.main([__file__])
