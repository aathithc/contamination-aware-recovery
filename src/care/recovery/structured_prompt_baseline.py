"""
Structured Prompt Baseline for Data-to-Text (D2T) tasks.

Rewrites raw conversation turns into a four-section Table/Highlighted/Context/Instruction
format. Uses gpt-4o-mini when an OpenAI client is provided; falls back to rule-based
parsing otherwise. Does NOT perform graph extraction — that is what makes it a baseline.
"""

from __future__ import annotations

import logging
from typing import Any

from care.schemas import ConversationStateGraph, RecoveryPrompt, SourceType

logger = logging.getLogger(__name__)

_LLM_SYSTEM_PROMPT = """\
You are a Data-to-Text prompt formatter.
Given raw multi-turn conversation turns about a table, extract and reformat into exactly four sections.
Output ONLY the formatted result — no preamble, no explanation.

Table:
<reproduce table structure from user input>

Highlighted:
<list only the cells the user highlighted or emphasised>

Context:
<corrections, constraints, or additional facts the user stated>

Instruction:
<the user's final task or question as a single imperative sentence>
"""


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

def _rule_based_format(turns: list[dict]) -> str:
    """Parse turns heuristically into four sections without an LLM."""
    table_lines: list[str] = []
    highlighted_lines: list[str] = []
    context_lines: list[str] = []
    instruction_lines: list[str] = []

    instruction_starters = ("describe", "generate", "write", "summarize", "summarise")

    for turn in turns:
        user_text = turn.get("user_input", "")
        if not user_text:
            continue
        for raw_line in user_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            lo = line.lower()
            if "|" in line or lo.startswith("table:"):
                table_lines.append(line)
            elif "[highlighted]" in lo or "highlighted" in lo:
                highlighted_lines.append(line)
            elif "?" in line or lo.startswith(instruction_starters):
                instruction_lines.append(line)
            else:
                context_lines.append(line)

    table_sec = "\n".join(table_lines) if table_lines else "(none)"
    highlighted_sec = "\n".join(highlighted_lines) if highlighted_lines else "(none)"
    context_sec = "\n".join(context_lines) if context_lines else "(none)"
    instruction_sec = " ".join(instruction_lines) if instruction_lines else "(none)"

    return (
        f"Table:\n{table_sec}\n\n"
        f"Highlighted:\n{highlighted_sec}\n\n"
        f"Context:\n{context_sec}\n\n"
        f"Instruction:\n{instruction_sec}"
    )


# ---------------------------------------------------------------------------
# LLM rewrite
# ---------------------------------------------------------------------------

def _llm_format(turns: list[dict], client: Any, model: str) -> str:
    """Call gpt-4o-mini to reformat turns into four sections."""
    turns_text = ""
    for i, turn in enumerate(turns):
        user_input = turn.get("user_input", "")
        agent_response = turn.get("agent_response", "")
        turns_text += f"--- Turn {i} ---\nUser: {user_input}\nAgent: {agent_response}\n\n"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _LLM_SYSTEM_PROMPT},
            {"role": "user", "content": turns_text.strip()},
        ],
        timeout=45.0,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_structured_prompt(
    turns: list[dict],
    conversation_id: str,
    openai_client: Any | None = None,
    model: str = "gpt-4o-mini",
) -> RecoveryPrompt:
    """
    Rewrite raw turns into Table/Highlighted/Context/Instruction format.

    Parameters
    ----------
    turns:
        List of dicts with ``user_input`` and ``agent_response`` keys.
    conversation_id:
        Identifier for the conversation.
    openai_client:
        An instantiated ``openai.OpenAI`` client.  When ``None``, rule-based
        parsing is used instead.
    model:
        OpenAI model to use when ``openai_client`` is provided.

    Returns
    -------
    RecoveryPrompt
    """
    if openai_client is not None:
        try:
            prompt_text = _llm_format(turns, openai_client, model)
        except Exception as exc:
            logger.warning(
                "LLM formatting failed for %s (%s); falling back to rule-based.",
                conversation_id,
                exc,
            )
            prompt_text = _rule_based_format(turns)
    else:
        prompt_text = _rule_based_format(turns)

    # Every node ID that was used = all turns (no graph, so we track nothing)
    return RecoveryPrompt(
        conversation_id=conversation_id,
        method="structured_prompt_baseline",
        prompt=prompt_text,
        included_node_ids=[],
        excluded_node_ids=[],
    )


def build_structured_prompt_from_csg(
    csg: ConversationStateGraph,
    openai_client: Any | None = None,
    model: str = "gpt-4o-mini",
) -> RecoveryPrompt:
    """
    Reconstruct turns from CSG nodes and build a structured prompt.

    Nodes are grouped by turn_index; user nodes supply ``user_input`` and
    assistant nodes supply ``agent_response``.
    """
    # Build turn list from CSG nodes
    turn_map: dict[int, dict[str, str]] = {}
    for node in sorted(csg.nodes, key=lambda n: (n.turn_index, n.id)):
        t = turn_map.setdefault(node.turn_index, {"user_input": "", "agent_response": ""})
        if node.source == SourceType.user:
            sep = " " if t["user_input"] else ""
            t["user_input"] += sep + node.text
        elif node.source == SourceType.assistant:
            sep = " " if t["agent_response"] else ""
            t["agent_response"] += sep + node.text

    turns = [turn_map[k] for k in sorted(turn_map)]

    return build_structured_prompt(
        turns=turns,
        conversation_id=csg.conversation_id,
        openai_client=openai_client,
        model=model,
    )
