from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

import yaml
from jsonschema import ValidationError, validate

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
    decimal_token = "<DECIMAL>"
    text = re.sub(r"(?<=\d)\.(?=\d)", decimal_token, text)
    sentence_pattern = _require_rule(rules, "sentence_split_regex")
    sequence_pattern = _require_rule(rules, "sequence_split_regex")
    has_conditionals = bool(re.search(r"\bif\b", text, flags=re.IGNORECASE)) and bool(
        re.search(r"\botherwise\b|\belse\b", text, flags=re.IGNORECASE)
    )
    if has_conditionals:
        sentence_pattern_no_comma = sentence_pattern.replace("\\,", "").replace(",", "")
        if sentence_pattern_no_comma.strip() == "":
            sentence_pattern_no_comma = sentence_pattern
        sentences = re.split(sentence_pattern_no_comma, text)
    else:
        sentences = re.split(sentence_pattern, text)
    tasks: List[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if re.search(r"\bif\b", sentence, flags=re.IGNORECASE) and re.search(
            r"\botherwise\b|\belse\b", sentence, flags=re.IGNORECASE
        ):
            parts = [sentence]
        else:
            parts = re.split(sequence_pattern, sentence, flags=re.IGNORECASE)
        for part in parts:
            part = part.strip()
            if part:
                tasks.append(part.replace(decimal_token, "."))
    return tasks


def _extract_condition_and_action(text: str) -> tuple[str | None, str | None]:
    then_split = re.split(r"\bthen\b", text, flags=re.IGNORECASE, maxsplit=1)
    if len(then_split) == 2:
        condition = then_split[0].strip(" ,;")
        action = then_split[1].strip(" ,;")
        return (condition or None, action or None)

    comparator_match = re.search(r"(.+?[<>=]=?\s*\d+)(.*)", text)
    if comparator_match:
        condition = comparator_match.group(1).strip(" ,;")
        action = comparator_match.group(2).strip(" ,;")
        return (condition or None, action or None)

    return (None, None)


def _split_if_else_task(text: str) -> Dict[str, str] | None:
    lowered = text.lower()
    if "if " not in lowered:
        return None

    if " otherwise " in lowered:
        parts = re.split(r"\botherwise\b", text, flags=re.IGNORECASE, maxsplit=1)
    elif re.search(r"\belse\b", text, flags=re.IGNORECASE):
        parts = re.split(r"\belse\b", text, flags=re.IGNORECASE, maxsplit=1)
    else:
        return None

    if len(parts) != 2:
        return None

    if_part_raw = re.split(r"\bif\b", parts[0], flags=re.IGNORECASE, maxsplit=1)[-1].strip(" ,;")
    else_part = parts[1].strip(" ,;")
    if not if_part_raw or not else_part:
        return None

    condition, action = _extract_condition_and_action(if_part_raw)
    if_action = action or if_part_raw
    return {
        "condition": condition or if_part_raw,
        "if_action": if_action,
        "else_action": else_part,
    }


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
    runtimes = configs.get("runtimes", [])

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

    previous_step_ids = [start_step.id]
    for task in tasks:
        if_else = _split_if_else_task(task)
        if if_else:
            step_id_counter += 1
            decision_step = Step(
                id=f"step_{step_id_counter}",
                type="decision" if "decision" in step_types else _infer_step_type(task, step_types, rules),
                name=f"Decision: {if_else['condition']}",
                actor=default_actor,
            )
            steps.append(decision_step)
            for previous_step_id in previous_step_ids:
                transitions.append(
                    Transition(from_step=previous_step_id, to_step=decision_step.id, condition=None)
                )

            step_id_counter += 1
            if_step = Step(
                id=f"step_{step_id_counter}",
                type=_infer_step_type(if_else["if_action"], step_types, rules),
                name=if_else["if_action"],
                actor=default_actor,
            )
            steps.append(if_step)

            step_id_counter += 1
            else_step = Step(
                id=f"step_{step_id_counter}",
                type=_infer_step_type(if_else["else_action"], step_types, rules),
                name=if_else["else_action"],
                actor=default_actor,
            )
            steps.append(else_step)

            transitions.append(
                Transition(
                    from_step=decision_step.id,
                    to_step=if_step.id,
                    condition=if_else["condition"],
                )
            )
            transitions.append(
                Transition(
                    from_step=decision_step.id,
                    to_step=else_step.id,
                    condition="otherwise",
                )
            )

            previous_step_ids = [if_step.id, else_step.id]
            continue

        step_id_counter += 1
        step_type = _infer_step_type(task, step_types, rules)
        step = Step(
            id=f"step_{step_id_counter}",
            type=step_type,
            name=task,
            actor=default_actor,
        )
        steps.append(step)
        for previous_step_id in previous_step_ids:
            transitions.append(
                Transition(from_step=previous_step_id, to_step=step.id, condition=None)
            )
        previous_step_ids = [step.id]

    step_id_counter += 1
    end_step = Step(
        id=f"step_{step_id_counter}",
        type=end_type,
        name=end_name,
        actor=default_actor,
    )
    steps.append(end_step)
    for previous_step_id in previous_step_ids:
        transitions.append(
            Transition(from_step=previous_step_id, to_step=end_step.id, condition=None)
        )

    default_runtime = rules.get("default_runtime")
    if default_runtime and default_runtime in runtimes:
        runtime = default_runtime
    else:
        runtime = runtimes[0] if runtimes else None

    workflow = Workflow(
        workflow_id="wf_001",
        steps=steps,
        transitions=transitions,
        actors=actors,
        runtime=runtime,
    )
    return workflow.dict()


def validate_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("tool invoked: validate_workflow")
    configs = load_configs()
    step_types = set(configs["step_types"])
    actors = set(configs["actors"])
    runtimes = set(configs.get("runtimes", []))
    workflow_schema = configs.get("schema_definitions", {}).get("workflow_schema")

    errors: List[Dict[str, Any]] = []
    if workflow_schema:
        try:
            validate(instance=workflow, schema=workflow_schema)
        except ValidationError as exc:
            errors.append(
                {
                    "code": "schema_error",
                    "message": "Workflow does not match schema",
                    "details": str(exc),
                }
            )
            logger.info("validation result: invalid")
            return {"valid": False, "errors": errors}

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

    if parsed.runtime and runtimes and parsed.runtime not in runtimes:
        errors.append(
            {
                "code": "unknown_runtime",
                "message": f"Unknown runtime: {parsed.runtime}",
                "details": {"runtime": parsed.runtime},
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
    format_templates = configs.get("format_templates", {})

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

    if fmt == "yaml":
        return {
            "format": "YAML",
            "output": yaml.safe_dump(parsed.dict(), sort_keys=False),
        }

    if fmt == "bpmn":
        definitions_id = parsed.workflow_id
        process_id = f"{definitions_id}_process"
        bpmn_templates = format_templates.get("bpmn", {})
        definitions_header = bpmn_templates.get(
            "definitions_header",
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<bpmn:definitions xmlns:bpmn=\"http://www.omg.org/spec/BPMN/20100524/MODEL\"\n"
            "                 xmlns:bpmndi=\"http://www.omg.org/spec/BPMN/20100524/DI\"\n"
            "                 xmlns:dc=\"http://www.omg.org/spec/DD/20100524/DC\"\n"
            "                 xmlns:di=\"http://www.omg.org/spec/DD/20100524/DI\"\n"
            "                 id=\"{definitions_id}\">\n"
            "  <bpmn:process id=\"{process_id}\" isExecutable=\"false\">",
        )
        task_template = bpmn_templates.get(
            "task_template", "    <bpmn:task id=\"{id}\" name=\"{name}\" />"
        )
        start_template = bpmn_templates.get(
            "start_template", "    <bpmn:startEvent id=\"{id}\" name=\"{name}\" />"
        )
        end_template = bpmn_templates.get(
            "end_template", "    <bpmn:endEvent id=\"{id}\" name=\"{name}\" />"
        )
        sequence_template = bpmn_templates.get(
            "sequence_template",
            "    <bpmn:sequenceFlow id=\"{flow_id}\" sourceRef=\"{from_step}\" targetRef=\"{to_step}\" />",
        )
        definitions_footer = bpmn_templates.get(
            "definitions_footer", "  </bpmn:process>\n</bpmn:definitions>"
        )

        lines = [
            definitions_header.format(
                definitions_id=definitions_id,
                process_id=process_id,
            )
        ]

        for step in parsed.steps:
            if step.type == "start":
                lines.append(start_template.format(id=step.id, name=step.name))
            elif step.type == "end":
                lines.append(end_template.format(id=step.id, name=step.name))
            else:
                lines.append(task_template.format(id=step.id, name=step.name))

        for index, transition in enumerate(parsed.transitions, start=1):
            flow_id = f"flow_{index}"
            lines.append(
                sequence_template.format(
                    flow_id=flow_id,
                    from_step=transition.from_step,
                    to_step=transition.to_step,
                )
            )

        lines.append(definitions_footer)

        return {"format": "BPMN", "output": "\n".join(lines)}

    mermaid_templates = format_templates.get("mermaid", {})
    header = mermaid_templates.get("header", "flowchart TD")
    node_template = mermaid_templates.get("node_template", "    {id}[\"{label}\"]")
    edge_template = mermaid_templates.get("edge_template", "    {from_step} --> {to_step}")

    lines = [header]
    for step in parsed.steps:
        label = f"{step.type}: {step.name}"
        lines.append(node_template.format(id=step.id, label=label))
    for transition in parsed.transitions:
        lines.append(
            edge_template.format(
                from_step=transition.from_step,
                to_step=transition.to_step,
            )
        )

    mermaid = "\n".join(lines)
    return {"format": "Mermaid", "output": mermaid}
