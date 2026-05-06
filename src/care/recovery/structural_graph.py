from care.schemas import ConversationStateGraph, RecoveryPrompt
from care.graph.structural_retrieval import (
    get_highlighted_cells,
    get_cell_neighborhood,
    linearize_structural,
)


def build_structural_graph_prompt(csg: ConversationStateGraph) -> RecoveryPrompt:
    """Recovery prompt built from structural retrieval linearization."""
    highlighted = get_highlighted_cells(csg)
    linearized = linearize_structural(csg)

    included_ids: list[str] = [c.id for c in highlighted]
    for cell in highlighted:
        for neighbor in get_cell_neighborhood(cell, csg):
            if neighbor.id not in included_ids:
                included_ids.append(neighbor.id)

    all_ids = {n.id for n in csg.nodes}
    excluded_ids = [nid for nid in all_ids if nid not in set(included_ids)]

    return RecoveryPrompt(
        conversation_id=csg.conversation_id,
        method="structural_graph",
        prompt=linearized,
        included_node_ids=included_ids,
        excluded_node_ids=excluded_ids,
    )
