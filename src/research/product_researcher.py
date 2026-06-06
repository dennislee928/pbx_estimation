import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from typing import Optional

from src.research.solution_crawler import discover_solution_catalog
from src.research.transport_taxonomy import classify_solution as classify_transport, serialize_for_csv

# --- Lifecycle classification logic ---

SOLUTION_GENERATIONS = {
    "tdm": (1980, 2010),
    "ip_pbx": (2005, 2018),
    "cloud": (2015, 2023),
    "ai_api": (2021, 2030),
}

CATEGORY_ORDER = ["cutting_edge", "mature_active", "most_used_current", "most_used_eol"]

VENDOR_RESOURCE_URLS = {
    "3cx": "https://www.3cx.com/",
    "8x8": "https://www.8x8.com/products/business-phone",
    "aircall": "https://aircall.io/",
    "alcatel-lucent": "https://www.al-enterprise.com/",
    "alibaba cloud": "https://www.alibabacloud.com/product/cloud-call-center",
    "asterisk": "https://www.asterisk.org/",
    "audiocodes": "https://www.audiocodes.com/",
    "auerswald": "https://www.auerswald.de/en/",
    "avaya": "https://www.avaya.com/",
    "bandwidth": "https://dev.bandwidth.com/docs/voice/",
    "bell canada": "https://business.bell.ca/",
    "bt": "https://business.bt.com/products/voice/cloud-voice/",
    "chunghwa telecom": "https://www.cht.com.tw/home/cht/business",
    "cisco": "https://www.webex.com/suite/cloud-calling.html",
    "clouditalia": "https://www.fastweb.it/business/",
    "comcast": "https://business.comcast.com/learn/voice/business-voiceedge",
    "deutsche telekom": "https://geschaeftskunden.telekom.de/internet-dsl/tarife/companyflex",
    "dialpad": "https://www.dialpad.com/products/business-phone-system/",
    "du": "https://www.du.ae/business",
    "e&": "https://www.etisalat.ae/en/business/",
    "emnify": "https://www.emnify.com/iot-esim",
    "ericsson": "https://www.ericssonlg-enterprise.com/",
    "ericsson-lg": "https://www.ericssonlg-enterprise.com/",
    "evox": "https://www.evoxglobal.com/",
    "exotel": "https://exotel.com/",
    "five9": "https://www.five9.com/products/call-center-software",
    "freeswitch": "https://freeswitch.org/",
    "gamma": "https://www.gamma.co.uk/products/horizon/",
    "google": "https://voice.google.com/",
    "huawei": "https://e.huawei.com/en/products/enterprise-networking/collaboration",
    "ihs": "https://www.ihstowers.com/",
    "infobip": "https://www.infobip.com/docs/voice-and-video",
    "intelbras": "https://www.intelbras.com/",
    "issabel": "https://www.issabel.org/",
    "kakao": "https://www.kakaowork.com/",
    "knowlarity": "https://www.knowlarity.com/",
    "kore": "https://www.korewireless.com/connectivity/omnisim",
    "kpn": "https://www.kpn.com/zakelijk.htm",
    "masmovil": "https://www.masmovil.es/empresas/",
    "matrix": "https://www.matrixcomsec.com/",
    "microsoft": "https://www.microsoft.com/en-us/microsoft-teams/microsoft-teams-phone",
    "mitel": "https://www.mitel.com/products/cloud-business-phone-systems",
    "mtn": "https://www.mtn.com/business/",
    "nec": "https://www.nec.com/en/global/solutions/enterprise-communication/",
    "nextiva": "https://www.nextiva.com/products/business-phone-service.html",
    "nfon": "https://www.nfon.com/en/products/cloudya",
    "ntt communications": "https://www.ntt.com/business/services/voice.html",
    "orange": "https://www.orange-business.com/en/solutions/communication-and-collaboration",
    "panasonic": "https://connect.panasonic.com/",
    "plivo": "https://www.plivo.com/docs/voice/",
    "poly": "https://www.hp.com/us-en/poly.html",
    "ringcentral": "https://www.ringcentral.com/office/features/business-phone-system/overview.html",
    "samsung": "https://www.samsung.com/business/",
    "sangoma": "https://www.sangoma.com/",
    "siemens": "https://unify.com/en/solutions",
    "singtel": "https://www.singtel.com/business",
    "sinch": "https://developers.sinch.com/docs/voice/",
    "soracom": "https://soracom.io/services/air/cellular/",
    "spark": "https://www.vox.co.za/",
    "starface": "https://www.starface.com/en/",
    "swisscom": "https://www.swisscom.ch/en/business.html",
    "telefonica": "https://www.telefonica.com/en/business-solutions/",
    "telavox": "https://telavox.com/",
    "telia": "https://www.telia.se/foretag",
    "telmex": "https://telmex.com/web/empresas",
    "telstra": "https://www.telstra.com.au/business-enterprise/products/voice-collaboration",
    "telnyx": "https://developers.telnyx.com/docs/voice",
    "telenor": "https://www.telenor.com/business/",
    "toshiba": "https://business.toshiba.com/",
    "twilio": "https://www.twilio.com/docs/voice",
    "voiceworks": "https://www.voiceworks.com/",
    "vonage": "https://developer.vonage.com/en/voice/voice-api/overview",
    "vonix": "https://www.vonix.com.br/",
    "vox telecom": "https://www.vox.co.za/",
    "whispir": "https://www.whispir.com/",
    "zoom": "https://www.zoom.com/en/products/voip-phone/",
    "zte": "https://www.zte.com.cn/global/",
}


def _normalize_tag(tag: str) -> str:
    return tag.strip().lower().replace(" ", "_").replace("-", "_")


def _resource_url(name: str, vendor: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    haystack = f"{vendor} {name}".lower()
    for key, url in VENDOR_RESOURCE_URLS.items():
        if key in haystack:
            return url
    return "https://www.g2.com/categories/voip"


def _recommended_terminals(tags: list[str], customers: str, lifecycle: str) -> str:
    text = " ".join(tags + [customers, lifecycle]).lower()
    if any(k in text for k in ["cpaas", "api", "iot", "esim"]):
        return "100-100,000+ API endpoints/devices"
    if any(k in text for k in ["enterprise", "government", "carrier"]):
        return "500-50,000 seats/devices"
    if any(k in text for k in ["contact_center", "call_center"]):
        return "25-5,000 agents"
    if any(k in text for k in ["cloud", "ucaas", "hosted"]):
        return "10-2,000 seats"
    if any(k in text for k in ["tdm", "analog", "hybrid"]):
        return "8-300 legacy extensions"
    return "5-500 seats"


def _cost_band(tags: list[str], lifecycle: str) -> str:
    text = " ".join(tags + [lifecycle]).lower()
    if "eol" in lifecycle or any(k in text for k in ["tdm", "analog"]):
        return "Low capex sunk cost; high maintenance/migration risk"
    if any(k in text for k in ["iot", "esim"]):
        return "Low-Medium: per SIM/device subscription"
    if any(k in text for k in ["cpaas", "api"]):
        return "Usage-based: per minute/API event"
    if any(k in text for k in ["enterprise", "contact_center", "call_center"]):
        return "Medium-High: per seat plus add-ons"
    if any(k in text for k in ["open_source"]):
        return "Low license cost; medium engineering/ops cost"
    return "Medium: monthly per-seat subscription"


def _industry_fit(tags: list[str], description: str, customers: str) -> str:
    text = " ".join(tags + [description, customers]).lower()
    industries = []
    if any(k in text for k in ["iot", "esim", "device", "sensor", "fleet"]):
        industries.extend(["IoT", "Utilities", "Logistics", "Manufacturing"])
    if any(k in text for k in ["health", "hospital", "clinic"]):
        industries.append("Healthcare")
    if any(k in text for k in ["government", "public sector", "education"]):
        industries.extend(["Government", "Education"])
    if any(k in text for k in ["contact", "call_center", "sales", "support", "crm"]):
        industries.extend(["Contact center", "Retail", "Financial services"])
    if any(k in text for k in ["hotel", "hospitality"]):
        industries.append("Hospitality")
    if any(k in text for k in ["cloud", "ucaas", "hosted", "enterprise"]):
        industries.extend(["Professional services", "Distributed offices"])
    if any(k in text for k in ["tdm", "analog", "legacy", "hybrid"]):
        industries.extend(["SMB retrofit", "Retail branches", "Legacy facilities"])
    if not industries:
        industries = ["SMB", "Enterprise", "Systems integrators"]
    return "; ".join(dict.fromkeys(industries))


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

def load_registry(
    path: str = "data/solutions_registry.yaml",
    include_discovered: bool = True,
) -> list[dict]:
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
    if include_discovered:
        solutions.extend(discover_solution_catalog())
    return solutions


# --- Analysis engine ---


def analyze_registry(
    registry_path: str = "data/solutions_registry.yaml",
    output_path: Optional[str] = "data/processed/solution_registry.csv",
    include_discovered: bool = True,
) -> pd.DataFrame:
    solutions = load_registry(registry_path, include_discovered=include_discovered)
    rows = []
    for sol in solutions:
        tags = sol.get("tags", [])
        transport = classify_transport(sol)
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
                "resource_url": _resource_url(
                    sol.get("name", ""),
                    sol.get("vendor", ""),
                    sol.get("resource_url") or sol.get("source_url"),
                ),
                "discovery_query": sol.get("discovery_query", ""),
                "recommended_terminals": sol.get("recommended_terminals")
                or _recommended_terminals(
                    [_normalize_tag(t) for t in tags],
                    sol.get("typical_customers", ""),
                    predicted,
                ),
                "cost_band": sol.get("cost_band")
                or _cost_band([_normalize_tag(t) for t in tags], predicted),
                "industry_fit": sol.get("industry_fit")
                or _industry_fit(
                    [_normalize_tag(t) for t in tags],
                    sol.get("description", ""),
                    sol.get("typical_customers", ""),
                ),
                **transport,
            }
        )
    df = pd.DataFrame(rows)
    if len(df):
        df = df.drop_duplicates(subset=["vendor", "name", "country_code"], keep="first").reset_index(drop=True)
    if output_path and len(df):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.map(serialize_for_csv).to_csv(output_path, index=False)
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
