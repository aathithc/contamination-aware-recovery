from care.schemas import (
    ConversationStateGraph,
    RecoveryPrompt,
    SourceType,
    NodeStatus,
    StateType,
)


def build_trust_filtered_prompt(csg: ConversationStateGraph) -> RecoveryPrompt:
    """Include active user/tool nodes and uncontaminated assistant derivations."""
    included: list = []
    excluded: list = []

    for node in sorted(csg.nodes, key=lambda n: (n.turn_index, n.id)):
        keep = False
        if node.source in (SourceType.user, SourceType.tool):
            keep = node.status == NodeStatus.active
        elif node.source == SourceType.assistant and node.type == StateType.derivation:
            keep = node.status == NodeStatus.active
        (included if keep else excluded).append(node)

    return RecoveryPrompt(
        conversation_id=csg.conversation_id,
        method="trust_filtered",
        prompt="\n".join(n.text for n in included),
        included_node_ids=[n.id for n in included],
        excluded_node_ids=[n.id for n in excluded],
    )
