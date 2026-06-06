from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = {
    "transport_schema_version", "label_dictionary_version", "primary_bearer",
    "bearer_family", "link_mode", "network_type", "bearers",
    "control_interfaces", "api_capable", "hybrid", "transport_confidence",
    "transport_classification_source", "transport_label_en", "transport_label_zh",
}
LINK_MODES = {"wired", "wireless", "contactless", "physical", "manual", "virtual", "hybrid", "unknown"}
NETWORK_TYPES = {"ip", "non_ip_digital", "analog", "physical_signal", "manual", "mixed", "unknown"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict]:
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a JSON array")
    return rows


def validate_rows(name: str, rows: list[dict]) -> dict:
    errors = []
    unknown = []
    hybrid = []
    identities = set()
    for index, row in enumerate(rows):
        identity = f"{row.get('vendor', '')}|{row.get('name', '')}|{row.get('country_code', '')}"
        if identity in identities:
            errors.append(f"{name}[{index}] duplicate identity: {identity}")
        identities.add(identity)
        missing = sorted(REQUIRED_FIELDS - row.keys())
        if missing:
            errors.append(f"{name}[{index}] {row.get('name')}: missing {', '.join(missing)}")
            continue
        if row["transport_schema_version"] != 2:
            errors.append(f"{name}[{index}] {row.get('name')}: transport_schema_version must be 2")
        if row["link_mode"] not in LINK_MODES:
            errors.append(f"{name}[{index}] {row.get('name')}: invalid link_mode {row['link_mode']}")
        if row["network_type"] not in NETWORK_TYPES:
            errors.append(f"{name}[{index}] {row.get('name')}: invalid network_type {row['network_type']}")
        if row["bearer_family"] == "cellular" and row["link_mode"] == "wired" and not row["hybrid"]:
            errors.append(f"{name}[{index}] {row.get('name')}: cellular bearer cannot be wired")
        if row["api_capable"] and row["transport_classification_source"] == "api_rule":
            errors.append(f"{name}[{index}] {row.get('name')}: API cannot be the bearer classification source")
        if row["transport_confidence"] == "unknown":
            unknown.append(row.get("name", ""))
        if row["hybrid"]:
            hybrid.append(row.get("name", ""))
    return {"row_count": len(rows), "errors": errors, "unknown": unknown, "hybrid": hybrid}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--solutions", type=Path, default=ROOT / "frontend/data/solution_registry.json")
    parser.add_argument("--alternatives", type=Path, default=ROOT / "frontend/data/awesome_list.json")
    parser.add_argument("--output", type=Path, default=ROOT / "rag_engine/dist/transport_snapshot_validation.json")
    args = parser.parse_args()
    solutions = load_rows(args.solutions)
    alternatives = load_rows(args.alternatives)
    solution_result = validate_rows("solutions", solutions)
    alternative_result = validate_rows("alternatives", alternatives)
    errors = solution_result["errors"] + alternative_result["errors"]
    report = {
        "transport_schema_version": 2,
        "valid": not errors,
        "solution_registry_sha256": sha256(args.solutions),
        "awesome_list_sha256": sha256(args.alternatives),
        "solutions": solution_result,
        "alternatives": alternative_result,
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
