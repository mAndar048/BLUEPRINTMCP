from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from mcp.resources import load_configs
from schemas.workflow import Step, Transition, Workflow

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _require_rule(rules: Dict[str, Any], key: str) -> Any:
    if key not in rules:
        raise ValueError(f"Missing generation rule: {key}")
    return rules[key]


def _split_description(description: str, rules: Dict[str, Any]) -> List[str]:
    text = _normalize_text(description)
    if not text:
        return []
    sentence_pattern = _require_rule(rules, "sentence_split_regex")
    sequence_pattern = _require_rule(rules, "sequence_split_regex")
    sentences = re.split(sentence_pattern, text)
    tasks: List[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        parts = re.split(sequence_pattern, sentence, flags=re.IGNORECASE)
        for part in parts:
            part = part.strip()
            if part:
                tasks.append(part)
    return tasks


def _pick_default_actor(actors: List[str], rules: Dict[str, Any]) -> str:
    preferred = rules.get("default_actor")
    if preferred and preferred in actors:
        return preferred

    fallback = rules.get("default_actor_fallback")
    if fallback and fallback in actors:
        return fallback

    if actors:
        return actors[0]

    if fallback:
        return fallback
    if preferred:
        return preferred

    raise ValueError("No actors configured")


def _infer_step_type(text: str, step_types: List[str], rules: Dict[str, Any]) -> str:
    lowered = text.lower()
    type_keywords = rules.get("type_keywords", {})
    for step_type, keywords in type_keywords.items():
        if step_type not in step_types:
            continue
        if any(keyword in lowered for keyword in keywords):
            return step_type

    default_step_type = rules.get("default_step_type")
    if default_step_type in step_types:
        return default_step_type

    return step_types[0]


def generate_workflow_spec(description: str) -> Dict[str, Any]:
    logger.info("tool invoked: generate_workflow_spec")
    configs = load_configs()
    step_types = configs["step_types"]
    actors = configs["actors"]
    rules = configs.get("generation_rules", {})

    if not step_types:
        raise ValueError("No step types configured")

    tasks = _split_description(description, rules)
    if not tasks:
        tasks = [_require_rule(rules, "default_task")]

    default_actor = _pick_default_actor(actors, rules)
    steps: List[Step] = []
    transitions: List[Transition] = []

    start_step_config = _require_rule(rules, "start_step")
    end_step_config = _require_rule(rules, "end_step")
    start_type = start_step_config.get("type")
    end_type = end_step_config.get("type")
    start_name = start_step_config.get("name")
    end_name = end_step_config.get("name")
    if not start_type or not end_type or not start_name or not end_name:
        raise ValueError("Generation rules must define start_step.type, start_step.name, end_step.type, end_step.name")

    if start_type not in step_types or end_type not in step_types:
        raise ValueError("Config must include start and end step types")

    step_id_counter = 1
    start_step = Step(
        id=f"step_{step_id_counter}",
        type=start_type,
        name=start_name,
        actor=default_actor,
    )
    steps.append(start_step)

    previous_step_id = start_step.id
    for task in tasks:
        step_id_counter += 1
        step_type = _infer_step_type(task, step_types, rules)
        step = Step(
            id=f"step_{step_id_counter}",
            type=step_type,
            name=task,
            actor=default_actor,
        )
        steps.append(step)
        transitions.append(
            Transition(from_step=previous_step_id, to_step=step.id, condition=None)
        )
        previous_step_id = step.id

    step_id_counter += 1
    end_step = Step(
        id=f"step_{step_id_counter}",
        type=end_type,
        name=end_name,
        actor=default_actor,
    )
    steps.append(end_step)
    transitions.append(
        Transition(from_step=previous_step_id, to_step=end_step.id, condition=None)
    )

    workflow = Workflow(
        workflow_id="wf_001",
        steps=steps,
        transitions=transitions,
        actors=actors,
    )
    return workflow.dict()


def validate_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("tool invoked: validate_workflow")
    configs = load_configs()
    step_types = set(configs["step_types"])
    actors = set(configs["actors"])

    errors: List[Dict[str, Any]] = []
    try:
        parsed = Workflow(**workflow)
    except Exception as exc:  # noqa: BLE001
        errors.append(
            {
                "code": "schema_error",
                "message": "Workflow does not match schema",
                "details": str(exc),
            }
        )
        logger.info("validation result: invalid")
        return {"valid": False, "errors": errors}

    step_ids = {step.id for step in parsed.steps}
    for step in parsed.steps:
        if step.type not in step_types:
            errors.append(
                {
                    "code": "unknown_step_type",
                    "message": f"Unknown step type: {step.type}",
                    "details": {"step_id": step.id},
                }
            )
        if step.actor not in actors:
            errors.append(
                {
                    "code": "missing_actor",
                    "message": f"Unknown actor: {step.actor}",
                    "details": {"step_id": step.id},
                }
            )

    for transition in parsed.transitions:
        if transition.from_step not in step_ids or transition.to_step not in step_ids:
            errors.append(
                {
                    "code": "invalid_transition",
                    "message": "Transition references unknown step",
                    "details": {
                        "from_step": transition.from_step,
                        "to_step": transition.to_step,
                    },
                }
            )

    valid = len(errors) == 0
    logger.info("validation result: %s", "valid" if valid else "invalid")
    return {"valid": valid, "errors": errors}


def export_to_format(workflow: Dict[str, Any], format_type: str) -> Dict[str, Any]:
    logger.info("tool invoked: export_to_format")
    configs = load_configs()
    formats = {f.lower() for f in configs["output_formats"]}

    fmt = format_type.strip().lower()
    if fmt not in formats:
        return {
            "format": format_type,
            "output": None,
            "errors": [
                {
                    "code": "unsupported_format",
                    "message": f"Unsupported format: {format_type}",
                }
            ],
        }

    parsed = Workflow(**workflow)
    if fmt == "json":
        return {"format": "JSON", "output": parsed.dict()}

    lines = ["flowchart TD"]
    for step in parsed.steps:
        label = f"{step.type}: {step.name}"
        lines.append(f"    {step.id}[\"{label}\"]")
    for transition in parsed.transitions:
        lines.append(f"    {transition.from_step} --> {transition.to_step}")

    mermaid = "\n".join(lines)
    return {"format": "Mermaid", "output": mermaid}
