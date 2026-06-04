from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_WORKSPACE = Path(__file__).resolve().parents[2]
WORKSPACE = Path(os.environ.get("PBX_WORKSPACE", DEFAULT_WORKSPACE)).resolve()


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


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


def generate_research_outputs() -> dict[str, Any]:
    result = _run([sys.executable, "scripts/generate_research_outputs.py"])
    validation = validate_research_outputs() if result["ok"] else {}
    return {"generation": result, "validation": validation}


def _load_json(relative: str) -> Any:
    path = WORKSPACE / relative
    with path.open() as handle:
        return json.load(handle)


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
    alternatives = [] if missing else _load_json("frontend/data/awesome_list.json")
    solutions = [] if missing else _load_json("frontend/data/solution_registry.json")
    crawler_seed = {} if missing else _load_json("frontend/data/crawler_seed_context.json")
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
        "crawler_seed_known_alternative_count": crawler_seed.get("known_alternative_count"),
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
    alternatives = _load_json("frontend/data/awesome_list.json")
    solutions = _load_json("frontend/data/solution_registry.json")

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


TOOLS = {
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
            "properties": {
                "scene": {"type": "string"},
                "top_k": {"type": "integer", "default": 8},
            },
            "required": ["scene"],
        },
    },
}


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    arguments = arguments or {}
    if name == "generate_research_outputs":
        return generate_research_outputs()
    if name == "validate_research_outputs":
        return validate_research_outputs()
    if name == "analyze_scene":
        return analyze_scene(str(arguments.get("scene", "")), int(arguments.get("top_k", 8)))
    raise ValueError(f"Unknown tool: {name}")


def mcp_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def mcp_error(request_id: Any, message: str, code: int = -32603) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def run_mcp() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            method = request.get("method")
            request_id = request.get("id")
            if method == "initialize":
                response = mcp_response(request_id, {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "pbx-research-mcp", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                })
            elif method == "tools/list":
                response = mcp_response(request_id, {"tools": [{"name": name, **meta} for name, meta in TOOLS.items()]})
            elif method == "tools/call":
                params = request.get("params") or {}
                result = call_tool(str(params.get("name", "")), params.get("arguments") or {})
                response = mcp_response(request_id, {"content": [{"type": "text", "text": _json(result)}]})
            else:
                response = mcp_error(request_id, f"Unsupported method: {method}", -32601)
        except Exception as error:  # noqa: BLE001 - MCP boundary should return JSON errors.
            response = mcp_error(None, str(error))
        print(json.dumps(response), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PBX research MCP service and CI runner.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("mcp", help="Run MCP-compatible stdio server.")
    subparsers.add_parser("generate", help="Generate crawler/research outputs and validate them.")
    subparsers.add_parser("validate", help="Validate generated research outputs.")
    analyze = subparsers.add_parser("analyze", help="Rank alternatives and solutions for a scene.")
    analyze.add_argument("scene")
    analyze.add_argument("--top-k", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "mcp":
        run_mcp()
        return
    if args.command == "generate":
        result = generate_research_outputs()
    elif args.command == "validate":
        result = validate_research_outputs()
    elif args.command == "analyze":
        result = analyze_scene(args.scene, args.top_k)
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
