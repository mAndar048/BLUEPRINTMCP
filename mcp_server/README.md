# MCP Server

## Overview
This repository contains the implementation of the Model Context Protocol (MCP) Server, which converts natural language process descriptions into structured workflow blueprints.

## File Structure
- `main.py`: FastAPI entry point.
- `mcp/resources.py`: Loads config libraries from `configs/`.
- `mcp/tools.py`: MCP tools to generate, validate, and export workflows.
- `mcp/runtime.py`: Orchestration wrapper for MCP tools.
- `schemas/`: Pydantic schemas for workflow validation.
- `configs/`: Configuration files for step types, actors, connectors, and output formats.

## API Endpoints
- `POST /generate`: Accepts plain English and returns workflow JSON.
- `POST /validate`: Validates the workflow.
- `POST /export`: Exports the workflow to the specified format.
- `GET /resources`: Lists MCP-style resources (step types, actors, connectors, output formats, generation rules).
- `GET /resources/{resource_name}`: Returns a single MCP-style resource.

## Run Instructions
```bash
uvicorn main:app --reload
```

## Example CURL Commands

### Generate Workflow
```bash
curl -X POST "http://localhost:8000/generate" -H "Content-Type: application/json" -d '{"description": "User submits a request, then manager approves, then system stores the record"}'
```

### Validate Workflow
```bash
curl -X POST "http://localhost:8000/validate" -H "Content-Type: application/json" -d '{"workflow": {"workflow_id": "wf_001", "steps": [], "transitions": [], "actors": []}}'
```

### Export Workflow
```bash
curl -X POST "http://localhost:8000/export" -H "Content-Type: application/json" -d '{"workflow": {"workflow_id": "wf_001", "steps": [], "transitions": [], "actors": []}, "format": "Mermaid"}'
```

### List MCP Resources
```bash
curl -X GET "http://localhost:8000/resources"
```
