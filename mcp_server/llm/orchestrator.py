from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from google.genai import errors, types

from llm.client import build_tool_schema, get_gemini_client, get_gemini_model, resolve_gemini_model
from mcp.runtime import MCPRuntime

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    def __init__(self, runtime: MCPRuntime) -> None:
        self.runtime = runtime

    def _tool_dispatch(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("llm tool selected: %s", name)
        if name == "generate_workflow_spec":
            return self.runtime.generate(arguments["description"])
        if name == "validate_workflow":
            return self.runtime.validate(arguments["workflow"])
        if name == "export_to_format":
            return self.runtime.export(arguments["workflow"], arguments["format"])
        return {
            "errors": [
                {
                    "code": "unknown_tool",
                    "message": f"Unknown tool: {name}",
                }
            ]
        }

    def generate_with_llm(self, prompt: str, output_format: str) -> Dict[str, Any]:
        client = get_gemini_client()
        model_name = resolve_gemini_model(client, get_gemini_model())
        tools = build_tool_schema()
        resources = self.runtime.list_resources()

        system_prompt = (
            "You are an MCP tool-using assistant. You must call MCP tools to generate, "
            "validate, and export a workflow. Do NOT create workflows directly. "
            "Always call generate_workflow_spec, then validate_workflow, then export_to_format."
        )

        contents: List[types.Content] = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=system_prompt),
                    types.Part(text=f"MCP resources: {json.dumps(resources, ensure_ascii=False)}"),
                    types.Part(text=f"Prompt: {prompt}\nOutput format: {output_format}"),
                ],
            )
        ]

        max_rounds = 6
        tool_calls_seen = 0
        last_generated: Optional[Dict[str, Any]] = None
        last_export: Optional[Dict[str, Any]] = None
        last_validation: Optional[Dict[str, Any]] = None

        for _ in range(max_rounds):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        tools=tools,
                        temperature=0,
                    ),
                )
            except errors.ClientError as exc:
                error_text = str(exc)
                if "NOT_FOUND" in error_text or "404" in error_text:
                    model_name = resolve_gemini_model(client, None)
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            tools=tools,
                            temperature=0,
                        ),
                    )
                else:
                    raise

            tool_calls = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    tool_calls.append(part.function_call)

            if not tool_calls:
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text=(
                                    "You must call MCP tools. Call generate_workflow_spec, then validate_workflow, then export_to_format."
                                )
                            )
                        ],
                    )
                )
                continue

            tool_calls_seen += len(tool_calls)
            for call in tool_calls:
                arguments = dict(call.args)
                result = self._tool_dispatch(call.name, arguments)
                if call.name == "generate_workflow_spec":
                    last_generated = result
                if call.name == "validate_workflow":
                    last_validation = result
                if call.name == "export_to_format":
                    last_export = result

                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=call.name,
                                    response=result,
                                )
                            )
                        ],
                    )
                )

            if last_export is not None and last_validation is not None:
                break

            if last_validation is not None and last_validation.get("valid", False) and last_export is None:
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text=(
                                    "Call export_to_format now using the most recent workflow and the requested output format."
                                )
                            )
                        ],
                    )
                )

        if tool_calls_seen == 0:
            return {
                "errors": [
                    {
                        "code": "llm_no_tool_calls",
                        "message": "LLM did not call MCP tools.",
                    }
                ]
            }

        if last_validation is not None and not last_validation.get("valid", False):
            return {
                "valid": False,
                "validation": last_validation,
                "export": last_export,
            }

        return {
            "valid": True,
            "validation": last_validation,
            "export": last_export,
        }
