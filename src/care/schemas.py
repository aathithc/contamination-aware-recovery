from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"
    system = "system"


class StateType(str, Enum):
    fact = "fact"
    correction = "correction"
    constraint = "constraint"
    assumption = "assumption"
    derivation = "derivation"
    structural_record = "structural_record"
    answer_candidate = "answer_candidate"
    metadata = "metadata"


class EdgeType(str, Enum):
    supports = "supports"
    contradicts = "contradicts"
    supersedes = "supersedes"
    derived_from = "derived_from"
    belongs_to = "belongs_to"
    verified_by = "verified_by"
    requires = "requires"


class NodeStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    contaminated = "contaminated"


class StateNode(BaseModel):
    id: str
    conversation_id: str
    turn_index: int
    source: SourceType
    type: StateType
    text: str
    entities: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    status: NodeStatus = NodeStatus.active


class StateEdge(BaseModel):
    source: str
    target: str
    type: EdgeType
    rationale: str | None = None


class ConversationStateGraph(BaseModel):
    conversation_id: str
    nodes: list[StateNode] = Field(default_factory=list)
    edges: list[StateEdge] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class RecoveryPrompt(BaseModel):
    conversation_id: str
    method: str
    prompt: str
    included_node_ids: list[str] = Field(default_factory=list)
    excluded_node_ids: list[str] = Field(default_factory=list)
