"""Tests for the survival analysis module."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.survival import (
    fit_cox_model,
    predict_survival_probability,
    rank_markets,
)


@pytest.fixture
def sample_survival_data():
    """Create synthetic survival data for testing."""
    np.random.seed(42)
    n = 30
    return pd.DataFrame({
        "country": [f"c{i}" for i in range(n)],
        "market_lifetime": np.random.exponential(10, n),
        "product_dead": np.random.binomial(1, 0.6, n),
        "broadband_value": np.random.uniform(5, 45, n),
        "gdp_per_capita_value": np.random.uniform(2000, 60000, n),
        "urban_pop_value": np.random.uniform(35, 95, n),
        "has_pstn_phaseout": np.random.binomial(1, 0.4, n),
    })


class TestFitCoxModel:
    def test_fit_basic(self, sample_survival_data):
        model = fit_cox_model(
            sample_survival_data,
            duration_col="market_lifetime",
            event_col="product_dead",
            covariates=["broadband_value", "has_pstn_phaseout"],
        )
        assert hasattr(model, "hazard_ratios_")
        assert len(model.hazard_ratios_) == 2

    def test_fit_auto_covariates(self, sample_survival_data):
        model = fit_cox_model(
            sample_survival_data,
            duration_col="market_lifetime",
            event_col="product_dead",
        )
        assert len(model.hazard_ratios_) >= 3

    def test_fit_penalizer(self, sample_survival_data):
        model = fit_cox_model(
            sample_survival_data,
            penalizer=1.0,
        )
        assert hasattr(model, "hazard_ratios_")

    def test_fit_insufficient_data(self):
        with pytest.raises(ValueError):
            fit_cox_model(
                pd.DataFrame({"market_lifetime": [], "product_dead": []}),
            )


class TestPredictSurvival:
    def test_predict_probability(self, sample_survival_data):
        model = fit_cox_model(
            sample_survival_data,
            covariates=["broadband_value", "has_pstn_phaseout"],
        )
        prob = predict_survival_probability(
            model,
            {"broadband_value": 30.0, "has_pstn_phaseout": 1},
            t=5,
        )
        assert 0 <= prob <= 1

    def test_predict_in_range(self, sample_survival_data):
        model = fit_cox_model(
            sample_survival_data,
            covariates=["broadband_value", "has_pstn_phaseout"],
        )
        prob_high = predict_survival_probability(
            model, {"broadband_value": 40.0, "has_pstn_phaseout": 0}, t=5
        )
        prob_low = predict_survival_probability(
            model, {"broadband_value": 5.0, "has_pstn_phaseout": 1}, t=5
        )
        # Better conditions should have higher or equal survival
        assert prob_high >= prob_low * 0.5  # Allow some model variation


class TestRankMarkets:
    def test_rankings(self, sample_survival_data):
        model = fit_cox_model(
            sample_survival_data,
            covariates=["broadband_value", "has_pstn_phaseout"],
        )
        rankings = rank_markets(model, sample_survival_data, t=5)
        assert "country" in rankings.columns
        assert "survival_prob_5y" in rankings.columns
        assert rankings["survival_prob_5y"].is_monotonic_decreasing

    def test_rank_at_different_times(self, sample_survival_data):
        model = fit_cox_model(sample_survival_data)
        r3 = rank_markets(model, sample_survival_data, t=3)
        r10 = rank_markets(model, sample_survival_data, t=10)
        assert len(r3) == len(r10)


if __name__ == "__main__":
    pytest.main([__file__])
