EXTRACTION_SYSTEM_PROMPT = """\
You are a precise state-extraction engine for multi-turn LLM conversations.

Task: decompose a conversation into atomic typed state units (nodes) and typed directed edges.

Output ONLY valid JSON — no markdown fences, no explanation, nothing else.

JSON schema:
{
  "conversation_id": "<id>",
  "nodes": [
    {
      "id": "<conversation_id>_<turn_index>_<seq>",
      "conversation_id": "<id>",
      "turn_index": <int>,
      "source": "user" | "assistant" | "tool" | "system",
      "type": "fact" | "correction" | "constraint" | "assumption" | "derivation"
             | "structural_record" | "answer_candidate" | "metadata",
      "text": "<atomic claim, one sentence>",
      "entities": ["<named entity>"],
      "attributes": {},
      "status": "active"
    }
  ],
  "edges": [
    {
      "source": "<node_id>",
      "target": "<node_id>",
      "type": "supports" | "contradicts" | "supersedes" | "derived_from"
             | "belongs_to" | "verified_by" | "requires",
      "rationale": "<one-phrase reason>"
    }
  ],
  "attributes": {}
}

Node extraction rules:
1. One atomic claim per node. Split compound sentences.
2. user turns → type: fact, constraint, correction, or metadata
3. assistant turns → type: assumption, derivation, or answer_candidate
4. tool outputs → type: fact or structural_record (source: "tool")
5. system messages → type: metadata or constraint (source: "system")
6. All status fields must be "active". Contamination is set downstream.

For Data2Text / table tasks, each cell is a structural_record node with attributes:
  {
    "table_title": "<title>",
    "row_id": "<row identifier>",
    "row_header": "<row label>",
    "column": "<column label>",
    "value": "<cell value>",
    "highlighted": true | false
  }

Edge rules (only add when relationship is explicit in the text):
- derived_from: source=derived_node, target=dependency_node
  (assistant final answer DERIVED_FROM its assumption/fact dependency)
- supersedes: source=new_node, target=old_node_it_replaces
  (user correction SUPERSEDES older conflicting node)
- contradicts: source=higher_trust_node, target=lower_trust_node
  (user fact CONTRADICTS assistant assumption asserting opposite value)
- supports: source=user_fact, target=assistant_derivation_it_backs
  (a user fact that explicitly endorses an assistant derivation)
- verified_by: source=assistant_claim, target=tool_output_confirming_it
  (assistant claim VERIFIED_BY tool output)
- belongs_to: source=structural_record_cell, target=row_or_table_node

Node ID format: "{conversation_id}_{turn_index}_{seq}" where seq starts at 0 per turn.
"""

EXTRACTION_USER_TEMPLATE = """\
Extract the state graph for this conversation.

Conversation ID: {conversation_id}

Turns:
{turns_formatted}

Return ONLY the JSON object. No markdown, no preamble, no trailing text.\
"""


def format_turns(turns: list[dict]) -> str:
    lines = []
    for turn in turns:
        turn_id = turn.get("turn_id", "?")
        user_input = turn.get("user_input", "")
        agent_response = turn.get("agent_response", "")
        if user_input:
            lines.append(f"[Turn {turn_id}] User: {user_input}")
        if agent_response:
            lines.append(f"[Turn {turn_id}] Assistant: {agent_response}")
    return "\n".join(lines)


def build_extraction_messages(conversation_id: str, turns: list[dict]) -> list[dict]:
    return [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": EXTRACTION_USER_TEMPLATE.format(
                conversation_id=conversation_id,
                turns_formatted=format_turns(turns),
            ),
        },
    ]
