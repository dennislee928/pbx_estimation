"""Survival analysis module using Cox Proportional Hazards Model.

Uses lifelines.CoxPHFitter to estimate product survival probability
across different market conditions.
"""

import warnings

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional
from lifelines import CoxPHFitter


def fit_cox_model(
    data: pd.DataFrame,
    duration_col: str = "market_lifetime",
    event_col: str = "product_dead",
    covariates: Optional[list[str]] = None,
    penalizer: float = 0.1,
) -> CoxPHFitter:
    """Fit a Cox Proportional Hazards model.

    Args:
        data: DataFrame with duration, event, and covariate columns.
        duration_col: Column name for survival duration.
        event_col: Column name for event indicator (1=dead, 0=censored).
        covariates: List of covariate column names. If None, uses all
                    columns except duration_col, event_col, and 'country'.
        penalizer: Ridge regression penalizer to handle convergence.

    Returns:
        Fitted CoxPHFitter instance.
    """
    model_data = data.copy()

    if covariates is None:
        covariates = [
            c for c in model_data.columns
            if c not in (duration_col, event_col, "country", "peak_penetration")
        ]

    # Drop rows with missing values in any used column
    used_cols = [duration_col, event_col] + covariates
    model_data = model_data[used_cols].dropna()

    if model_data.empty:
        raise ValueError("No valid data after dropping missing values.")

    cph = CoxPHFitter(penalizer=penalizer)
    cph.fit(
        model_data,
        duration_col=duration_col,
        event_col=event_col,
    )
    cph.covariates_ = covariates
    return cph


def plot_survival_curves(
    model: CoxPHFitter,
    countries: list[str],
    data: pd.DataFrame,
    t_max: int = 20,
    ax=None,
) -> None:
    """Plot predicted survival curves for each country.

    Uses each country's actual covariate values from the data.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 6))

    covariate_cols = model.covariates_
    time_points = np.arange(0, t_max + 1)

    for country in countries:
        row = data[data["country"] == country]
        if row.empty:
            continue
        covs = row[covariate_cols].iloc[0].to_dict()
        for k, v in covs.items():
            if isinstance(v, (np.floating, float)):
                covs[k] = float(v)
            elif isinstance(v, (np.integer, int)):
                covs[k] = int(v)

        surv = model.predict_survival_function(
            pd.DataFrame([covs]), times=time_points
        )
        ax.step(
            time_points,
            surv.values.flatten() if hasattr(surv, "values") else surv.iloc[0],
            where="post",
            label=f"{country}",
        )

    ax.set_xlabel("Years since product introduction")
    ax.set_ylabel("Survival probability $S(t)$")
    ax.set_title("Product Survival Curves by Country")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.05)


def predict_survival_probability(
    model: CoxPHFitter,
    covariates: dict,
    t: int = 5,
) -> float:
    """Predict probability that product survives beyond t years.

    Args:
        model: Fitted CoxPHFitter
        covariates: Dict of covariate values for the scenario
        t: Number of years to survive

    Returns:
        Survival probability S(t)
    """
    # Guard against silent extrapolation beyond the fitted baseline timeline.
    # lifelines forward-fills the last baseline survival value for t past the
    # largest observed duration, which understates uncertainty — warn so callers
    # (and notebooks) treat far-horizon predictions as extrapolation.
    baseline = getattr(model, "baseline_survival_", None)
    if baseline is not None and len(baseline.index):
        max_t = float(baseline.index.max())
        if t > max_t:
            warnings.warn(
                f"predict_survival_probability: t={t} exceeds the fitted "
                f"baseline horizon ({max_t:.0f}); result is extrapolated.",
                stacklevel=2,
            )

    df = pd.DataFrame([covariates])
    surv = model.predict_survival_function(df, times=[t])
    return float(surv.iloc[0, 0] if hasattr(surv, "iloc") else surv.values[0, 0])


def rank_markets(
    model: CoxPHFitter,
    data: pd.DataFrame,
    t: int = 5,
) -> pd.DataFrame:
    """Rank countries by product survival probability at time t.

    Returns DataFrame sorted by survival probability (descending).
    """
    covariate_cols = model.covariates_
    rankings = []
    for _, row in data.iterrows():
        covs = {c: row[c] for c in covariate_cols}
        prob = predict_survival_probability(model, covs, t=t)
        rankings.append({
            "country": row["country"],
            f"survival_prob_{t}y": round(prob, 4),
            "market_lifetime": row.get("market_lifetime", np.nan),
        })

    result = pd.DataFrame(rankings)
    return result.sort_values(f"survival_prob_{t}y", ascending=False).reset_index(drop=True)


def plot_hazard_ratios(model: CoxPHFitter, ax=None) -> None:
    """Plot hazard ratios with 95% CIs for each covariate."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, max(4, len(model.covariates_) * 0.6)))

    hr = model.hazard_ratios_
    # confidence_intervals_ are on the coefficient (log-hazard) scale, while
    # hazard_ratios_ are exp(beta). Exponentiate the bounds so both live on the
    # same hazard-ratio scale before computing error bars.
    ci = np.exp(model.confidence_intervals_)
    cis = []
    for c in hr.index:
        if c in ci.index:
            cis.append((ci.loc[c, "95% lower-bound"], ci.loc[c, "95% upper-bound"]))
        else:
            cis.append((np.nan, np.nan))

    y_pos = range(len(hr))
    xerr_lower = [max(0, hr.values[i] - cis[i][0]) for i in range(len(hr))]
    xerr_upper = [max(0, cis[i][1] - hr.values[i]) for i in range(len(hr))]
    ax.errorbar(
        hr.values, y_pos,
        xerr=[xerr_lower, xerr_upper],
        fmt="o", capsize=5, color="steelblue",
    )
    ax.axvline(1.0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("Hazard Ratio (exp($\\beta$))")
    ax.set_ylabel("Covariate")
    ax.set_title("CoxPH Hazard Ratios")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(hr.index)
    ax.grid(True, alpha=0.3)
