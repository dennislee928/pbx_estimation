"""Logistic Growth / Decline Model (S-Curve) for market trend prediction.

Two distinct concepts are modelled separately so they stop being conflated:

* **Growth S-curve** ``P(t) = K / (1 + exp(-r (t - t0)))`` with ``r > 0`` —
  describes the *adoption* phase. Its natural milestone is the
  ``saturation_year`` (when penetration reaches ``(1 - threshold) * K``).
* **Decline S-curve** ``P(t) = K / (1 + exp(+r (t - t0)))`` with ``r > 0`` —
  fitted on the *post-peak* segment only. Its milestone is the
  ``death_year`` (when penetration falls below ``threshold * peak``).

Historically fixed-line penetration *rose then fell*. The old code derived a
"death year" from the growth crossing (a low-adoption point on the way up),
which made notebook 03 disagree with notebook 04. ``death_year`` is now always
taken from the decline fit, so the two notebooks reconcile.
"""

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import seaborn as sns


def logistic(t: np.ndarray, K: float, r: float, t0: float) -> np.ndarray:
    """Logistic growth function (S-Curve). r > 0 grows, r < 0 declines."""
    return K / (1.0 + np.exp(-r * (t - t0)))


def logistic_decline(t: np.ndarray, K: float, r: float, t0: float) -> np.ndarray:
    """Logistic decline function. r > 0 means a falling S-curve."""
    return K / (1.0 + np.exp(r * (t - t0)))


def _empty_result(death_threshold: float, warning: str) -> dict:
    return {
        "K": np.nan, "r": np.nan, "t0": np.nan,
        "death_year": np.nan, "saturation_year": np.nan,
        "peak_year": np.nan, "peak_value": np.nan, "phase": "unknown",
        "r_squared": np.nan, "fitted": None, "rmse": np.nan,
        "n_points": 0, "decline_r": np.nan,
        "converged": False, "fit_warning": warning,
        "death_threshold": death_threshold,
    }


def _classify_phase(years: np.ndarray, values: np.ndarray, peak_idx: int) -> str:
    """Label the series as growing / declining / flat based on the peak position."""
    n = len(values)
    peak_val = values[peak_idx]
    last_val = values[-1]
    rel_drop = (peak_val - last_val) / peak_val if peak_val > 0 else 0.0
    # Peak in the last point and still near the top => still growing/plateau.
    if peak_idx >= n - 2 and rel_drop < 0.05:
        return "growing"
    if rel_drop >= 0.05:
        return "declining"
    return "flat"


def _fit_decline(years: np.ndarray, values: np.ndarray, peak_idx: int,
                 peak_value: float, death_threshold: float) -> tuple:
    """Fit the post-peak decline; return (decline_r, t0, death_year) or NaNs."""
    yd = years[peak_idx:].astype(float)
    pd_ = values[peak_idx:].astype(float)
    if len(yd) < 4:
        return np.nan, np.nan, np.nan
    p0 = (peak_value, 0.3, float(np.median(yd)))
    bounds = ((peak_value * 0.5, 0.0, yd.min() - 5.0),
              (peak_value * 1.5, 2.0, yd.max() + 50.0))
    try:
        popt, _ = curve_fit(logistic_decline, yd, pd_, p0=p0, bounds=bounds, maxfev=10000)
    except (RuntimeError, ValueError):
        return np.nan, np.nan, np.nan
    K_d, r_d, t0_d = popt
    death_year = np.nan
    death_val = death_threshold * peak_value
    if K_d > 0 and r_d > 0 and 0.0 < death_val < K_d:
        t_death = t0_d + np.log(K_d / death_val - 1.0) / r_d
        if np.isfinite(t_death) and t_death > 1900:
            death_year = t_death
    return r_d, t0_d, death_year


def fit_country(
    years: np.ndarray,
    penetration: np.ndarray,
    death_threshold: float = 0.05,
    p0: tuple[float, float, float] = (50.0, 0.3, 2010.0),
    bounds: tuple = (
        (0.0, -1.0, 1960.0),
        (np.inf, 1.0, 2050.0),
    ),
) -> dict:
    """Fit a growth S-curve and (if the market has peaked) a decline S-curve.

    Returns a dict with growth params (K, r, t0, r_squared, rmse), the observed
    peak (peak_year, peak_value), a phase label, ``saturation_year`` (growth
    milestone) and ``death_year`` (decline milestone, NaN unless a real
    post-peak decline with >=4 points is present).
    """
    valid = ~(np.isnan(penetration) | (penetration < 0))
    y = years[valid].astype(float)
    p = penetration[valid].astype(float)

    if len(y) < 4:
        return _empty_result(death_threshold, "fewer than 4 valid observations")

    order = np.argsort(y)
    y, p = y[order], p[order]

    try:
        popt, _ = curve_fit(logistic, y, p, p0=p0, bounds=bounds, maxfev=10000)
        K_fit, r_fit, t0_fit = popt
        fitted = logistic(y, *popt)
        residuals = p - fitted
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((p - np.mean(p)) ** 2)
        r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        rmse = np.sqrt(np.mean(residuals ** 2))
    except (RuntimeError, ValueError):
        return _empty_result(death_threshold, "growth curve_fit did not converge")

    peak_idx = int(np.argmax(p))
    peak_year = float(y[peak_idx])
    peak_value = float(p[peak_idx])
    phase = _classify_phase(y, p, peak_idx)

    # Saturation milestone (growth concept): time to reach (1 - thr) * K.
    saturation_year = np.nan
    if K_fit > 0 and r_fit > 0 and 0.0 < death_threshold < 1.0:
        sat_val = (1.0 - death_threshold) * K_fit
        t_sat = t0_fit - np.log(K_fit / sat_val - 1.0) / r_fit
        if np.isfinite(t_sat) and t_sat > 1900:
            saturation_year = t_sat

    # Death milestone (decline concept): only meaningful once the market peaks.
    decline_r, decline_t0, death_year = np.nan, np.nan, np.nan
    warning = ""
    if phase == "declining":
        decline_r, decline_t0, death_year = _fit_decline(
            y, p, peak_idx, peak_value, death_threshold
        )
        if np.isnan(death_year):
            warning = "decline detected but decline fit failed; death_year unavailable"
    else:
        warning = f"market phase is '{phase}'; death_year not applicable yet"

    return {
        "K": K_fit, "r": r_fit, "t0": t0_fit,
        "death_year": death_year, "saturation_year": saturation_year,
        "peak_year": peak_year, "peak_value": peak_value, "phase": phase,
        "r_squared": r_sq, "fitted": fitted, "rmse": rmse,
        "n_points": int(len(y)), "decline_r": decline_r,
        "converged": True, "fit_warning": warning,
        "death_threshold": death_threshold,
    }


def fit_all_countries(
    panel: pd.DataFrame,
    penetration_col: str = "fixed_subs_value",
    death_threshold: float = 0.05,
    year_col: str = "year",
    country_col: str = "country",
) -> pd.DataFrame:
    """Fit the growth+decline model for all countries in panel."""
    results = []
    for country in panel[country_col].unique():
        ctry = panel[panel[country_col] == country].sort_values(year_col)
        years = ctry[year_col].values
        penetration = ctry[penetration_col].values
        result = fit_country(years, penetration, death_threshold=death_threshold)
        result["country"] = country
        result["death_threshold"] = death_threshold
        results.append(result)

    return pd.DataFrame(results)


def predict_years(
    params: dict,
    years: np.ndarray,
) -> np.ndarray:
    """Generate predicted penetration values given fitted growth parameters."""
    K, r, t0 = params["K"], params["r"], params["t0"]
    if np.any(np.isnan([K, r, t0])):
        return np.full_like(years, np.nan, dtype=float)
    return logistic(years.astype(float), K, r, t0)


def plot_country_fit(
    country: str,
    years: np.ndarray,
    actual: np.ndarray,
    fitted: np.ndarray,
    death_year: float,
    K: float,
    r_squared: float,
    ax=None,
) -> None:
    """Plot actual vs fitted S-curve for a single country."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))

    valid = ~(np.isnan(actual) | (actual < 0))
    ax.scatter(years[valid], actual[valid], color="steelblue", s=30, label="Actual")
    ax.plot(years[valid], fitted[valid], color="crimson", linewidth=2, label="Fitted")

    if not np.isnan(death_year) and death_year > 1900:
        ax.axvline(death_year, color="gray", linestyle="--", alpha=0.7)
        ax.annotate(
            f"Death: {death_year:.0f}",
            xy=(death_year, ax.get_ylim()[1] * 0.9),
            fontsize=9, color="gray",
        )

    if not np.isnan(K):
        ax.axhline(K, color="green", linestyle=":", alpha=0.5)
        ax.annotate(f"K={K:.1f}", xy=(years[0], K), fontsize=9, color="green")

    ax.set_xlabel("Year")
    ax.set_ylabel("Penetration (per 100 people)")
    ax.set_title(f"{country} — Logistic Growth Fit\n$R^2$ = {r_squared:.3f}")
    ax.legend()
    ax.grid(True, alpha=0.3)


def plot_all_fits(
    results_df: pd.DataFrame,
    panel: pd.DataFrame,
    penetration_col: str = "fixed_subs_value",
    n_cols: int = 3,
) -> plt.Figure:
    """Plot S-curve fits for all countries in a grid."""
    countries = results_df["country"].tolist()
    n_rows = int(np.ceil(len(countries) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for i, country in enumerate(countries):
        row = results_df[results_df["country"] == country].iloc[0]
        ctry = panel[panel["country"] == country].sort_values("year")
        years = ctry["year"].values
        actual = ctry[penetration_col].values
        fitted = row["fitted"]
        if fitted is None:
            axes[i].text(0.5, 0.5, f"{country}\nNo fit", ha="center", va="center")
            axes[i].set_title(country)
            continue
        plot_country_fit(
            country, years, actual, fitted,
            row["death_year"], row["K"], row["r_squared"],
            ax=axes[i],
        )

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    return fig


def summarize_results(results_df: pd.DataFrame) -> pd.DataFrame:
    """Create a clean summary table of logistic regression results."""
    cols = [
        "country", "K", "r", "t0", "peak_year", "peak_value", "phase",
        "saturation_year", "death_year", "r_squared", "rmse", "n_points",
        "converged", "fit_warning",
    ]
    present = [c for c in cols if c in results_df.columns]
    summary = results_df[present].copy()
    for col in ("death_year", "saturation_year", "peak_year"):
        if col in summary.columns:
            summary[col] = summary[col].round(0).astype("Int64")
    summary["death_threshold"] = results_df["death_threshold"]
    if "K" in summary:
        summary["K"] = summary["K"].round(2)
    if "r" in summary:
        summary["r"] = summary["r"].round(4)
    if "t0" in summary:
        summary["t0"] = summary["t0"].round(1)
    if "peak_value" in summary:
        summary["peak_value"] = summary["peak_value"].round(2)
    if "r_squared" in summary:
        summary["r_squared"] = summary["r_squared"].round(3)
    if "rmse" in summary:
        summary["rmse"] = summary["rmse"].round(3)
    return summary
