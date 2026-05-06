from care.schemas import ConversationStateGraph, StateNode, StateType, EdgeType, NodeStatus


def get_highlighted_cells(csg: ConversationStateGraph) -> list[StateNode]:
    return [
        n for n in csg.nodes
        if n.type == StateType.structural_record
        and n.attributes.get("highlighted", False)
        and n.status != NodeStatus.contaminated
    ]


def get_cell_neighborhood(cell: StateNode, csg: ConversationStateGraph) -> list[StateNode]:
    """Return 1-hop BELONGS_TO neighbors of a structural cell."""
    nmap = {n.id: n for n in csg.nodes}
    return [
        nmap[e.target]
        for e in csg.edges
        if e.source == cell.id and e.type == EdgeType.belongs_to and e.target in nmap
    ]


def linearize_structural(csg: ConversationStateGraph) -> str:
    """Build the structured linearization used by the structural_graph recovery method."""
    highlighted = get_highlighted_cells(csg)
    if not highlighted:
        return ""

    # Group by table title
    tables: dict[str, list[StateNode]] = {}
    for cell in highlighted:
        title = cell.attributes.get("table_title", "Unknown Table")
        tables.setdefault(title, []).append(cell)

    # Collect supporting context from 1-hop neighborhoods
    seen: set[str] = {c.id for c in highlighted}
    supporting: list[str] = []
    for cell in highlighted:
        for neighbor in get_cell_neighborhood(cell, csg):
            if neighbor.id not in seen:
                seen.add(neighbor.id)
                supporting.append(neighbor.text)

    lines: list[str] = []
    for table_title, cells in tables.items():
        lines.append(f"Table: {table_title}")
        lines.append("Relevant highlighted cells:")
        for cell in cells:
            row = cell.attributes.get("row_header") or cell.attributes.get("row_id", "?")
            col = cell.attributes.get("column", "?")
            val = cell.attributes.get("value", cell.text)
            lines.append(f"  - Row: {row}")
            lines.append(f"    Column: {col}")
            lines.append(f"    Value: {val}")
            lines.append(f"    Highlighted: true")

    if supporting:
        lines.append("Supporting context:")
        for ctx in supporting:
            lines.append(f"  - {ctx}")

    lines.append("")
    lines.append("Instruction:")
    lines.append(
        "Write one faithful sentence describing only the highlighted cell(s). "
        "Preserve row/column alignment. Do not mention non-highlighted cells unless necessary."
    )

    return "\n".join(lines)
