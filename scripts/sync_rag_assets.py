from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
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


def build_manifest(paths: list[Path], prefix: str) -> dict:
    assets = []
    for path in iter_files(paths):
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        assets.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "key": asset_key(path, prefix),
                "size": path.stat().st_size,
                "sha256": sha256(path),
                "content_type": mime_type,
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_prefix": prefix,
        "asset_count": len(assets),
        "assets": assets,
    }


def write_manifest(manifest: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def upload_notellm(manifest: dict, endpoint: str, token: str, timeout: int) -> dict:
    """Upload assets to a NoteLLM-compatible HTTP ingestion endpoint.

    Public NoteLLM docs currently expose agent note retrieval but do not document
    a project file upload API. This adapter intentionally uses a generic,
    explicit endpoint so CI can integrate with a future NoteLLM upload endpoint,
    a NoteLLM MCP bridge, or a compatible custom ingestion service.
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    results = []
    for asset in manifest["assets"]:
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
    parser.add_argument("--include", action="append", type=Path, default=None)
    parser.add_argument("--notellm-upload-url", default=os.environ.get("NOTELLM_UPLOAD_URL", ""))
    parser.add_argument("--notellm-token", default=os.environ.get("NOTELLM_API_TOKEN", ""))
    parser.add_argument("--notellm-timeout", type=int, default=int(os.environ.get("NOTELLM_TIMEOUT", "60")))
    parser.add_argument("--upload-notellm", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    include_paths = [path if path.is_absolute() else ROOT / path for path in (args.include or DEFAULT_INCLUDE_DIRS)]
    manifest = build_manifest(include_paths, args.prefix)
    write_manifest(manifest, args.manifest)
    print(f"Wrote {manifest['asset_count']} RAG assets to {args.manifest}")

    if args.upload_notellm:
        if not args.notellm_upload_url:
            raise SystemExit("NOTELLM_UPLOAD_URL is required when --upload-notellm is set")
        result = upload_notellm(manifest, args.notellm_upload_url, args.notellm_token, args.notellm_timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
