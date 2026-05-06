"""
Contamination propagation using a source/type partial order (no numeric trust scores).

Edge direction conventions assumed here:
  derived_from:  source=derived_node,    target=dependency_node
  supersedes:    source=new_node,        target=old_node_being_replaced
  contradicts:   source=higher_trust,    target=lower_trust (set by extractor)
  supports:      source=user_fact,       target=assistant_derivation
  verified_by:   source=assistant_claim, target=tool_output

Propagation rules (fixed-point):
  A. assistant assumption/answer_candidate with no incoming SUPPORTS or VERIFIED_BY → contaminated
  B. high-trust node CONTRADICTS/SUPERSEDES lower-trust node → lower-trust contaminated/inactive
     (Rule C: do NOT contaminate both sides of CONTRADICTS)
  D. node X whose derived_from dependency (target) is contaminated or inactive → X contaminated
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum

from care.schemas import (
    ConversationStateGraph,
    StateNode,
    StateEdge,
    EdgeType,
    NodeStatus,
    SourceType,
    StateType,
)


class TrustLevel(IntEnum):
    TOOL_VERIFIED = 5
    USER_CORRECTION = 4
    USER_FACT = 3
    ASSISTANT_VERIFIED = 2       # derivation with explicit SUPPORTS from user / VERIFIED_BY tool
    ASSISTANT_DERIVATION = 1     # derivation without explicit support
    ASSISTANT_ASSUMPTION = 0     # assumption / answer_candidate without support


@dataclass
class ContaminationReport:
    contaminated_ids: list[str] = field(default_factory=list)
    inactive_ids: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)


def _node_map(csg: ConversationStateGraph) -> dict[str, StateNode]:
    return {n.id: n for n in csg.nodes}


def _incoming(node_id: str, edges: list[StateEdge]) -> list[StateEdge]:
    return [e for e in edges if e.target == node_id]


def _outgoing(node_id: str, edges: list[StateEdge]) -> list[StateEdge]:
    return [e for e in edges if e.source == node_id]


def get_trust_level(node: StateNode, csg: ConversationStateGraph) -> TrustLevel:
    if node.source == SourceType.tool:
        return TrustLevel.TOOL_VERIFIED

    nmap = _node_map(csg)

    # Check if this assistant node has a VERIFIED_BY edge pointing to a tool output
    # Edge: assistant_claim --verified_by--> tool_output
    if node.source == SourceType.assistant:
        is_tool_verified = any(
            e.type == EdgeType.verified_by
            and nmap.get(e.target, node).source == SourceType.tool
            for e in _outgoing(node.id, csg.edges)
        )
        if is_tool_verified:
            return TrustLevel.TOOL_VERIFIED

        # Derivation explicitly supported by a user fact
        # Edge: user_fact --supports--> this_node
        has_user_support = any(
            e.type == EdgeType.supports
            and nmap.get(e.source, node).source == SourceType.user
            for e in _incoming(node.id, csg.edges)
        )
        if has_user_support:
            return TrustLevel.ASSISTANT_VERIFIED

        if node.type == StateType.derivation:
            return TrustLevel.ASSISTANT_DERIVATION

        # assumption or answer_candidate without any support
        return TrustLevel.ASSISTANT_ASSUMPTION

    if node.source == SourceType.user:
        if node.type == StateType.correction:
            return TrustLevel.USER_CORRECTION
        return TrustLevel.USER_FACT

    # system → treat as high-trust constraint
    return TrustLevel.USER_FACT


def propagate_contamination(
    csg: ConversationStateGraph,
) -> tuple[ConversationStateGraph, ContaminationReport]:
    report = ContaminationReport()
    statuses: dict[str, NodeStatus] = {n.id: n.status for n in csg.nodes}
    nmap = _node_map(csg)

    def mark_contaminated(node_id: str, reason: str) -> bool:
        if statuses[node_id] == NodeStatus.contaminated:
            return False
        # Superseded (inactive) nodes stay inactive — they are retired, not "wrong"
        if statuses[node_id] == NodeStatus.inactive:
            return False
        statuses[node_id] = NodeStatus.contaminated
        if node_id not in report.contaminated_ids:
            report.contaminated_ids.append(node_id)
        report.reasons[node_id] = reason
        return True

    def mark_inactive(node_id: str, reason: str) -> bool:
        """Supersedes → inactive. Overrides contaminated (superseded nodes are retired)."""
        if statuses[node_id] == NodeStatus.inactive:
            return False
        statuses[node_id] = NodeStatus.inactive
        # Move from contaminated → inactive if needed
        if node_id in report.contaminated_ids:
            report.contaminated_ids.remove(node_id)
        if node_id not in report.inactive_ids:
            report.inactive_ids.append(node_id)
        report.reasons[node_id] = reason
        return True

    changed = True
    while changed:
        changed = False

        for node in csg.nodes:
            nid = node.id

            # Rule A: assistant assumption/answer_candidate with no incoming SUPPORTS or VERIFIED_BY
            if (
                node.source == SourceType.assistant
                and node.type in (StateType.assumption, StateType.answer_candidate)
                and statuses[nid] == NodeStatus.active
            ):
                has_support = any(
                    e.type in (EdgeType.supports, EdgeType.verified_by)
                    for e in _incoming(nid, csg.edges)
                )
                if not has_support:
                    changed |= mark_contaminated(nid, "assistant assumption/answer_candidate without support")

            # Rule B: outgoing CONTRADICTS or SUPERSEDES edges from this node
            src_trust = get_trust_level(nmap[nid], csg)
            for edge in _outgoing(nid, csg.edges):
                if edge.type not in (EdgeType.contradicts, EdgeType.supersedes):
                    continue
                tgt = nmap.get(edge.target)
                if tgt is None:
                    continue
                tgt_trust = get_trust_level(tgt, csg)
                if src_trust <= tgt_trust:
                    continue  # Rule C: only contaminate the lower-trust side

                if edge.type == EdgeType.supersedes:
                    changed |= mark_inactive(edge.target, f"superseded by {nid}")
                else:  # contradicts
                    changed |= mark_contaminated(
                        edge.target, f"contradicted by higher-trust node {nid}"
                    )

            # Rule D: derived_from a contaminated or inactive dependency
            # Edge: source=this_node (derived), target=dependency
            if statuses[nid] == NodeStatus.active:
                for edge in _outgoing(nid, csg.edges):
                    if edge.type != EdgeType.derived_from:
                        continue
                    dep_status = statuses.get(edge.target)
                    if dep_status in (NodeStatus.contaminated, NodeStatus.inactive):
                        changed |= mark_contaminated(
                            nid, f"derived_from {dep_status.value} node {edge.target}"
                        )

    updated_nodes = [
        n.model_copy(update={"status": statuses[n.id]}) for n in csg.nodes
    ]
    updated_csg = ConversationStateGraph(
        conversation_id=csg.conversation_id,
        nodes=updated_nodes,
        edges=csg.edges,
        attributes=csg.attributes,
    )
    return updated_csg, report
