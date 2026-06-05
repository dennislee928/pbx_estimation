from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INCLUDE_DIRS = [
    ROOT / "reports",
    ROOT / "data" / "processed",
    ROOT / "frontend" / "data",
]
DEFAULT_MANIFEST = ROOT / "rag_engine" / "dist" / "rag_assets_manifest.json"
DEFAULT_NOTEBOOKLM_DIR = ROOT / "rag_engine" / "dist" / "notebooklm_sources"
DEFAULT_HF_ASSET_DIR = ROOT / "rag_engine" / "dist" / "hf_assets"
NOTEBOOKLM_EXTENSIONS = {".md", ".txt", ".csv", ".json", ".html", ".pdf"}
NOTEBOOKLM_SOURCE_LIMIT = 50


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            yield path
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and not child.name.startswith("."):
                yield child


def asset_key(path: Path, prefix: str) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return f"{prefix.rstrip('/')}/{relative}"


# Catalog files whose rows carry structured transport/metric metadata. The
# manifest summarizes these so the RAG retriever can filter on transport
# (e.g. exclude ethernet) and metrics, not just on filename.
CATALOG_LABEL_FIELDS = {
    "frontend/data/awesome_list.json": {
        "transport_field": "medium",
        "metric_fields": ["latency", "reliability", "security", "cost_model", "recommended_devices", "industry_fit"],
    },
    "frontend/data/solution_registry.json": {
        "transport_field": "tags",
        "metric_fields": ["vendor", "continent", "recommended_terminals", "cost_band", "industry_fit", "lifecycle_assigned"],
    },
}


def classify_kind(rel_path: str) -> str:
    """Coarse semantic kind used by the retriever to weight/scope a document."""
    if rel_path.startswith("reports/"):
        return "report"
    if rel_path.startswith("data/processed/"):
        return "data"
    if rel_path.startswith("frontend/data/"):
        return "catalog"
    return "other"


def build_labels(path: Path, rel_path: str) -> dict:
    """Build a semantic label block for an asset.

    For known catalog JSONs this includes the distinct transport mediums and the
    metric fields present, so retrieval can apply transport exclusions and
    metric filters. Failures degrade gracefully to the coarse ``kind`` label.
    """
    labels: dict = {"kind": classify_kind(rel_path)}
    spec = CATALOG_LABEL_FIELDS.get(rel_path)
    if spec is None:
        return labels
    try:
        rows = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return labels
    if not isinstance(rows, list):
        return labels
    transport_field = spec["transport_field"]
    transports = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = str(row.get(transport_field, ""))
        for token in re.split(r"[;,]\s*", raw):
            token = token.strip()
            if token:
                transports.add(token)
    labels["row_count"] = len(rows)
    labels["transport_field"] = transport_field
    labels["transport_values"] = sorted(transports)
    labels["metric_fields"] = spec["metric_fields"]
    return labels


def build_manifest(paths: list[Path], prefix: str) -> dict:
    assets = []
    for path in iter_files(paths):
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        rel_path = path.relative_to(ROOT).as_posix()
        assets.append(
            {
                "path": rel_path,
                "key": asset_key(path, prefix),
                "size": path.stat().st_size,
                "sha256": sha256(path),
                "content_type": mime_type,
                "labels": build_labels(path, rel_path),
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_prefix": prefix,
        "asset_count": len(assets),
        "label_schema": {
            "kind": "report | data | catalog | other",
            "transport_field": "catalog field summarizing the transport medium",
            "transport_values": "distinct transport mediums present in a catalog",
            "metric_fields": "structured metric columns available for filtering",
        },
        "assets": assets,
    }


def write_manifest(manifest: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def write_r2_pairs(manifest: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as handle:
        for asset in manifest["assets"]:
            handle.write(f"{asset['key']}\t{asset['path']}\n")


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")[:120] or "source"


def build_notebooklm_bundle(manifest: dict, output_dir: Path) -> dict:
    """Create a NotebookLM-ready bundle of at most 50 uploadable sources."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    preferred = []
    for asset in manifest["assets"]:
        path = ROOT / asset["path"]
        suffix = path.suffix.lower()
        if suffix not in NOTEBOOKLM_EXTENSIONS:
            continue
        score = 0
        if asset["path"].startswith("reports/"):
            score += 40
        if asset["path"].startswith("data/processed/"):
            score += 30
        if asset["path"].startswith("frontend/data/"):
            score += 20
        if suffix in {".md", ".txt", ".csv", ".json"}:
            score += 10
        preferred.append((score, asset))

    selected = [asset for _, asset in sorted(preferred, key=lambda item: (-item[0], item[1]["path"]))[:NOTEBOOKLM_SOURCE_LIMIT]]
    source_manifest = {
        "generated_at": manifest["generated_at"],
        "source_limit": NOTEBOOKLM_SOURCE_LIMIT,
        "source_count": len(selected),
        "sources": [],
        "notes": [
            "Google NotebookLM has no official public upload API.",
            "Upload these files manually, or use an unofficial notebooklm-rest-api/notebooklm-py bridge at your own risk.",
        ],
    }

    for index, asset in enumerate(selected, start=1):
        source_path = ROOT / asset["path"]
        destination_name = f"{index:02d}-{slug(asset['path'])}"
        destination = output_dir / destination_name
        shutil.copy2(source_path, destination)
        source_manifest["sources"].append(
            {
                "source_file": destination.name,
                "original_path": asset["path"],
                "sha256": asset["sha256"],
                "size": asset["size"],
                "content_type": asset["content_type"],
            }
        )

    (output_dir / "notebooklm_sources_manifest.json").write_text(
        json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n"
    )
    return source_manifest


def build_hf_asset_bundle(manifest: dict, output_dir: Path) -> dict:
    """Copy all RAG assets into a self-contained directory for HF Docker Spaces."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for asset in manifest["assets"]:
        source = ROOT / asset["path"]
        destination = output_dir / asset["key"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append({"key": asset["key"], "path": asset["path"]})

    manifest_destination = output_dir / manifest["asset_prefix"] / "rag_engine" / "dist" / "rag_assets_manifest.json"
    manifest_destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {"asset_count": len(copied), "asset_root": output_dir.as_posix(), "assets": copied}


def upload_notebooklm(manifest: dict, endpoint: str, token: str, timeout: int) -> dict:
    """Upload sources to an unofficial NotebookLM-compatible ingestion endpoint.

    Google NotebookLM has no official public file-upload API. This adapter is
    intentionally generic so CI can call a self-hosted notebooklm-rest-api
    instance or a notebooklm-py bridge when the user explicitly provides one.
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    results = []
    selected = [
        asset
        for asset in manifest["assets"]
        if (ROOT / asset["path"]).suffix.lower() in NOTEBOOKLM_EXTENSIONS
    ][:NOTEBOOKLM_SOURCE_LIMIT]
    for asset in selected:
        path = ROOT / asset["path"]
        with path.open("rb") as handle:
            response = requests.post(
                endpoint,
                headers=headers,
                data={
                    "path": asset["path"],
                    "key": asset["key"],
                    "sha256": asset["sha256"],
                    "content_type": asset["content_type"],
                    "source": "pbx_estimation",
                    "target": "notebooklm",
                },
                files={"file": (path.name, handle, asset["content_type"])},
                timeout=timeout,
            )
        response.raise_for_status()
        results.append({"path": asset["path"], "status_code": response.status_code})
    return {"uploaded": len(results), "results": results}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and optionally upload RAG assets.")
    parser.add_argument("--prefix", default=os.environ.get("RAG_ASSET_PREFIX", "latest"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--r2-pairs", type=Path, default=ROOT / "rag_engine" / "dist" / "rag_assets_r2.tsv")
    parser.add_argument("--notebooklm-dir", type=Path, default=DEFAULT_NOTEBOOKLM_DIR)
    parser.add_argument("--hf-asset-dir", type=Path, default=DEFAULT_HF_ASSET_DIR)
    parser.add_argument("--include", action="append", type=Path, default=None)
    parser.add_argument("--notebooklm-upload-url", default=os.environ.get("NOTEBOOKLM_UPLOAD_URL", ""))
    parser.add_argument("--notebooklm-token", default=os.environ.get("NOTEBOOKLM_API_TOKEN", ""))
    parser.add_argument("--notebooklm-timeout", type=int, default=int(os.environ.get("NOTEBOOKLM_TIMEOUT", "60")))
    parser.add_argument("--upload-notebooklm", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    include_paths = [path if path.is_absolute() else ROOT / path for path in (args.include or DEFAULT_INCLUDE_DIRS)]
    manifest = build_manifest(include_paths, args.prefix)
    write_manifest(manifest, args.manifest)
    write_r2_pairs(manifest, args.r2_pairs)
    notebooklm_manifest = build_notebooklm_bundle(manifest, args.notebooklm_dir)
    hf_manifest = build_hf_asset_bundle(manifest, args.hf_asset_dir)
    print(f"Wrote {manifest['asset_count']} RAG assets to {args.manifest}")
    print(f"Wrote {notebooklm_manifest['source_count']} NotebookLM sources to {args.notebooklm_dir}")
    print(f"Wrote {hf_manifest['asset_count']} Hugging Face Space assets to {args.hf_asset_dir}")

    if args.upload_notebooklm:
        if not args.notebooklm_upload_url:
            raise SystemExit("NOTEBOOKLM_UPLOAD_URL is required when --upload-notebooklm is set")
        result = upload_notebooklm(manifest, args.notebooklm_upload_url, args.notebooklm_token, args.notebooklm_timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
