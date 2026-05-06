from care.schemas import ConversationStateGraph, RecoveryPrompt, SourceType


def build_concat_prompt(csg: ConversationStateGraph) -> RecoveryPrompt:
    """Baseline: concatenate all user-turn nodes in turn order, no filtering."""
    user_nodes = sorted(
        [n for n in csg.nodes if n.source == SourceType.user],
        key=lambda n: (n.turn_index, n.id),
    )
    included_ids = [n.id for n in user_nodes]
    excluded_ids = [n.id for n in csg.nodes if n.id not in set(included_ids)]

    return RecoveryPrompt(
        conversation_id=csg.conversation_id,
        method="concat",
        prompt="\n".join(n.text for n in user_nodes),
        included_node_ids=included_ids,
        excluded_node_ids=excluded_ids,
    )
