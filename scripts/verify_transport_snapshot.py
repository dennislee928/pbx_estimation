from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "rag_engine" / "dist" / "rag_assets_manifest.json"
DEFAULT_POINTER = ROOT / "rag_engine" / "dist" / "latest-pointer.json"
DEFAULT_PAIRS = ROOT / "rag_engine" / "dist" / "rag_assets_r2.tsv"
DEFAULT_OUTPUT = ROOT / "rag_engine" / "dist" / "transport_snapshot_parity.json"
CATALOGS = {
    "solution": ROOT / "frontend" / "data" / "solution_registry.json",
    "alternative": ROOT / "frontend" / "data" / "awesome_list.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify an immutable RAG snapshot before publication.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--pointer", type=Path, default=DEFAULT_POINTER)
    parser.add_argument("--r2-pairs", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = read_json(args.manifest)
    pointer = read_json(args.pointer)
    assets = {asset["path"]: asset for asset in manifest.get("assets", [])}
    pairs = {
        tuple(line.split("\t", 1))
        for line in args.r2_pairs.read_text().splitlines()
        if line.strip()
    }
    errors: list[str] = []

    expected_manifest_key = f'{manifest.get("asset_prefix", "")}/rag_engine/dist/rag_assets_manifest.json'
    if pointer.get("manifest_key") != expected_manifest_key:
        errors.append("latest pointer does not reference the generated immutable manifest")
    for field in ("asset_prefix", "catalog_snapshot_id", "transport_schema_version", "catalog_snapshot"):
        if pointer.get(field) != manifest.get(field):
            errors.append(f"pointer and manifest disagree on {field}")

    checks = {}
    catalog_spec = {
        "solution": ("frontend/data/solution_registry.json", "solution_registry_sha256", "solution_record_count"),
        "alternative": ("frontend/data/awesome_list.json", "awesome_list_sha256", "alternative_record_count"),
    }
    snapshot = manifest.get("catalog_snapshot", {})
    for kind, (relative, sha_field, count_field) in catalog_spec.items():
        path = CATALOGS[kind]
        asset = assets.get(relative)
        actual_sha = sha256(path)
        actual_count = len(read_json(path))
        expected_key = f'{manifest.get("asset_prefix", "").rstrip("/")}/{relative}'
        checks[kind] = {"path": relative, "sha256": actual_sha, "record_count": actual_count}
        if not asset:
            errors.append(f"manifest is missing {relative}")
            continue
        if asset.get("sha256") != actual_sha or snapshot.get(sha_field) != actual_sha:
            errors.append(f"SHA-256 mismatch for {relative}")
        if asset.get("labels", {}).get("row_count") != actual_count or snapshot.get(count_field) != actual_count:
            errors.append(f"record-count mismatch for {relative}")
        if (expected_key, relative) not in pairs:
            errors.append(f"R2 upload list is missing {relative}")

    result = {
        "valid": not errors,
        "transport_schema_version": manifest.get("transport_schema_version"),
        "asset_prefix": manifest.get("asset_prefix"),
        "asset_count": manifest.get("asset_count"),
        "checks": checks,
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
