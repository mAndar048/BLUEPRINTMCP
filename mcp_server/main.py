from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from mcp.runtime import MCPRuntime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI()
runtime = MCPRuntime()


class GenerateRequest(BaseModel):
    description: str


class ValidateRequest(BaseModel):
    workflow: Dict[str, Any]


class ExportRequest(BaseModel):
    workflow: Dict[str, Any]
    format: str


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
