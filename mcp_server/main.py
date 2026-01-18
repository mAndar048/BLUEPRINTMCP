from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from urllib.parse import quote

from llm.orchestrator import LLMOrchestrator
from mcp.runtime import MCPRuntime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI()
runtime = MCPRuntime()
llm_orchestrator = LLMOrchestrator(runtime)

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"


class GenerateRequest(BaseModel):
    description: str


class ValidateRequest(BaseModel):
    workflow: Dict[str, Any]


class ExportRequest(BaseModel):
    workflow: Dict[str, Any]
    format: str


class LLMGenerateRequest(BaseModel):
    prompt: str
    output_format: str


class VisualizerRenderRequest(BaseModel):
    workflow: Dict[str, Any] | None = None
    mermaid: str | None = None
    format: str = "Mermaid"


@app.post("/generate")
async def generate_workflow(payload: GenerateRequest):
    return runtime.generate(payload.description)


@app.post("/validate")
async def validate_workflow(payload: ValidateRequest):
    return runtime.validate(payload.workflow)


@app.post("/export")
async def export_workflow(payload: ExportRequest):
    return runtime.export(payload.workflow, payload.format)


@app.get("/resources")
async def list_resources():
    return runtime.list_resources()


@app.get("/resources/{resource_name}")
async def get_resource(resource_name: str):
    return runtime.get_resource(resource_name)


@app.post("/llm/generate")
async def llm_generate(payload: LLMGenerateRequest):
    return llm_orchestrator.generate_with_llm(payload.prompt, payload.output_format)


@app.get("/visualizer")
async def mermaid_visualizer():
    return FileResponse(PUBLIC_DIR / "visualizer.html")


@app.post("/visualizer/render")
async def visualizer_render(payload: VisualizerRenderRequest):
    # Accept either raw Mermaid code or a workflow to export
    mermaid_code: str | None = None
    if payload.mermaid:
        mermaid_code = payload.mermaid
    elif payload.workflow:
        export_result = runtime.export(payload.workflow, payload.format)
        # Expect { format: str, output: str }
        mermaid_code = export_result.get("output")
        if not mermaid_code:
            return {
                "errors": export_result.get(
                    "errors",
                    [{"code": "export_failed", "message": "Failed to export workflow to diagram."}],
                )
            }
    else:
        return {"errors": [{"code": "invalid_request", "message": "Provide 'mermaid' or 'workflow' in request."}]}

    # URL-encode Mermaid so the visualizer can render immediately via ?src=
    encoded = quote(mermaid_code)
    return RedirectResponse(url=f"/visualizer?src={encoded}", status_code=307)
