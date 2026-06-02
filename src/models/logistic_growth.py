"""Logistic Growth Model (S-Curve) for market trend prediction.

Fits: P(t) = K / (1 + exp(-r * (t - t0)))
Uses scipy.optimize.curve_fit per country.
"""

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import seaborn as sns


def logistic(t: np.ndarray, K: float, r: float, t0: float) -> np.ndarray:
    """Logistic growth function (S-Curve)."""
    return K / (1.0 + np.exp(-r * (t - t0)))


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
    """Fit logistic model for a single country.

    Args:
        years: Array of year values.
        penetration: Array of penetration values.
        death_threshold: Fraction of K below which the market is "dead".
        p0: Initial guess (K, r, t0).
        bounds: Parameter bounds.

    Returns:
        dict with keys: K, r, t0, death_year, r_squared, fitted, rmse
    """
    valid = ~(np.isnan(penetration) | (penetration < 0))
    y = years[valid].astype(float)
    p = penetration[valid].astype(float)

    if len(y) < 4:
        return {
            "K": np.nan, "r": np.nan, "t0": np.nan,
            "death_year": np.nan, "r_squared": np.nan,
            "fitted": None, "rmse": np.nan,
            "converged": False,
            "death_threshold": death_threshold,
        }

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
        return {
            "K": np.nan, "r": np.nan, "t0": np.nan,
            "death_year": np.nan, "r_squared": np.nan,
            "fitted": None, "rmse": np.nan,
            "converged": False,
            "death_threshold": death_threshold,
        }

    death_year = np.nan
    # A "death year" only makes sense for a declining market (r < 0): the curve
    # falls below death_threshold * K at some point in the future. For a growing
    # market (r >= 0) the curve never declines, so death_year stays NaN instead
    # of resolving to a nonsensical year in the past.
    if K_fit > 0 and r_fit < 0 and 0.0 < death_threshold < 1.0:
        death_val = death_threshold * K_fit
        t_death = t0_fit - np.log(K_fit / death_val - 1) / r_fit
        if t_death > 1900:
            death_year = t_death

    return {
        "K": K_fit,
        "r": r_fit,
        "t0": t0_fit,
        "death_year": death_year,
        "r_squared": r_sq,
        "fitted": fitted,
        "rmse": rmse,
        "converged": True,
        "death_threshold": death_threshold,
    }


def fit_all_countries(
    panel: pd.DataFrame,
    penetration_col: str = "fixed_subs_value",
    death_threshold: float = 0.05,
    year_col: str = "year",
    country_col: str = "country",
) -> pd.DataFrame:
    """Fit logistic model for all countries in panel.

    Returns DataFrame with one row per country and columns:
    country, K, r, t0, death_year, r_squared, rmse
    """
    results = []
    for country in panel[country_col].unique():
        ctry = panel[panel[country_col] == country].sort_values(year_col)
        years = ctry[year_col].values
        penetration = ctry[penetration_col].values
        result = fit_country(years, penetration)
        result["country"] = country
        result["death_threshold"] = death_threshold
        results.append(result)

    return pd.DataFrame(results)


def predict_years(
    params: dict,
    years: np.ndarray,
) -> np.ndarray:
    """Generate predicted penetration values given fitted parameters."""
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
    summary = results_df[
        ["country", "K", "r", "t0", "death_year", "r_squared", "rmse", "converged"]
    ].copy()
    summary["death_year"] = summary["death_year"].round(0).astype("Int64")
    summary["death_threshold"] = results_df["death_threshold"]
    summary["K"] = summary["K"].round(2)
    summary["r"] = summary["r"].round(4)
    summary["t0"] = summary["t0"].round(1)
    summary["r_squared"] = summary["r_squared"].round(3)
    summary["rmse"] = summary["rmse"].round(3)
    return summary
