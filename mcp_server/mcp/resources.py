from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_CONFIG_CACHE: Dict[str, Any] | None = None


def _load_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_configs() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    base_dir = Path(__file__).resolve().parents[1]
    default_config_dir = base_dir / "configs"
    override_dir = os.getenv("MCP_CONFIG_DIR")
    config_dir = Path(override_dir) if override_dir else Path("/app/configs")
    if not config_dir.exists():
        config_dir = default_config_dir

    step_types = _load_json_file(config_dir / "step_types.json")
    actors = _load_json_file(config_dir / "actors.json")
    connectors = _load_json_file(config_dir / "connectors.json")
    output_formats = _load_json_file(config_dir / "output_formats.json")
    generation_rules = _load_json_file(config_dir / "generation_rules.json")
    schema_definitions = _load_json_file(config_dir / "schema_definitions.json")
    format_templates = _load_json_file(config_dir / "format_templates.json")
    runtimes = _load_json_file(config_dir / "runtimes.json")

    _CONFIG_CACHE = {
        "step_types": step_types.get("step_types", []),
        "actors": actors.get("actors", []),
        "connectors": connectors.get("connectors", []),
        "output_formats": output_formats.get("formats", []),
        "generation_rules": generation_rules,
        "schema_definitions": schema_definitions,
        "format_templates": format_templates,
        "runtimes": runtimes.get("runtimes", []),
    }

    logger.info("configs loaded from %s", config_dir)
    return _CONFIG_CACHE


def list_resources() -> list[Dict[str, Any]]:
    configs = load_configs()
    return [
        {
            "name": "step_types",
            "uri": "mcp://resources/step-types",
            "data": configs["step_types"],
        },
        {
            "name": "actors",
            "uri": "mcp://resources/actors",
            "data": configs["actors"],
        },
        {
            "name": "connectors",
            "uri": "mcp://resources/connectors",
            "data": configs["connectors"],
        },
        {
            "name": "output_formats",
            "uri": "mcp://resources/output-formats",
            "data": configs["output_formats"],
        },
        {
            "name": "generation_rules",
            "uri": "mcp://resources/generation-rules",
            "data": configs["generation_rules"],
        },
        {
            "name": "schema_definitions",
            "uri": "mcp://resources/schema-definitions",
            "data": configs["schema_definitions"],
        },
        {
            "name": "format_templates",
            "uri": "mcp://resources/format-templates",
            "data": configs["format_templates"],
        },
        {
            "name": "runtimes",
            "uri": "mcp://resources/runtimes",
            "data": configs["runtimes"],
        },
    ]


def get_resource(resource_name: str) -> Dict[str, Any] | None:
    for resource in list_resources():
        if resource["name"] == resource_name:
            return resource
    return None
