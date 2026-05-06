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

Edge rules (only add when relationship is explicit in the text):
- derived_from: source=derived_node, target=dependency_node
- supersedes: source=new_node, target=old_node_it_replaces
- contradicts: source=higher_trust_node, target=lower_trust_node
- supports: source=user_fact, target=assistant_derivation_it_backs
  (see SUPPORTS RULES below — this edge is STRICT)
- verified_by: source=assistant_claim, target=tool_output_confirming_it
- belongs_to: source=structural_record_cell, target=table_metadata_node

Node ID format: "{conversation_id}_{turn_index}_{seq}" where seq starts at 0 per turn.

═══════════════════════════════════════════════════════════════
SUPPORTS EDGE RULES (STRICT — read carefully before emitting)
═══════════════════════════════════════════════════════════════

A SUPPORTS edge from user node U to assistant node A is valid ONLY when:
  U contains a SPECIFIC VALUE (number, name, date) that A uses directly in its claim.

Do NOT emit SUPPORTS in ANY of these cases:
  1. The assistant claim contains placeholder language such as:
       "I'll assume", "let me say", "let's assume", "let's call it",
       "let's say", "$X", "Y dollars", "let me estimate", "let me guess"
     These are invented values — no user fact "supports" an invented number.
  2. U merely describes the problem context and A "responded to" or "referenced" U.
     Being a response to a turn is NOT support.
  3. A invents intermediate values not present anywhere in the user turns.

Node typing rule for assistant turns:
  If the assistant turn contains phrases like "Let's assume", "I'll assume",
  "let me say", or introduces placeholder numbers/values not given by the user,
  type it as "assumption", NOT "answer_candidate" or "derivation".
  Type as "derivation" only when the computation uses ONLY values the user stated.
  Type as "answer_candidate" only for the final complete answer using real facts.

derived_from edges for multi-turn reasoning:
  If assistant Turn N builds on an intermediate result from assistant Turn N-1
  (uses its numeric output as an input), add:
    derived_from: source=Turn_N_node, target=Turn_(N-1)_node

═══════════════════════
SUPPORTS EXAMPLES
═══════════════════════

SCENARIO: Math problem delivered in shards.
  User Turn 0: "Alice has been baking for 3 years."
  Asst Turn 0: "Let me assume she bakes 10 loaves per year. 3 × 10 = 30 loaves total."
  User Turn 1: "She bakes 15 loaves per year."
  Asst Turn 1: "With 15 loaves/year and 3 years: 3 × 15 = 45 loaves total."

CORRECT extraction:
  Asst Turn 0 node: type="assumption" (uses invented "10 loaves" not given by user)
  Asst Turn 1 node: type="derivation" (uses "15 loaves" and "3 years" from user)
  Edge: User Turn 1 ("she bakes 15 loaves/year") --supports--> Asst Turn 1 ("3×15=45") ✓
    Reason: User Turn 1 contains the SPECIFIC VALUE "15" used in Turn 1's derivation.
  Edge: Asst Turn 1 --derived_from--> Asst Turn 0 ✗  (Turn 1 recalculates from scratch)
  NO edge: User Turn 0 --supports--> Asst Turn 0
    Reason: "3 years" is real, but Turn 0's "10 loaves/year" is INVENTED by the assistant.
    The user fact does not supply the value "10" — so no SUPPORTS.

INCORRECT (do NOT do this):
  Edge: User Turn 0 ("Alice has baked for 3 years") --supports--> Asst Turn 0 ("30 loaves")
    Reason: Asst Turn 0 invented "10 loaves/year" — the user never said this.
    "3 years" appears in the derivation but the key intermediate value is invented.

═══════════════════════
END SUPPORTS RULES
═══════════════════════

═══════════════════════════════════════════════════════════════
DATA-TO-TEXT / TABLE TASK DETECTION AND EXTRACTION (MANDATORY)
═══════════════════════════════════════════════════════════════

TRIGGER: If ANY user turn contains HTML table markup (<table>, <tr>, <td>, <th>)
OR the text class="highlighted", you are in a D2T task. Apply ALL rules below
instead of the general rules for those turns.

D2T RULE 1 — SKIP REFERENCE EXAMPLES
The first user turn in D2T tasks contains example sentences ("Here's 10 examples...").
These are reference context only. Extract them as exactly ONE metadata node:
  {type: "metadata", text: "Reference table-description examples provided.", attributes: {}}
Do NOT create one fact/metadata node per example sentence.

D2T RULE 2 — PARSE EVERY HTML CELL AS A structural_record NODE
For the turn containing <table>...</table>:
  a. First, create one metadata node for the table header (column names from <th> elements
     in the FIRST row). Example: {type:"metadata", text:"Table columns: Event, Gold, Silver"}
  b. For EACH <td> element AND each <th> element that is NOT in the header row,
     create ONE structural_record node. Never lump multiple cells into a single node.
  c. Detect highlighting: if the <td> or <th> tag contains class="highlighted",
     set "highlighted": true. All other cells get "highlighted": false.
  d. Fill all six required attributes for every structural_record:
     {
       "table_title": "<title extracted from surrounding context or 'Table'>",
       "row_id": "row_<N>" where N is the 0-based row index,
       "row_header": "<text of the leftmost <th> in this row, or row_N if none>",
       "column": "<the column header for this cell>",
       "value": "<the cell's text content, stripped of HTML>",
       "highlighted": true | false
     }

D2T RULE 3 — BELONGS_TO EDGES
After creating the table metadata node and all structural_record nodes, add
a belongs_to edge from EVERY structural_record node to the table metadata node:
  {source: "<cell_node_id>", target: "<table_metadata_node_id>",
   type: "belongs_to", rationale: "cell belongs to table"}

D2T RULE 4 — ASSISTANT RESPONSES
Assistant turns in D2T = answer_candidate nodes (one per sentence).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE — CORRECT D2T EXTRACTION (conversation_id = "ex")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Input Turn 0 (user): "Here's 10 examples: Alice won gold. Bob won silver. ..."
Input Turn 1 (user): "Table:
<table>
<tr> <th>Event</th><th class=\"highlighted\">Gold</th><th>Silver</th></tr>
<tr> <th>100m</th><td class=\"highlighted\">Alice (USA)</td><td>Bob (GBR)</td></tr>
<tr> <th>200m</th><td>Carol (AUS)</td><td class=\"highlighted\">Dana (CAN)</td></tr>
</table>"
Input Turn 1 (assistant): "Alice won the 100m gold for USA."

CORRECT output (abbreviated):
{
  "nodes": [
    {"id":"ex_0_0","turn_index":0,"source":"user","type":"metadata",
     "text":"Reference table-description examples provided.","entities":[],"attributes":{},"status":"active","conversation_id":"ex"},
    {"id":"ex_1_0","turn_index":1,"source":"user","type":"metadata",
     "text":"Table columns: Event, Gold, Silver","entities":[],"attributes":{},"status":"active","conversation_id":"ex"},
    {"id":"ex_1_1","turn_index":1,"source":"user","type":"structural_record",
     "text":"100m | Gold: Alice (USA) [highlighted]","entities":["Alice","USA"],
     "attributes":{"table_title":"Table","row_id":"row_0","row_header":"100m","column":"Gold","value":"Alice (USA)","highlighted":true},"status":"active","conversation_id":"ex"},
    {"id":"ex_1_2","turn_index":1,"source":"user","type":"structural_record",
     "text":"100m | Silver: Bob (GBR)","entities":["Bob","GBR"],
     "attributes":{"table_title":"Table","row_id":"row_0","row_header":"100m","column":"Silver","value":"Bob (GBR)","highlighted":false},"status":"active","conversation_id":"ex"},
    {"id":"ex_1_3","turn_index":1,"source":"user","type":"structural_record",
     "text":"200m | Gold: Carol (AUS)","entities":["Carol","AUS"],
     "attributes":{"table_title":"Table","row_id":"row_1","row_header":"200m","column":"Gold","value":"Carol (AUS)","highlighted":false},"status":"active","conversation_id":"ex"},
    {"id":"ex_1_4","turn_index":1,"source":"user","type":"structural_record",
     "text":"200m | Silver: Dana (CAN) [highlighted]","entities":["Dana","CAN"],
     "attributes":{"table_title":"Table","row_id":"row_1","row_header":"200m","column":"Silver","value":"Dana (CAN)","highlighted":true},"status":"active","conversation_id":"ex"},
    {"id":"ex_1_5","turn_index":1,"source":"assistant","type":"answer_candidate",
     "text":"Alice won the 100m gold for USA.","entities":["Alice","USA"],"attributes":{},"status":"active","conversation_id":"ex"}
  ],
  "edges": [
    {"source":"ex_1_1","target":"ex_1_0","type":"belongs_to","rationale":"cell belongs to table"},
    {"source":"ex_1_2","target":"ex_1_0","type":"belongs_to","rationale":"cell belongs to table"},
    {"source":"ex_1_3","target":"ex_1_0","type":"belongs_to","rationale":"cell belongs to table"},
    {"source":"ex_1_4","target":"ex_1_0","type":"belongs_to","rationale":"cell belongs to table"}
  ],
  "attributes": {}
}

WRONG — do NOT do this (collapses entire table into a fact node):
  {"id":"ex_1_0","type":"fact","text":"The table shows 100m and 200m sprint results...","attributes":{}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END D2T RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
