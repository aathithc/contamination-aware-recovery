import inspect
import pytest
from pydantic import ValidationError

from care.schemas import (
    ConversationStateGraph,
    EdgeType,
    NodeStatus,
    RecoveryPrompt,
    SourceType,
    StateEdge,
    StateNode,
    StateType,
)


class TestStateNode:
    def test_defaults(self):
        node = StateNode(
            id="n1",
            conversation_id="c1",
            turn_index=0,
            source=SourceType.user,
            type=StateType.fact,
            text="Hello",
        )
        assert node.entities == []
        assert node.attributes == {}
        assert node.status == NodeStatus.active

    def test_invalid_source_raises(self):
        with pytest.raises(ValidationError):
            StateNode(
                id="n1",
                conversation_id="c1",
                turn_index=0,
                source="oracle",
                type=StateType.fact,
                text="Hello",
            )

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            StateNode(
                id="n1",
                conversation_id="c1",
                turn_index=0,
                source=SourceType.user,
                type="opinion",
                text="Hello",
            )


class TestStateEdge:
    def test_basic_edge(self):
        edge = StateEdge(source="n1", target="n2", type=EdgeType.supports)
        assert edge.rationale is None

    def test_edge_with_rationale(self):
        edge = StateEdge(source="n1", target="n2", type=EdgeType.derived_from, rationale="depends on")
        assert edge.rationale == "depends on"


class TestConversationStateGraph:
    def test_has_attributes_field(self):
        csg = ConversationStateGraph(conversation_id="c1", nodes=[], edges=[])
        assert csg.attributes == {}

    def test_attributes_stored(self):
        csg = ConversationStateGraph(
            conversation_id="c1", nodes=[], edges=[], attributes={"failed_extraction": True}
        )
        assert csg.attributes["failed_extraction"] is True

    def test_serialization_roundtrip(self):
        node = StateNode(
            id="n1",
            conversation_id="c1",
            turn_index=0,
            source=SourceType.user,
            type=StateType.fact,
            text="x = 5",
        )
        csg = ConversationStateGraph(conversation_id="c1", nodes=[node], edges=[])
        restored = ConversationStateGraph.model_validate_json(csg.model_dump_json())
        assert restored.nodes[0].text == "x = 5"
        assert restored.attributes == {}


class TestSelectorSignature:
    """Selector must not accept task labels — selection must be graph-structure-only."""

    def test_select_and_build_has_no_task_label_param(self):
        from care.recovery.selector import select_and_build
        params = list(inspect.signature(select_and_build).parameters)
        assert "task_type" not in params
        assert "task_label" not in params
        assert "label" not in params
        assert "task" not in params
