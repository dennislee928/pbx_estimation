import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from typing import Optional

# --- Lifecycle classification logic ---

SOLUTION_GENERATIONS = {
    "tdm": (1980, 2010),
    "ip_pbx": (2005, 2018),
    "cloud": (2015, 2023),
    "ai_api": (2021, 2030),
}

CATEGORY_ORDER = ["cutting_edge", "mature_active", "most_used_current", "most_used_eol"]


def _normalize_tag(tag: str) -> str:
    return tag.strip().lower().replace(" ", "_").replace("-", "_")


def _generation(tags: list[str], vendor: str) -> str:
    gen_map = {
        "tdm": "tdm",
        "digital": "tdm",
        "analog": "tdm",
        "fxo": "tdm",
        "fxs": "tdm",
        "ip_pbx": "ip_pbx",
        "hybrid": "ip_pbx",
        "sip": "ip_pbx",
        "cloud": "cloud",
        "ucaaS": "cloud",
        "hosted": "cloud",
        "cpaas": "ai_api",
        "api": "ai_api",
        "webrtc": "ai_api",
        "ai": "ai_api",
        "webhook": "ai_api",
    }
    for t in tags:
        if t in gen_map:
            return gen_map[t]
    for v_part in vendor.lower().split():
        if v_part in gen_map:
            return gen_map[v_part]
    return "ip_pbx"


def _classify_eol(
    eol_status: str | None, eol_year: int | None, current_year: int = 2026
) -> bool:
    if eol_status and _normalize_tag(eol_status) in ("eol", "eos", "discontinued"):
        return True
    if eol_year is not None and eol_year <= current_year:
        return True
    return False


def _sample_market_share_trend(vendor: str, tags: list[str]) -> str:
    declining_keywords = ["panasonic", "toshiba", "avaya", "nec", "mitsubishi", "siemens"]
    growing_keywords = ["zoom", "teams", "ringcentral", "evox", "twilio", "3cx", "8x8"]
    for v in declining_keywords:
        if v in vendor.lower():
            return "declining"
    for v in growing_keywords:
        if v in vendor.lower():
            return "growing"
    if "cloud" in tags or "api" in tags or "ucaaS" in tags:
        return "growing"
    if "tdm" in tags or "analog" in tags:
        return "declining"
    return "stable"


def classify_solution(
    name: str,
    vendor: str,
    tags: list[str] | None = None,
    eol_status: str | None = None,
    eol_year: int | None = None,
) -> str:
    tags = [_normalize_tag(t) for t in (tags or [])]
    gen = _generation(tags, vendor)
    is_eol = _classify_eol(eol_status, eol_year)
    trend = _sample_market_share_trend(vendor, tags)

    if is_eol:
        return "most_used_eol"
    if gen == "ai_api" or (gen == "cloud" and trend == "growing"):
        return "cutting_edge"
    if gen == "cloud" or (gen == "ip_pbx" and trend == "stable"):
        if trend == "growing":
            return "cutting_edge"
        return "mature_active"
    if gen == "ip_pbx" and trend in ("stable", "declining"):
        return "most_used_current"
    if gen == "tdm" and not is_eol:
        return "most_used_current"
    return "mature_active"


# --- Registry loader ---

def load_registry(path: str = "data/solutions_registry.yaml") -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with open(p) as f:
        data = yaml.safe_load(f)
    solutions = []
    for continent, countries in data.items():
        for country_code, country_data in countries.items():
            country_code = str(country_code)
            for cat in CATEGORY_ORDER:
                for sol in country_data.get(cat, []):
                    sol["continent"] = continent
                    sol["country_code"] = country_code
                    sol["lifecycle_category"] = cat
                    solutions.append(sol)
    return solutions


# --- Analysis engine ---


def analyze_registry(
    registry_path: str = "data/solutions_registry.yaml",
    output_path: Optional[str] = "data/processed/solution_registry.csv",
) -> pd.DataFrame:
    solutions = load_registry(registry_path)
    rows = []
    for sol in solutions:
        tags = sol.get("tags", [])
        predicted = classify_solution(
            name=sol.get("name", ""),
            vendor=sol.get("vendor", ""),
            tags=tags,
            eol_status=sol.get("eol_status"),
            eol_year=sol.get("eol_year"),
        )
        rows.append(
            {
                "continent": sol.get("continent", ""),
                "country_code": sol.get("country_code", ""),
                "name": sol.get("name", ""),
                "vendor": sol.get("vendor", ""),
                "lifecycle_assigned": predicted,
                "lifecycle_original": sol.get("lifecycle_category", ""),
                "eol_status": sol.get("eol_status", ""),
                "eol_year": sol.get("eol_year"),
                "generation": _generation(tags, sol.get("vendor", "")),
                "tags": ", ".join(tags),
                "description": sol.get("description", ""),
                "pros": "; ".join(sol.get("pros", [])),
                "cons": "; ".join(sol.get("cons", [])),
                "typical_customers": sol.get("typical_customers", ""),
            }
        )
    df = pd.DataFrame(rows)
    if output_path and len(df):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
    return df


# --- Summary statistics ---


def summarize_registry(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["continent", "lifecycle_assigned"])
        .agg(count=("name", "count"), vendors=("vendor", lambda x: ", ".join(sorted(set(x)))))
        .reset_index()
    )
    return summary


def summary_by_country(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["continent", "country_code", "lifecycle_assigned"])
        .agg(count=("name", "count"))
        .reset_index()
    )
