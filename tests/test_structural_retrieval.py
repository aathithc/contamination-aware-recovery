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
from care.graph.structural_retrieval import (
    get_highlighted_cells,
    get_cell_neighborhood,
    linearize_structural,
)
from care.recovery.selector import select_and_build


def _node(id: str, type: StateType, attributes: dict | None = None, status: NodeStatus = NodeStatus.active) -> StateNode:
    return StateNode(
        id=id,
        conversation_id="test",
        turn_index=0,
        source=SourceType.user,
        type=type,
        text=f"node {id}",
        attributes=attributes or {},
        status=status,
    )


def _make_d2t_graph() -> ConversationStateGraph:
    table_meta = _node("t1", StateType.metadata, {"title": "Sales Q1"})
    cell_hi = _node("c1", StateType.structural_record, {
        "table_title": "Sales Q1",
        "row_id": "row_0",
        "row_header": "Product A",
        "column": "Revenue",
        "value": "$500K",
        "highlighted": True,
    })
    cell_lo = _node("c2", StateType.structural_record, {
        "table_title": "Sales Q1",
        "row_id": "row_1",
        "row_header": "Product B",
        "column": "Revenue",
        "value": "$300K",
        "highlighted": False,
    })
    edges = [
        StateEdge(source="c1", target="t1", type=EdgeType.belongs_to),
        StateEdge(source="c2", target="t1", type=EdgeType.belongs_to),
    ]
    return ConversationStateGraph(conversation_id="test", nodes=[table_meta, cell_hi, cell_lo], edges=edges)


class TestGetHighlightedCells:
    def test_returns_only_highlighted(self):
        csg = _make_d2t_graph()
        highlighted = get_highlighted_cells(csg)
        assert len(highlighted) == 1
        assert highlighted[0].id == "c1"

    def test_excludes_contaminated_highlighted(self):
        csg = _make_d2t_graph()
        nodes = [
            n.model_copy(update={"status": NodeStatus.contaminated}) if n.id == "c1" else n
            for n in csg.nodes
        ]
        csg2 = ConversationStateGraph(conversation_id="test", nodes=nodes, edges=csg.edges)
        assert get_highlighted_cells(csg2) == []

    def test_empty_graph(self):
        csg = ConversationStateGraph(conversation_id="test", nodes=[], edges=[])
        assert get_highlighted_cells(csg) == []


class TestCellNeighborhood:
    def test_retrieves_belongs_to_neighbors(self):
        csg = _make_d2t_graph()
        highlighted = get_highlighted_cells(csg)
        neighbors = get_cell_neighborhood(highlighted[0], csg)
        neighbor_ids = [n.id for n in neighbors]
        assert "t1" in neighbor_ids

    def test_non_highlighted_cell_not_in_neighborhood_of_highlighted(self):
        csg = _make_d2t_graph()
        highlighted = get_highlighted_cells(csg)
        neighbors = get_cell_neighborhood(highlighted[0], csg)
        neighbor_ids = [n.id for n in neighbors]
        # c2 is not a belongs_to neighbor of c1
        assert "c2" not in neighbor_ids


class TestLinearizeStructural:
    def test_contains_highlighted_cell_data(self):
        csg = _make_d2t_graph()
        text = linearize_structural(csg)
        assert "Product A" in text
        assert "Revenue" in text
        assert "$500K" in text
        assert "Highlighted: true" in text

    def test_does_not_mention_non_highlighted_row_in_header(self):
        csg = _make_d2t_graph()
        text = linearize_structural(csg)
        # Product B is non-highlighted; it must not appear in the highlighted section
        assert "Product B" not in text.split("Supporting context:")[0]

    def test_empty_on_no_highlighted(self):
        csg = _make_d2t_graph()
        nodes = [
            n.model_copy(update={"attributes": {**n.attributes, "highlighted": False}})
            for n in csg.nodes
        ]
        csg2 = ConversationStateGraph(conversation_id="test", nodes=nodes, edges=csg.edges)
        assert linearize_structural(csg2) == ""

    def test_includes_instruction(self):
        csg = _make_d2t_graph()
        text = linearize_structural(csg)
        assert "Instruction:" in text
        assert "faithful sentence" in text


class TestSelectorUsesGraphStructure:
    def test_selects_structural_graph_for_highlighted_table(self):
        csg = _make_d2t_graph()
        prompt = select_and_build(csg)
        assert prompt.method == "structural_graph"

    def test_selects_concat_for_plain_clean_graph(self):
        u1 = _node("u1", StateType.fact)
        csg = ConversationStateGraph(conversation_id="test", nodes=[u1], edges=[])
        prompt = select_and_build(csg)
        assert prompt.method == "concat"
