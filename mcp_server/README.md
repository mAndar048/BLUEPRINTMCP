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

## Phase 2: Containerization

### Build Image
```bash
docker build -t mcp-workflow-server .
```

### Run Container
```bash
docker run -p 8000:8000 mcp-workflow-server
```

### Run With Config Override (Volume Mount)
```bash
docker run -p 8000:8000 \
	-v $(pwd)/configs:/app/configs \
	mcp-workflow-server
```

### Example Container Requests
```bash
curl -X GET "http://localhost:8000/resources"
curl -X POST "http://localhost:8000/generate" -H "Content-Type: application/json" -d '{"description": "Customer submits request, manager reviews and approves, system notifies customer."}'
curl -X POST "http://localhost:8000/validate" -H "Content-Type: application/json" -d '{"workflow": {"workflow_id": "wf_001", "steps": [], "transitions": [], "actors": []}}'
curl -X POST "http://localhost:8000/export" -H "Content-Type: application/json" -d '{"workflow": {"workflow_id": "wf_001", "steps": [], "transitions": [], "actors": []}, "format": "Mermaid"}'
```

## Phase 3: LLM Integration

### Environment Variables
```bash
setx GEMINI_API_KEY "your_api_key"
setx GEMINI_MODEL "gemini-1.5-flash-latest"
```

### LLM Generate Endpoint
```bash
curl -X POST "http://localhost:8000/llm/generate" -H "Content-Type: application/json" -d '{"prompt": "Customer submits request, manager reviews and approves, system notifies customer.", "output_format": "Mermaid"}'
curl -X POST "http://localhost:8000/llm/generate" -H "Content-Type: application/json" -d '{"prompt": "Customer submits request, manager reviews and approves, system notifies customer.", "output_format": "JSON"}'
curl -X POST "http://localhost:8000/llm/generate" -H "Content-Type: application/json" -d '{"prompt": "Customer submits request, manager reviews and approves, system notifies customer.", "output_format": "YAML"}'
curl -X POST "http://localhost:8000/llm/generate" -H "Content-Type: application/json" -d '{"prompt": "Customer submits request, manager reviews and approves, system notifies customer.", "output_format": "BPMN"}'
```

### Industry Prompt Examples (Config-Driven)
```bash
# Banking
curl -X POST "http://localhost:8000/llm/generate" -H "Content-Type: application/json" -d '{"prompt": "Loan origination process: customer applies, underwriter reviews, manager approves, system funds loan.", "output_format": "JSON"}'

# Healthcare
curl -X POST "http://localhost:8000/llm/generate" -H "Content-Type: application/json" -d '{"prompt": "Patient intake, clinician assessment, treatment approval, follow-up scheduling.", "output_format": "Mermaid"}'

# HR
curl -X POST "http://localhost:8000/llm/generate" -H "Content-Type: application/json" -d '{"prompt": "Employee onboarding: candidate accepts offer, HR verifies documents, IT provisions access, manager orientation.", "output_format": "JSON"}'

# Legal
curl -X POST "http://localhost:8000/llm/generate" -H "Content-Type: application/json" -d '{"prompt": "Case intake, conflict check, attorney review, client approval, filing.", "output_format": "Mermaid"}'
```
