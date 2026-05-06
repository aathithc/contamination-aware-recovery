from care.schemas import ConversationStateGraph, EdgeType, StateType, NodeStatus, SourceType


def has_highlighted_structural(csg: ConversationStateGraph) -> bool:
    return any(
        n.type == StateType.structural_record and n.attributes.get("highlighted", False)
        for n in csg.nodes
    )


def has_many_belongs_to(csg: ConversationStateGraph, threshold: int = 3) -> bool:
    return sum(1 for e in csg.edges if e.type == EdgeType.belongs_to) >= threshold


def has_contaminated_nodes(csg: ConversationStateGraph) -> bool:
    return any(n.status == NodeStatus.contaminated for n in csg.nodes)


def count_active_user_nodes(csg: ConversationStateGraph) -> int:
    return sum(
        1 for n in csg.nodes
        if n.source == SourceType.user and n.status == NodeStatus.active
    )
