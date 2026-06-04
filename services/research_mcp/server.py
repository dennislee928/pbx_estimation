from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urldefrag, urljoin, urlparse
from typing import Any, Callable, Iterable

# ----------------------------------------------------------------------------
# Optional heavy dependencies. The service degrades gracefully when a library
# is missing so the core CI/validation path never breaks.
# ----------------------------------------------------------------------------
try:  # pragma: no cover - import guard
    import httpx
except Exception:  # noqa: BLE001
    httpx = None  # type: ignore[assignment]

try:  # pragma: no cover
    import trafilatura
except Exception:  # noqa: BLE001
    trafilatura = None  # type: ignore[assignment]

try:  # pragma: no cover
    from bs4 import BeautifulSoup
except Exception:  # noqa: BLE001
    BeautifulSoup = None  # type: ignore[assignment]

try:  # pragma: no cover
    import feedparser
except Exception:  # noqa: BLE001
    feedparser = None  # type: ignore[assignment]


script_path = Path(__file__).resolve()
DEFAULT_WORKSPACE = script_path.parents[2] if len(script_path.parents) > 2 else Path.cwd()
WORKSPACE = Path(os.environ.get("PBX_WORKSPACE") or DEFAULT_WORKSPACE).resolve()

USER_AGENT = os.environ.get(
    "RESEARCH_MCP_USER_AGENT",
    "pbx-research-mcp/1.0 (+https://github.com/dennis-lee/pbx_estimation)",
)
HTTP_TIMEOUT = float(os.environ.get("RESEARCH_MCP_HTTP_TIMEOUT", "20"))
MAX_FETCH_BYTES = int(os.environ.get("RESEARCH_MCP_MAX_BYTES", str(3 * 1024 * 1024)))
MAX_CONCURRENCY = int(os.environ.get("RESEARCH_MCP_CONCURRENCY", "8"))


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=WORKSPACE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "ok": result.returncode == 0,
    }


# ----------------------------------------------------------------------------
# Data access helpers
# ----------------------------------------------------------------------------
def _load_json(relative: str, default: Any = None) -> Any:
    path = WORKSPACE / relative
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


DATASETS = {
    "awesome_list": "frontend/data/awesome_list.json",
    "solution_registry": "frontend/data/solution_registry.json",
    "crawler_discoveries": "frontend/data/crawler_discoveries.json",
    "crawler_seed_context": "frontend/data/crawler_seed_context.json",
    "crawler_taxonomy": "frontend/data/crawler_taxonomy.json",
    "research_sources": "frontend/data/research_sources.json",
}


def _dataset(name: str) -> Any:
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset '{name}'. Known: {sorted(DATASETS)}")
    return _load_json(DATASETS[name], default=[])


def _as_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


# ----------------------------------------------------------------------------
# Existing pipeline tools (preserved)
# ----------------------------------------------------------------------------
def generate_research_outputs() -> dict[str, Any]:
    result = _run([sys.executable, "scripts/generate_research_outputs.py"])
    validation = validate_research_outputs() if result["ok"] else {}
    return {"generation": result, "validation": validation}


def validate_research_outputs() -> dict[str, Any]:
    required = [
        "frontend/data/awesome_list.json",
        "frontend/data/solution_registry.json",
        "frontend/data/crawler_seed_context.json",
        "frontend/data/crawler_taxonomy.json",
        "reports/global_research_report_en.html",
        "reports/global_research_report_zh.html",
        "reports/index.html",
        "data/processed/awesome_list.csv",
        "data/processed/solution_registry.csv",
    ]
    missing = [path for path in required if not (WORKSPACE / path).exists()]
    alternatives = [] if missing else _load_json("frontend/data/awesome_list.json", [])
    solutions = [] if missing else _load_json("frontend/data/solution_registry.json", [])
    crawler_seed = {} if missing else _load_json("frontend/data/crawler_seed_context.json", {})
    categories = {row.get("category") for row in alternatives if isinstance(row, dict)}
    non_web = [row for row in alternatives if row.get("category") == "non_web"]
    rf_like = [
        row for row in non_web
        if any(token in str(row.get("medium", "")).lower() for token in ["radio", "wifi", "cellular", "satellite", "dect", "uwb", "lpwan", "near_field", "rfid", "nfc"])
    ]
    return {
        "ok": not missing and len(alternatives) > 0 and len(solutions) > 0 and {"web", "non_web"}.issubset(categories),
        "missing": missing,
        "alternative_count": len(alternatives),
        "solution_count": len(solutions),
        "non_web_count": len(non_web),
        "non_web_non_rf_count": len(non_web) - len(rf_like),
        "crawler_seed_known_alternative_count": crawler_seed.get("known_alternative_count") if isinstance(crawler_seed, dict) else None,
    }


def _tokens(value: str) -> list[str]:
    return [token for token in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split() if len(token) >= 2]


def _score(scene: str, row: dict[str, Any]) -> int:
    terms = _tokens(scene)
    text = " ".join(str(value).lower() for value in row.values())
    score = 0
    for term in terms:
        if term in text:
            score += 8
        if term in str(row.get("name", "")).lower():
            score += 12
        if term in str(row.get("use_case", "")).lower():
            score += 10
        if term in str(row.get("industry_fit", "")).lower():
            score += 8
    return score


def analyze_scene(scene: str, top_k: int = 8) -> dict[str, Any]:
    alternatives = _as_rows(_dataset("awesome_list"))
    solutions = _as_rows(_dataset("solution_registry"))

    def rank(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ranked = [
            {"name": row.get("name"), "score": _score(scene, row), "medium": row.get("medium"), "category": row.get("category"), "resource_url": row.get("resource_url", "")}
            for row in rows
        ]
        return [row for row in sorted(ranked, key=lambda item: (-item["score"], str(item["name"]))) if row["score"] > 0][:top_k]

    return {
        "scene": scene,
        "alternatives": rank(alternatives),
        "solutions": rank(solutions),
    }


# ----------------------------------------------------------------------------
# Web research: fetch / extract / crawl / feeds
# ----------------------------------------------------------------------------
def _require_httpx() -> None:
    if httpx is None:
        raise RuntimeError("httpx is not installed in this image; rebuild with services/research_mcp/requirements.txt")


def _client() -> "httpx.Client":
    _require_httpx()
    kwargs = {
        "headers": {"User-Agent": USER_AGENT, "Accept": "*/*"},
        "timeout": HTTP_TIMEOUT,
        "follow_redirects": True,
    }
    try:
        return httpx.Client(http2=True, **kwargs)
    except ImportError:
        # The optional 'h2' package isn't installed; fall back to HTTP/1.1.
        return httpx.Client(**kwargs)


def _extract_text(html: str, url: str) -> str:
    if trafilatura is not None:
        try:
            extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=True)
            if extracted:
                return extracted.strip()
        except Exception:  # noqa: BLE001
            pass
    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "noscript", "template"]):
                tag.decompose()
            text = soup.get_text(" ", strip=True)
            return re.sub(r"\s{2,}", " ", text)
        except Exception:  # noqa: BLE001
            pass
    return re.sub(r"<[^>]+>", " ", html)


def _parse_html(html: str, base_url: str) -> dict[str, Any]:
    title = ""
    description = ""
    links: list[str] = []
    headings: list[str] = []
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "lxml")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = tag.get_text(" ", strip=True)
            if text:
                headings.append(text)
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            absolute = urldefrag(urljoin(base_url, anchor["href"]))[0]
            if absolute.startswith(("http://", "https://")) and absolute not in seen:
                seen.add(absolute)
                links.append(absolute)
    else:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if title_match:
            title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        for match in re.findall(r'href=["\']([^"\']+)["\']', html, re.I):
            absolute = urldefrag(urljoin(base_url, match))[0]
            if absolute.startswith(("http://", "https://")):
                links.append(absolute)
    return {"title": title, "description": description, "headings": headings[:50], "links": links}


def web_fetch(url: str, extract: bool = True, max_chars: int = 20000) -> dict[str, Any]:
    started = time.time()
    with _client() as client:
        response = client.get(url)
        content = response.content[:MAX_FETCH_BYTES]
        encoding = response.encoding or "utf-8"
        html = content.decode(encoding, errors="replace")
    parsed = _parse_html(html, str(response.url))
    text = _extract_text(html, str(response.url)) if extract else ""
    return {
        "ok": response.is_success,
        "url": url,
        "final_url": str(response.url),
        "status": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "elapsed_ms": round((time.time() - started) * 1000, 1),
        "title": parsed["title"],
        "description": parsed["description"],
        "headings": parsed["headings"],
        "link_count": len(parsed["links"]),
        "links": parsed["links"][:200],
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
        "fetched_at": _now(),
    }


def extract_content(url: str, max_chars: int = 40000) -> dict[str, Any]:
    result = web_fetch(url, extract=True, max_chars=max_chars)
    return {
        "ok": result["ok"],
        "url": result["final_url"],
        "title": result["title"],
        "description": result["description"],
        "headings": result["headings"],
        "word_count": len(result["text"].split()),
        "text": result["text"],
    }


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def web_crawl(
    seeds: list[str],
    max_pages: int = 20,
    max_depth: int = 2,
    same_domain: bool = True,
    include: str | None = None,
    extract: bool = False,
) -> dict[str, Any]:
    _require_httpx()
    seeds = [s for s in seeds if s]
    if not seeds:
        raise ValueError("crawl requires at least one seed URL")
    allowed_domains = {_domain(s) for s in seeds}
    include_re = re.compile(include) if include else None
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(urldefrag(s)[0], 0) for s in seeds]
    pages: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    with _client() as client:
        while queue and len(pages) < max_pages:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                response = client.get(url)
                html = response.content[:MAX_FETCH_BYTES].decode(response.encoding or "utf-8", errors="replace")
                parsed = _parse_html(html, str(response.url))
                page = {
                    "url": url,
                    "final_url": str(response.url),
                    "depth": depth,
                    "status": response.status_code,
                    "title": parsed["title"],
                    "description": parsed["description"],
                    "outlinks": len(parsed["links"]),
                }
                if extract:
                    page["text"] = _extract_text(html, str(response.url))[:8000]
                pages.append(page)
                if depth < max_depth:
                    for link in parsed["links"]:
                        if link in visited:
                            continue
                        if same_domain and _domain(link) not in allowed_domains:
                            continue
                        if include_re and not include_re.search(link):
                            continue
                        queue.append((link, depth + 1))
            except Exception as error:  # noqa: BLE001
                errors.append({"url": url, "error": str(error)})

    return {
        "ok": True,
        "seeds": seeds,
        "pages_crawled": len(pages),
        "max_pages": max_pages,
        "max_depth": max_depth,
        "same_domain": same_domain,
        "pages": pages,
        "errors": errors,
        "crawled_at": _now(),
    }


def fetch_feed(url: str, limit: int = 20) -> dict[str, Any]:
    if feedparser is None:
        raise RuntimeError("feedparser is not installed in this image")
    with _client() as client:
        raw = client.get(url).content
    parsed = feedparser.parse(raw)
    entries = []
    for entry in parsed.entries[:limit]:
        entries.append({
            "title": getattr(entry, "title", ""),
            "link": getattr(entry, "link", ""),
            "published": getattr(entry, "published", getattr(entry, "updated", "")),
            "summary": re.sub(r"<[^>]+>", " ", getattr(entry, "summary", ""))[:500],
        })
    return {
        "ok": True,
        "feed_title": getattr(parsed.feed, "title", ""),
        "entry_count": len(parsed.entries),
        "entries": entries,
    }


# ----------------------------------------------------------------------------
# Link / data validation
# ----------------------------------------------------------------------------
def _collect_urls(rows: list[dict[str, Any]], fields: Iterable[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for row in rows:
        for field in fields:
            value = row.get(field)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                pairs.append((row.get("name", ""), value))
    return pairs


def check_links(
    dataset: str = "crawler_discoveries",
    fields: list[str] | None = None,
    limit: int = 50,
    method: str = "HEAD",
) -> dict[str, Any]:
    _require_httpx()
    fields = fields or ["resource_url", "url"]
    rows = _as_rows(_dataset(dataset))
    pairs = _collect_urls(rows, fields)[:limit]
    results: list[dict[str, Any]] = []

    def check(name: str, url: str) -> dict[str, Any]:
        try:
            with _client() as client:
                request = client.head if method.upper() == "HEAD" else client.get
                response = request(url)
                if response.status_code in (403, 405) and method.upper() == "HEAD":
                    response = client.get(url)
                return {"name": name, "url": url, "status": response.status_code, "ok": response.is_success, "final_url": str(response.url)}
        except Exception as error:  # noqa: BLE001
            return {"name": name, "url": url, "status": None, "ok": False, "error": str(error)}

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as pool:
        futures = [pool.submit(check, name, url) for name, url in pairs]
        for future in as_completed(futures):
            results.append(future.result())

    broken = [r for r in results if not r["ok"]]
    return {
        "ok": len(broken) == 0,
        "dataset": dataset,
        "checked": len(results),
        "broken_count": len(broken),
        "broken": broken,
        "results": sorted(results, key=lambda r: str(r["url"])),
    }


def validate_dataset(dataset: str, required_fields: list[str] | None = None) -> dict[str, Any]:
    rows = _as_rows(_dataset(dataset))
    defaults = {
        "awesome_list": ["name", "category", "medium"],
        "solution_registry": ["name"],
        "crawler_discoveries": ["name", "country_code", "resource_url"],
    }
    required = required_fields or defaults.get(dataset, ["name"])
    issues: list[dict[str, Any]] = []
    seen_names: Counter = Counter()
    for index, row in enumerate(rows):
        missing = [field for field in required if not row.get(field)]
        if missing:
            issues.append({"index": index, "name": row.get("name"), "missing": missing})
        if row.get("name"):
            seen_names[row["name"]] += 1
    duplicates = {name: count for name, count in seen_names.items() if count > 1}
    return {
        "ok": not issues and not duplicates,
        "dataset": dataset,
        "row_count": len(rows),
        "required_fields": required,
        "rows_with_issues": len(issues),
        "issues": issues[:100],
        "duplicate_names": duplicates,
    }


# ----------------------------------------------------------------------------
# Analytics / search
# ----------------------------------------------------------------------------
def dataset_stats(dataset: str = "crawler_discoveries", group_by: list[str] | None = None) -> dict[str, Any]:
    rows = _as_rows(_dataset(dataset))
    defaults = {
        "crawler_discoveries": ["continent", "country_code", "lifecycle_category", "vendor"],
        "awesome_list": ["category", "medium"],
        "solution_registry": ["category", "medium"],
    }
    fields = group_by or defaults.get(dataset, [])
    breakdown: dict[str, dict[str, int]] = {}
    for field in fields:
        counter: Counter = Counter()
        for row in rows:
            value = row.get(field)
            if isinstance(value, list):
                counter.update(str(v) for v in value)
            elif value is not None:
                counter[str(value)] += 1
        breakdown[field] = dict(counter.most_common(50))
    tag_counter: Counter = Counter()
    for row in rows:
        tags = row.get("tags")
        if isinstance(tags, list):
            tag_counter.update(str(t).lower() for t in tags)
    return {
        "dataset": dataset,
        "row_count": len(rows),
        "breakdown": breakdown,
        "top_tags": dict(tag_counter.most_common(30)),
        "generated_at": _now(),
    }


def full_text_search(query: str, datasets: list[str] | None = None, top_k: int = 15) -> dict[str, Any]:
    targets = datasets or ["awesome_list", "solution_registry", "crawler_discoveries"]
    terms = _tokens(query)
    hits: list[dict[str, Any]] = []
    for name in targets:
        for row in _as_rows(_dataset(name)):
            text = " ".join(str(v).lower() for v in row.values())
            score = sum(text.count(term) * (3 if term in str(row.get("name", "")).lower() else 1) for term in terms)
            if score > 0:
                hits.append({
                    "dataset": name,
                    "name": row.get("name"),
                    "score": score,
                    "category": row.get("category") or row.get("lifecycle_category"),
                    "resource_url": row.get("resource_url") or row.get("url", ""),
                })
    hits.sort(key=lambda h: (-h["score"], str(h["name"])))
    return {"query": query, "total_hits": len(hits), "results": hits[:top_k]}


def get_record(dataset: str, name: str) -> dict[str, Any]:
    needle = name.strip().lower()
    for row in _as_rows(_dataset(dataset)):
        if str(row.get("name", "")).strip().lower() == needle:
            return {"ok": True, "dataset": dataset, "record": row}
    matches = [row for row in _as_rows(_dataset(dataset)) if needle in str(row.get("name", "")).lower()]
    return {"ok": bool(matches), "dataset": dataset, "record": matches[0] if matches else None, "fuzzy": True, "candidates": [m.get("name") for m in matches[:10]]}


def search_sources(query: str, top_k: int = 10) -> dict[str, Any]:
    terms = _tokens(query)
    rows = _as_rows(_dataset("research_sources"))
    scored = []
    for row in rows:
        text = " ".join(str(v).lower() for v in row.values())
        score = sum(text.count(term) for term in terms)
        if score > 0 or not terms:
            scored.append({"name": row.get("name"), "url": row.get("url"), "note_en": row.get("note_en"), "score": score})
    scored.sort(key=lambda r: -r["score"])
    return {"query": query, "results": scored[:top_k], "source_count": len(rows)}


# ----------------------------------------------------------------------------
# Evidence gathering + reports
# ----------------------------------------------------------------------------
def gather_evidence(name: str, dataset: str = "solution_registry", max_chars: int = 6000) -> dict[str, Any]:
    record = get_record(dataset, name)
    if not record.get("record"):
        return {"ok": False, "error": f"No record matching '{name}' in {dataset}", "candidates": record.get("candidates")}
    row = record["record"]
    url = row.get("resource_url") or row.get("url")
    evidence: dict[str, Any] = {"ok": True, "name": row.get("name"), "record": row, "source_url": url}
    if url:
        try:
            fetched = extract_content(url, max_chars=max_chars)
            evidence["fetched"] = fetched
        except Exception as error:  # noqa: BLE001
            evidence["fetch_error"] = str(error)
    return evidence


def build_report(scene: str | None = None, top_k: int = 10) -> dict[str, Any]:
    discoveries = _as_rows(_dataset("crawler_discoveries"))
    alternatives = _as_rows(_dataset("awesome_list"))
    solutions = _as_rows(_dataset("solution_registry"))
    stats = dataset_stats("crawler_discoveries")
    scene_analysis = analyze_scene(scene, top_k) if scene else None

    lines = ["# PBX Research Brief", "", f"_Generated: {_now()}_", ""]
    lines.append("## Coverage")
    lines.append(f"- Solutions: {len(solutions)}")
    lines.append(f"- Technology alternatives: {len(alternatives)}")
    lines.append(f"- Crawler discoveries: {len(discoveries)}")
    countries = stats["breakdown"].get("country_code", {})
    lines.append(f"- Countries/regions: {len(countries)}")
    lines.append("")
    lines.append("## Lifecycle distribution")
    for key, value in stats["breakdown"].get("lifecycle_category", {}).items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Top tags")
    for tag, count in list(stats["top_tags"].items())[:15]:
        lines.append(f"- {tag}: {count}")
    if scene_analysis:
        lines.append("")
        lines.append(f"## Scene match: {scene}")
        lines.append("### Solutions")
        for item in scene_analysis["solutions"]:
            lines.append(f"- {item['name']} (score {item['score']})")
        lines.append("### Alternatives")
        for item in scene_analysis["alternatives"]:
            lines.append(f"- {item['name']} (score {item['score']})")

    return {
        "ok": True,
        "markdown": "\n".join(lines),
        "summary": {
            "solutions": len(solutions),
            "alternatives": len(alternatives),
            "discoveries": len(discoveries),
            "countries": len(countries),
        },
        "scene_analysis": scene_analysis,
        "stats": stats,
    }


# ----------------------------------------------------------------------------
# Tool registry
# ----------------------------------------------------------------------------
TOOLS: dict[str, dict[str, Any]] = {
    "generate_research_outputs": {
        "description": "Run crawler/research generation and validate produced PBX research assets.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "validate_research_outputs": {
        "description": "Validate generated report, registry, crawler seed, and technology-alternative assets.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "analyze_scene": {
        "description": "Rank existing alternatives and solutions for a deployment scene.",
        "inputSchema": {
            "type": "object",
            "properties": {"scene": {"type": "string"}, "top_k": {"type": "integer", "default": 8}},
            "required": ["scene"],
        },
    },
    "web_fetch": {
        "description": "Fetch a URL and return status, title, metadata, outbound links, and extracted main text.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}, "extract": {"type": "boolean", "default": True}, "max_chars": {"type": "integer", "default": 20000}},
            "required": ["url"],
        },
    },
    "extract_content": {
        "description": "Fetch a URL and return only cleaned readable article text plus headings.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}, "max_chars": {"type": "integer", "default": 40000}},
            "required": ["url"],
        },
    },
    "web_crawl": {
        "description": "Breadth-first crawl from seed URLs with depth/page limits and optional same-domain and regex filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "seeds": {"type": "array", "items": {"type": "string"}},
                "max_pages": {"type": "integer", "default": 20},
                "max_depth": {"type": "integer", "default": 2},
                "same_domain": {"type": "boolean", "default": True},
                "include": {"type": "string"},
                "extract": {"type": "boolean", "default": False},
            },
            "required": ["seeds"],
        },
    },
    "fetch_feed": {
        "description": "Fetch and parse an RSS/Atom feed into normalized entries.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}, "limit": {"type": "integer", "default": 20}},
            "required": ["url"],
        },
    },
    "check_links": {
        "description": "Validate reachability of URLs referenced by a dataset (parallel HEAD/GET with status codes).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {"type": "string", "default": "crawler_discoveries"},
                "fields": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "default": 50},
                "method": {"type": "string", "default": "HEAD"},
            },
        },
    },
    "validate_dataset": {
        "description": "Check a dataset for missing required fields and duplicate names.",
        "inputSchema": {
            "type": "object",
            "properties": {"dataset": {"type": "string"}, "required_fields": {"type": "array", "items": {"type": "string"}}},
            "required": ["dataset"],
        },
    },
    "dataset_stats": {
        "description": "Aggregate counts/breakdowns and top tags for a dataset.",
        "inputSchema": {
            "type": "object",
            "properties": {"dataset": {"type": "string", "default": "crawler_discoveries"}, "group_by": {"type": "array", "items": {"type": "string"}}},
        },
    },
    "full_text_search": {
        "description": "Keyword-rank records across one or more research datasets.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "datasets": {"type": "array", "items": {"type": "string"}}, "top_k": {"type": "integer", "default": 15}},
            "required": ["query"],
        },
    },
    "get_record": {
        "description": "Fetch a single dataset record by exact or fuzzy name match.",
        "inputSchema": {
            "type": "object",
            "properties": {"dataset": {"type": "string"}, "name": {"type": "string"}},
            "required": ["dataset", "name"],
        },
    },
    "search_sources": {
        "description": "Search the curated research_sources catalog by keyword.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 10}},
            "required": ["query"],
        },
    },
    "gather_evidence": {
        "description": "Resolve a record by name and fetch+extract supporting evidence from its source URL.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "dataset": {"type": "string", "default": "solution_registry"}, "max_chars": {"type": "integer", "default": 6000}},
            "required": ["name"],
        },
    },
    "build_report": {
        "description": "Build a markdown research brief summarizing coverage, lifecycle, tags, and optional scene match.",
        "inputSchema": {
            "type": "object",
            "properties": {"scene": {"type": "string"}, "top_k": {"type": "integer", "default": 10}},
        },
    },
}


DISPATCH: dict[str, Callable[..., Any]] = {
    "generate_research_outputs": lambda a: generate_research_outputs(),
    "validate_research_outputs": lambda a: validate_research_outputs(),
    "analyze_scene": lambda a: analyze_scene(str(a.get("scene", "")), int(a.get("top_k", 8))),
    "web_fetch": lambda a: web_fetch(str(a["url"]), bool(a.get("extract", True)), int(a.get("max_chars", 20000))),
    "extract_content": lambda a: extract_content(str(a["url"]), int(a.get("max_chars", 40000))),
    "web_crawl": lambda a: web_crawl(list(a.get("seeds", [])), int(a.get("max_pages", 20)), int(a.get("max_depth", 2)), bool(a.get("same_domain", True)), a.get("include"), bool(a.get("extract", False))),
    "fetch_feed": lambda a: fetch_feed(str(a["url"]), int(a.get("limit", 20))),
    "check_links": lambda a: check_links(str(a.get("dataset", "crawler_discoveries")), a.get("fields"), int(a.get("limit", 50)), str(a.get("method", "HEAD"))),
    "validate_dataset": lambda a: validate_dataset(str(a["dataset"]), a.get("required_fields")),
    "dataset_stats": lambda a: dataset_stats(str(a.get("dataset", "crawler_discoveries")), a.get("group_by")),
    "full_text_search": lambda a: full_text_search(str(a["query"]), a.get("datasets"), int(a.get("top_k", 15))),
    "get_record": lambda a: get_record(str(a["dataset"]), str(a["name"])),
    "search_sources": lambda a: search_sources(str(a["query"]), int(a.get("top_k", 10))),
    "gather_evidence": lambda a: gather_evidence(str(a["name"]), str(a.get("dataset", "solution_registry")), int(a.get("max_chars", 6000))),
    "build_report": lambda a: build_report(a.get("scene"), int(a.get("top_k", 10))),
}


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    arguments = arguments or {}
    handler = DISPATCH.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return handler(arguments)


# ----------------------------------------------------------------------------
# MCP stdio transport
# ----------------------------------------------------------------------------
def mcp_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def mcp_error(request_id: Any, message: str, code: int = -32603) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def run_mcp() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        request_id = None
        try:
            request = json.loads(line)
            method = request.get("method")
            request_id = request.get("id")
            if method == "initialize":
                response = mcp_response(request_id, {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "pbx-research-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                })
            elif method in ("notifications/initialized", "initialized"):
                continue
            elif method == "tools/list":
                response = mcp_response(request_id, {"tools": [{"name": name, **meta} for name, meta in TOOLS.items()]})
            elif method == "tools/call":
                params = request.get("params") or {}
                result = call_tool(str(params.get("name", "")), params.get("arguments") or {})
                response = mcp_response(request_id, {"content": [{"type": "text", "text": _json(result)}]})
            elif method == "ping":
                response = mcp_response(request_id, {})
            else:
                response = mcp_error(request_id, f"Unsupported method: {method}", -32601)
        except Exception as error:  # noqa: BLE001 - MCP boundary returns JSON errors.
            response = mcp_error(request_id, str(error))
        print(json.dumps(response), flush=True)


# ----------------------------------------------------------------------------
# HTTP transport
# ----------------------------------------------------------------------------
class ResearchHttpHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", os.environ.get("ALLOWED_ORIGINS", "*"))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/healthz"}:
            self._send_json(200, {"ok": True, "service": "pbx-research-mcp", "version": "1.0.0", "tools": sorted(TOOLS)})
            return
        if parsed.path == "/tools":
            self._send_json(200, {"tools": [{"name": name, **meta} for name, meta in TOOLS.items()]})
            return
        if parsed.path == "/validate":
            self._send_json(200, validate_research_outputs())
            return
        if parsed.path == "/analyze":
            query = parse_qs(parsed.query)
            self._send_json(200, analyze_scene(query.get("scene", [""])[0], int(query.get("top_k", ["8"])[0])))
            return
        self._send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            parsed = urlparse(self.path)
            # Generic tool endpoint: POST /tool/<name> with JSON arguments.
            if parsed.path.startswith("/tool/"):
                name = parsed.path[len("/tool/"):]
                self._send_json(200, {"ok": True, "tool": name, "result": call_tool(name, payload)})
                return
            if self.path == "/analyze":
                self._send_json(200, analyze_scene(str(payload.get("scene", "")), int(payload.get("top_k", 8))))
                return
            if self.path == "/generate":
                self._send_json(200, generate_research_outputs())
                return
            self._send_json(404, {"ok": False, "error": "Not found"})
        except Exception as error:  # noqa: BLE001
            self._send_json(500, {"ok": False, "error": str(error)})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", os.environ.get("ALLOWED_ORIGINS", "*"))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)


def run_http() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), ResearchHttpHandler)
    print(f"PBX research MCP HTTP service listening on {host}:{port}", flush=True)
    server.serve_forever()


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PBX research MCP service and CI runner.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("http", help="Run HTTP service for hosted microservice platforms.")
    subparsers.add_parser("mcp", help="Run MCP-compatible stdio server.")
    subparsers.add_parser("generate", help="Generate crawler/research outputs and validate them.")
    subparsers.add_parser("validate", help="Validate generated research outputs.")
    analyze = subparsers.add_parser("analyze", help="Rank alternatives and solutions for a scene.")
    analyze.add_argument("scene")
    analyze.add_argument("--top-k", type=int, default=8)
    tool = subparsers.add_parser("tool", help="Invoke any registered tool with JSON arguments.")
    tool.add_argument("name")
    tool.add_argument("--args", default="{}", help="JSON object of arguments.")
    subparsers.add_parser("list-tools", help="Print available tools.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "http":
        run_http()
        return
    if args.command == "mcp":
        run_mcp()
        return
    if args.command == "list-tools":
        print(_json([{"name": name, "description": meta["description"]} for name, meta in TOOLS.items()]))
        return
    if args.command == "generate":
        result = generate_research_outputs()
    elif args.command == "validate":
        result = validate_research_outputs()
    elif args.command == "analyze":
        result = analyze_scene(args.scene, args.top_k)
    elif args.command == "tool":
        result = call_tool(args.name, json.loads(args.args))
    else:
        raise SystemExit(f"Unsupported command: {args.command}")
    print(_json(result))
    if isinstance(result, dict) and result.get("ok") is False:
        raise SystemExit(1)
    if isinstance(result, dict) and result.get("generation", {}).get("ok") is False:
        raise SystemExit(1)
    if isinstance(result, dict) and result.get("validation", {}).get("ok") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
