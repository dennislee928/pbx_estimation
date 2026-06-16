"""Fetch supplementary public data sources: ITU, UK Parliament, CEPT, NCC Taiwan."""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Optional
import pandas as pd
import requests

USER_AGENT = (
    "PBXEstimation/1.0 (+https://github.com/dennis-lee/pbx_estimation; research bot)"
)

ISO2_TO_ISO3 = {
    "tw": "TWN",
    "jp": "JPN",
    "kr": "KOR",
    "cn": "CHN",
    "in": "IND",
    "gb": "GBR",
    "de": "DEU",
    "fr": "FRA",
    "se": "SWE",
    "it": "ITA",
    "us": "USA",
    "ca": "CAN",
    "br": "BRA",
    "nl": "NLD",
    "ee": "EST",
    "no": "NOR",
    "ch": "CHE",
    "es": "ESP",
    "mt": "MLT",
    "dk": "DNK",
    "lu": "LUX",
    "pt": "PRT",
    "be": "BEL",
}

ISO3_TO_ISO2 = {v: k for k, v in ISO2_TO_ISO3.items()}

UK_SWITCHOFF_PATTERNS = (
    re.compile(r"\b(?:by|before|in)\s+January\s+2027\b", re.I),
    re.compile(r"\bJanuary\s+2027\b", re.I),
    re.compile(r"\b31\s+January\s+2027\b", re.I),
)

CEPT_COUNTRY_PATTERNS = {
    "de": re.compile(r"\bGermany\b.{0,200}?\b(20\d{2})\b", re.I | re.S),
    "gb": re.compile(r"\bUnited Kingdom\b.{0,200}?\b(20\d{2})\b", re.I | re.S),
    "fr": re.compile(r"\bFrance\b.{0,200}?\b(20\d{2})\b", re.I | re.S),
    "nl": re.compile(r"\bNetherlands\b.{0,200}?\b(20\d{2})\b", re.I | re.S),
    "it": re.compile(r"\bItaly\b.{0,200}?\b(20\d{2})\b", re.I | re.S),
    "es": re.compile(r"\bSpain\b.{0,200}?\b(20\d{2})\b", re.I | re.S),
    "se": re.compile(r"\bSweden\b.{0,200}?\b(20\d{2})\b", re.I | re.S),
    "ch": re.compile(r"\bSwitzerland\b.{0,200}?\b(20\d{2})\b", re.I | re.S),
}


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8",
        }
    )
    return session


def _get(url: str, timeout: int = 60, **kwargs: Any) -> requests.Response:
    return _session().get(url, timeout=timeout, **kwargs)


def _download_itu_indicator(indicator_id: int, timeout: int = 120) -> pd.DataFrame:
    url = f"https://api.datahub.itu.int/v2/data/download/byid/{indicator_id}/iscollection/false"
    response = _get(url, timeout=timeout)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        csv_name = archive.namelist()[0]
        return pd.read_csv(io.BytesIO(archive.read(csv_name)))


def _normalize_itu_frame(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["country", "year", value_col])

    working = df.copy()
    working["entityIso"] = working["entityIso"].astype(str).str.upper()
    working["dataYear"] = pd.to_numeric(working["dataYear"], errors="coerce")
    working["dataValue"] = pd.to_numeric(working["dataValue"], errors="coerce")
    working["country"] = working["entityIso"].map(ISO3_TO_ISO2)
    working = working.dropna(subset=["country", "dataYear", "dataValue"])
    working["year"] = working["dataYear"].astype(int)
    return working[["country", "year", "dataValue"]].rename(columns={"dataValue": value_col})


def fetch_itu_data(
    config: dict,
    countries: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Fetch ITU DataHub indicators and return a country-year panel."""
    cfg = config["data"]["itu"]
    indicators: dict[str, int] = cfg["indicators"]
    start_year = int(cfg.get("start_year", 2000))
    end_year = int(cfg.get("end_year", 2025))

    if countries is None:
        countries = list(ISO2_TO_ISO3.keys())

    merged: Optional[pd.DataFrame] = None
    for name, indicator_id in indicators.items():
        try:
            raw = _download_itu_indicator(int(indicator_id))
            frame = _normalize_itu_frame(raw, f"itu_{name}_value")
        except Exception:
            frame = pd.DataFrame(columns=["country", "year", f"itu_{name}_value"])

        if merged is None:
            merged = frame
        else:
            merged = merged.merge(frame, on=["country", "year"], how="outer")

    if merged is None or merged.empty:
        return pd.DataFrame(columns=["country", "year"])

    merged = merged[merged["country"].isin(countries)]
    merged = merged[(merged["year"] >= start_year) & (merged["year"] <= end_year)]
    return merged.sort_values(["country", "year"]).reset_index(drop=True)


def _extract_uk_switchoff_from_text(text: str) -> Optional[int]:
    for pattern in UK_SWITCHOFF_PATTERNS:
        if pattern.search(text):
            return 2027
    if re.search(r"\b2027\b", text) and re.search(r"\bPSTN\b", text, re.I):
        return 2027
    return None


def fetch_uk_pstn_switchoff(config: dict) -> dict[str, Any]:
    """Scrape UK Parliament briefing for PSTN switch-off date."""
    cfg = config["data"]["uk_parliament"]
    country_code = cfg.get("country_code", "gb")
    result: dict[str, Any] = {
        "source": "UK House of Commons Library",
        "country_code": country_code,
        "switchoff_year": None,
        "fetch_status": "failed",
        "urls_tried": [],
        "excerpt": "",
    }

    urls = [cfg.get("pdf_url"), cfg.get("briefing_url")]
    text_chunks: list[str] = []

    for url in urls:
        if not url:
            continue
        result["urls_tried"].append(url)
        try:
            response = _get(url, timeout=60)
            content_type = response.headers.get("content-type", "").lower()
            if response.ok and "pdf" in content_type:
                from PyPDF2 import PdfReader

                reader = PdfReader(io.BytesIO(response.content))
                text = "".join(page.extract_text() or "" for page in reader.pages)
                text_chunks.append(text)
            elif response.ok:
                text_chunks.append(response.text)
        except Exception:
            continue

    combined = "\n".join(text_chunks)
    year = _extract_uk_switchoff_from_text(combined)
    if year is not None:
        result["switchoff_year"] = year
        result["fetch_status"] = "success"
        match = re.search(r".{0,120}January 2027.{0,120}", combined, re.I | re.S)
        result["excerpt"] = (match.group(0) if match else combined[:400]).strip()
    else:
        fallback = config["data"]["pstn_switchoff"].get(country_code)
        if fallback not in (None, "~"):
            result["switchoff_year"] = int(fallback)
            result["fetch_status"] = "fallback_config"
            result["excerpt"] = "Used config.yaml fallback because live fetch did not return parseable text."

    return result


def fetch_cept_migration_status(config: dict) -> dict[str, Any]:
    """Extract migration mentions from CEPT ECC Report 265 PDF."""
    cfg = config["data"]["cept"]
    url = cfg["report_url"]
    result: dict[str, Any] = {
        "source": cfg.get("report_title", "CEPT ECC Report"),
        "url": url,
        "fetch_status": "failed",
        "countries": [],
        "excerpt": "",
    }

    try:
        response = _get(url, timeout=90)
        response.raise_for_status()
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(response.content))
        text = "".join(page.extract_text() or "" for page in reader.pages)
        result["fetch_status"] = "success"
        result["excerpt"] = text[:500].strip()

        for country_code, pattern in CEPT_COUNTRY_PATTERNS.items():
            match = pattern.search(text)
            if not match:
                continue
            year = int(match.group(1))
            if 2000 < year < 2100:
                result["countries"].append(
                    {
                        "country_code": country_code,
                        "mentioned_year": year,
                        "context": match.group(0).replace("\n", " ")[:240],
                    }
                )
    except Exception as error:
        result["error"] = str(error)

    return result


def _parse_roc_period(period: str) -> tuple[int, int]:
    period = str(period).strip()
    if len(period) < 5:
        raise ValueError(f"Invalid ROC period: {period}")
    roc_year = int(period[:3])
    month = int(period[3:5])
    return roc_year + 1911, month


def _parse_taiwan_number(value: str) -> float:
    digits = re.sub(r"[^\d.]", "", str(value))
    return float(digits) if digits else 0.0


def fetch_ncc_taiwan_telecom(config: dict) -> pd.DataFrame:
    """Fetch Taiwan telecom statistics from NCC API and MODA open data."""
    cfg = config["data"]["ncc"]
    country_code = cfg.get("country_code", "tw")
    rows: list[dict[str, Any]] = []

    mobile_url = cfg["mobile_stats_csv"]
    try:
        response = _get(mobile_url, timeout=60)
        response.raise_for_status()
        mobile = pd.read_csv(io.StringIO(response.content.decode("utf-8-sig")))
        mobile.columns = [str(c).strip() for c in mobile.columns]
        period_col = mobile.columns[0]
        users_col = mobile.columns[-1]
        operator_col = mobile.columns[2]
        totals = mobile[mobile[operator_col].astype(str).str.contains("總計", na=False)].copy()
        for _, record in totals.iterrows():
            year, month = _parse_roc_period(record[period_col])
            rows.append(
                {
                    "country": country_code,
                    "year": year,
                    "month": month,
                    "metric": "mobile_subscribers",
                    "value": _parse_taiwan_number(record[users_col]),
                    "source": "ncc_mobile_stats_csv",
                }
            )
    except Exception:
        pass

    numbers_url = cfg["telecom_numbers_csv"]
    try:
        response = _get(numbers_url, timeout=60)
        response.raise_for_status()
        numbers = pd.read_csv(io.StringIO(response.content.decode("utf-8-sig")))
        numbers.columns = [str(c).strip() for c in numbers.columns]
        landline = numbers[
            numbers.iloc[:, 1].astype(str).str.contains("市話", na=False)
        ]
        if not landline.empty:
            allocated = _parse_taiwan_number(landline.iloc[0, 3])
            rows.append(
                {
                    "country": country_code,
                    "year": pd.Timestamp.now().year,
                    "month": pd.Timestamp.now().month,
                    "metric": "landline_numbers_allocated",
                    "value": allocated,
                    "source": "moda_telecom_numbers_csv",
                }
            )
    except Exception:
        pass

    if not rows:
        return pd.DataFrame(
            columns=["country", "year", "month", "metric", "value", "source"]
        )
    return pd.DataFrame(rows)


def merge_pstn_switchoff_dates(
    config: dict,
    berec_dates: dict[str, int],
    uk_result: dict[str, Any],
    cept_result: dict[str, Any],
) -> dict[str, Optional[int]]:
    """Merge config, BEREC, UK Parliament, and CEPT extracted dates."""
    raw = config["data"]["pstn_switchoff"]
    merged: dict[str, Optional[int]] = {}
    for country, value in raw.items():
        if value in (None, "~"):
            merged[country] = None
        else:
            merged[country] = int(value)

    for country, year in berec_dates.items():
        code = country.lower()
        if 2000 < year < 2100:
            merged[code] = year

    uk_year = uk_result.get("switchoff_year")
    if uk_year:
        merged[uk_result.get("country_code", "gb")] = int(uk_year)

    for item in cept_result.get("countries", []):
        code = item.get("country_code")
        year = item.get("mentioned_year")
        if code and year and merged.get(code) is None:
            merged[code] = int(year)

    return merged


def fetch_all_supplementary(
    config: dict,
    cache_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Run all supplementary fetchers and optionally cache raw outputs."""
    countries = []
    for region in config["countries"].values():
        for item in region:
            countries.extend(item.keys())

    itu = fetch_itu_data(config, countries=countries)
    uk = fetch_uk_pstn_switchoff(config)
    cept = fetch_cept_migration_status(config)
    ncc = fetch_ncc_taiwan_telecom(config)

    result = {
        "itu": itu,
        "uk_parliament": uk,
        "cept": cept,
        "ncc": ncc,
    }

    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        if not itu.empty:
            itu.to_csv(cache_dir / "itu_indicators.csv", index=False)
        if not ncc.empty:
            ncc.to_csv(cache_dir / "ncc_taiwan_telecom.csv", index=False)
        (cache_dir / "uk_parliament_pstn.json").write_text(
            json.dumps(uk, ensure_ascii=False, indent=2) + "\n"
        )
        (cache_dir / "cept_migration.json").write_text(
            json.dumps(cept, ensure_ascii=False, indent=2) + "\n"
        )

    return result


def ncc_to_annual_panel(ncc_df: pd.DataFrame) -> pd.DataFrame:
    """Convert NCC monthly mobile stats to annual country-year metrics."""
    if ncc_df.empty:
        return pd.DataFrame(columns=["country", "year", "ncc_mobile_subscribers_value"])

    mobile = ncc_df[ncc_df["metric"] == "mobile_subscribers"].copy()
    if mobile.empty:
        return pd.DataFrame(columns=["country", "year", "ncc_mobile_subscribers_value"])

    annual = (
        mobile.groupby(["country", "year"], as_index=False)["value"]
        .mean()
        .rename(columns={"value": "ncc_mobile_subscribers_value"})
    )
    return annual


def ncc_taiwan_legacy_decline_series(ncc_df: pd.DataFrame) -> pd.Series:
    """Extract Taiwan's real legacy-mobile (2G) decline as an annual series.

    World Bank has no Taiwan entry and the NCC feed carries no fixed-line series,
    so Taiwan is otherwise absent from the decline analysis. The NCC mobile feed
    does, however, contain a genuine *legacy-access sunset*: each month holds two
    sub-series (total mobile, which grows, and the legacy 2G base, which is the
    smaller value and declines steeply until Taiwan's 2G shutdown in 2017). We
    isolate that legacy series over 2012-2016 (the window before the source CSV
    format changes and the parse becomes unreliable). This is real, documented
    data and a faithful "legacy telecom access dying in Taiwan" signal.

    Returns an annual pd.Series indexed by year (values in raw subscriber counts),
    or an empty Series if the NCC data is unavailable.
    """
    if ncc_df.empty:
        return pd.Series(dtype=float)
    mobile = ncc_df[ncc_df["metric"] == "mobile_subscribers"].copy()
    if mobile.empty:
        return pd.Series(dtype=float)

    # Two rows per (year, month); the smaller is the declining legacy 2G base.
    mobile["_rank"] = mobile.groupby(["year", "month"])["value"].rank(method="first")
    legacy = mobile[(mobile["_rank"] == 1.0) & (mobile["year"] <= 2016)]
    if legacy.empty:
        return pd.Series(dtype=float)
    return legacy.groupby("year")["value"].mean().sort_index()


def taiwan_decline_projection_row(
    ncc_df: pd.DataFrame,
    horizon_years: list[int],
    death_threshold: float = 0.3,
) -> Optional[dict]:
    """Build a long-horizon projection row for Taiwan from real NCC 2G-decline data.

    Mirrors the per-market output of notebook 04's projection cell: a dict with
    ``market='TWN'`` and one entry per horizon year giving penetration as a % of
    Taiwan's historical legacy peak. Returns None if the decline cannot be fit.
    """
    from src.models.logistic_growth import _fit_decline, logistic_decline
    import numpy as np

    series = ncc_taiwan_legacy_decline_series(ncc_df)
    if len(series) < 4:
        return None

    years = series.index.values.astype(float)
    vals = series.values.astype(float)
    peak_idx = int(np.argmax(vals))
    peak_val = float(vals[peak_idx])
    if peak_val <= 0:
        return None

    decline_k, decline_r, decline_t0, _death = _fit_decline(
        years, vals, peak_idx, peak_val, death_threshold
    )
    if np.isnan(decline_k):
        return None

    row = {"market": "TWN"}
    for yr in horizon_years:
        pct = logistic_decline(np.array([float(yr)]), decline_k, decline_r, decline_t0)[0]
        row[f"{yr}"] = round(max(0.0, pct / peak_val * 100), 2)
    return row
