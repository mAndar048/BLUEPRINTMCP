from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    return genai.Client(api_key=api_key)


def get_gemini_model() -> str | None:
    return os.getenv("GEMINI_MODEL")


def resolve_gemini_model(client: genai.Client, preferred: str | None) -> str:
    if preferred:
        return preferred

    models = list(client.models.list())
    for model in models:
        name = getattr(model, "name", "")
        if "gemini-1.5-flash" in name:
            return name
    for model in models:
        name = getattr(model, "name", "")
        if "gemini" in name and "embed" not in name:
            return name

    raise ValueError("No Gemini model available for generateContent")


def build_tool_schema() -> List[types.Tool]:
    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="generate_workflow_spec",
                    description="Generate a workflow blueprint JSON from natural language.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Natural language description of the workflow.",
                            }
                        },
                        "required": ["description"],
                    },
                ),
                types.FunctionDeclaration(
                    name="validate_workflow",
                    description="Validate a workflow against the MCP schema and config rules.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "workflow": {
                                "type": "object",
                                "description": "Workflow JSON to validate.",
                            }
                        },
                        "required": ["workflow"],
                    },
                ),
                types.FunctionDeclaration(
                    name="export_to_format",
                    description="Export a workflow to JSON or Mermaid format.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "workflow": {
                                "type": "object",
                                "description": "Workflow JSON to export.",
                            },
                            "format": {
                                "type": "string",
                                "description": "Export format: JSON, Mermaid, YAML, or BPMN.",
                                "enum": ["JSON", "Mermaid", "YAML", "BPMN"],
                            },
                        },
                        "required": ["workflow", "format"],
                    },
                ),
            ]
        )
    ]
    logger.info("llm tool schema prepared")
    return tools
