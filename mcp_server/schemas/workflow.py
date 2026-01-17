from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Step(BaseModel):
    id: str
    type: str
    name: str
    actor: str
    connector: Optional[str] = None


class Transition(BaseModel):
    from_step: str
    to_step: str
    condition: Optional[str] = None


class Workflow(BaseModel):
    workflow_id: str
    steps: List[Step]
    transitions: List[Transition]
    actors: List[str]
