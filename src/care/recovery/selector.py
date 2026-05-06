from care.schemas import ConversationStateGraph, RecoveryPrompt
from care.graph.features import (
    has_highlighted_structural,
    has_many_belongs_to,
    has_contaminated_nodes,
)
from care.recovery.concat import build_concat_prompt
from care.recovery.trust_filtered import build_trust_filtered_prompt
from care.recovery.structural_graph import build_structural_graph_prompt


def select_and_build(csg: ConversationStateGraph) -> RecoveryPrompt:
    """
    Rule-based selector — uses graph structure only, no task labels.

    Priority:
      1. structural_graph  if highlighted structural_record nodes or >= 3 BELONGS_TO edges
      2. trust_filtered    if contaminated nodes present
      3. concat            otherwise (baseline)
    """
    if has_highlighted_structural(csg) or has_many_belongs_to(csg):
        return build_structural_graph_prompt(csg)
    if has_contaminated_nodes(csg):
        return build_trust_filtered_prompt(csg)
    return build_concat_prompt(csg)
