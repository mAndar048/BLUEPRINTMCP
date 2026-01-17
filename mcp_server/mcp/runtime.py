from __future__ import annotations

import logging
from typing import Any, Dict

from mcp.resources import get_resource, list_resources
from mcp.tools import export_to_format, generate_workflow_spec, validate_workflow

logger = logging.getLogger(__name__)


class MCPRuntime:
    def generate(self, description: str) -> Dict[str, Any]:
        logger.info("runtime generate invoked")
        return generate_workflow_spec(description)

    def validate(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("runtime validate invoked")
        return validate_workflow(workflow)

    def export(self, workflow: Dict[str, Any], format_type: str) -> Dict[str, Any]:
        logger.info("runtime export invoked")
        return export_to_format(workflow, format_type)

    def list_resources(self) -> Dict[str, Any]:
        logger.info("runtime list_resources invoked")
        return {"resources": list_resources()}

    def get_resource(self, resource_name: str) -> Dict[str, Any]:
        logger.info("runtime get_resource invoked")
        resource = get_resource(resource_name)
        if resource is None:
            return {
                "errors": [
                    {
                        "code": "resource_not_found",
                        "message": f"Unknown resource: {resource_name}",
                    }
                ]
            }
        return resource
