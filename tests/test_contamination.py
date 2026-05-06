import pytest
from care.schemas import (
    ConversationStateGraph,
    EdgeType,
    NodeStatus,
    SourceType,
    StateEdge,
    StateNode,
    StateType,
)
from care.graph.contamination import propagate_contamination, get_trust_level, TrustLevel


def node(id: str, source: SourceType, type: StateType, **kw) -> StateNode:
    return StateNode(
        id=id,
        conversation_id="test",
        turn_index=kw.pop("turn_index", 0),
        source=source,
        type=type,
        text=kw.pop("text", f"node {id}"),
        **kw,
    )


def graph(nodes: list[StateNode], edges: list[StateEdge]) -> ConversationStateGraph:
    return ConversationStateGraph(conversation_id="test", nodes=nodes, edges=edges)


class TestContradictionAsymmetry:
    """Rule C: contradicts must not contaminate both sides."""

    def test_user_fact_contradicts_assistant_assumption(self):
        u1 = node("u1", SourceType.user, StateType.fact)
        a1 = node("a1", SourceType.assistant, StateType.assumption)
        edge = StateEdge(source="u1", target="a1", type=EdgeType.contradicts)
        csg = graph([u1, a1], [edge])

        updated, report = propagate_contamination(csg)
        nmap = {n.id: n for n in updated.nodes}

        assert nmap["u1"].status == NodeStatus.active, "user fact must stay active"
        assert nmap["a1"].status == NodeStatus.contaminated
        assert "u1" not in report.contaminated_ids
        assert "a1" in report.contaminated_ids

    def test_contradicts_does_not_contaminate_higher_trust(self):
        # If the edge direction is reversed (assistant contradicts user), the user stays clean
        u1 = node("u1", SourceType.user, StateType.fact)
        a1 = node("a1", SourceType.assistant, StateType.assumption)
        edge = StateEdge(source="a1", target="u1", type=EdgeType.contradicts)
        csg = graph([u1, a1], [edge])

        updated, report = propagate_contamination(csg)
        nmap = {n.id: n for n in updated.nodes}

        # a1 gets contaminated by Rule A (assumption without support)
        # u1 must NOT be contaminated (a1 has lower trust than u1)
        assert nmap["u1"].status == NodeStatus.active
        assert "u1" not in report.contaminated_ids


class TestUserCorrectionSupersedes:
    """Rule B with supersedes: old node becomes inactive, correction stays active."""

    def test_user_correction_supersedes_assistant_assumption(self):
        a1 = node("a1", SourceType.assistant, StateType.assumption)
        u1 = node("u1", SourceType.user, StateType.correction)
        edge = StateEdge(source="u1", target="a1", type=EdgeType.supersedes)
        csg = graph([a1, u1], [edge])

        updated, report = propagate_contamination(csg)
        nmap = {n.id: n for n in updated.nodes}

        assert nmap["a1"].status == NodeStatus.inactive
        assert nmap["u1"].status == NodeStatus.active
        assert "a1" in report.inactive_ids
        assert "u1" not in report.inactive_ids

    def test_superseded_node_not_in_contaminated_list(self):
        a1 = node("a1", SourceType.assistant, StateType.assumption)
        u1 = node("u1", SourceType.user, StateType.correction)
        edge = StateEdge(source="u1", target="a1", type=EdgeType.supersedes)
        csg = graph([a1, u1], [edge])

        _, report = propagate_contamination(csg)
        assert "a1" not in report.contaminated_ids


class TestDerivedFromPropagation:
    """Rule D: contamination flows through derived_from edges (source=derived, target=dependency)."""

    def test_contamination_propagates_to_derivation(self):
        a1 = node("a1", SourceType.assistant, StateType.assumption)
        a2 = node("a2", SourceType.assistant, StateType.derivation)
        # a2 derived_from a1 (a2 is source, a1 is target/dependency)
        edge = StateEdge(source="a2", target="a1", type=EdgeType.derived_from)
        csg = graph([a1, a2], [edge])

        updated, report = propagate_contamination(csg)
        nmap = {n.id: n for n in updated.nodes}

        assert nmap["a1"].status == NodeStatus.contaminated
        assert nmap["a2"].status == NodeStatus.contaminated
        assert "a2" in report.contaminated_ids

    def test_contamination_propagates_through_inactive_dependency(self):
        """Derivation of a superseded (inactive) node is also contaminated."""
        u1 = node("u1", SourceType.user, StateType.correction)
        a1 = node("a1", SourceType.assistant, StateType.assumption)
        a2 = node("a2", SourceType.assistant, StateType.derivation)
        supersedes_edge = StateEdge(source="u1", target="a1", type=EdgeType.supersedes)
        derived_edge = StateEdge(source="a2", target="a1", type=EdgeType.derived_from)
        csg = graph([u1, a1, a2], [supersedes_edge, derived_edge])

        updated, report = propagate_contamination(csg)
        nmap = {n.id: n for n in updated.nodes}

        assert nmap["a1"].status == NodeStatus.inactive
        assert nmap["a2"].status == NodeStatus.contaminated

    def test_assumption_contaminated_even_with_user_support(self):
        # Rule A (updated): assumption nodes require tool VERIFIED_BY to stay clean.
        # A SUPPORTS edge from a user fact is NOT sufficient — assumptions are placeholders
        # invented by the assistant, not derivations from user-provided values.
        a1 = node("a1", SourceType.assistant, StateType.assumption)
        u1 = node("u1", SourceType.user, StateType.fact)
        a2 = node("a2", SourceType.assistant, StateType.derivation)
        support_edge = StateEdge(source="u1", target="a1", type=EdgeType.supports)
        derived_edge = StateEdge(source="a2", target="a1", type=EdgeType.derived_from)
        csg = graph([a1, u1, a2], [support_edge, derived_edge])

        updated, report = propagate_contamination(csg)
        nmap = {n.id: n for n in updated.nodes}

        # a1 is contaminated despite SUPPORTS (assumption rule)
        assert nmap["a1"].status == NodeStatus.contaminated
        # a2 is contaminated via Rule D (derived_from contaminated a1)
        assert nmap["a2"].status == NodeStatus.contaminated


class TestTrustLevels:
    def test_tool_node_highest(self):
        t = node("t1", SourceType.tool, StateType.fact)
        csg = graph([t], [])
        assert get_trust_level(t, csg) == TrustLevel.TOOL_VERIFIED

    def test_user_correction_above_user_fact(self):
        u_corr = node("u1", SourceType.user, StateType.correction)
        u_fact = node("u2", SourceType.user, StateType.fact)
        csg = graph([u_corr, u_fact], [])
        assert get_trust_level(u_corr, csg) > get_trust_level(u_fact, csg)

    def test_assistant_assumption_lowest(self):
        a = node("a1", SourceType.assistant, StateType.assumption)
        csg = graph([a], [])
        assert get_trust_level(a, csg) == TrustLevel.ASSISTANT_ASSUMPTION
