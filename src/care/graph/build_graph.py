import networkx as nx
from care.schemas import ConversationStateGraph, StateNode, StateEdge


def to_nx(csg: ConversationStateGraph) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    for node in csg.nodes:
        G.add_node(node.id, **node.model_dump())
    for edge in csg.edges:
        G.add_edge(
            edge.source,
            edge.target,
            type=edge.type,
            rationale=edge.rationale,
        )
    return G


def from_nx(G: nx.MultiDiGraph, conversation_id: str) -> ConversationStateGraph:
    nodes = [StateNode.model_validate(data) for _, data in G.nodes(data=True)]
    edges = [
        StateEdge(source=u, target=v, type=data["type"], rationale=data.get("rationale"))
        for u, v, data in G.edges(data=True)
    ]
    return ConversationStateGraph(
        conversation_id=conversation_id,
        nodes=nodes,
        edges=edges,
    )
