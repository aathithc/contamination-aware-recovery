import json
import logging
import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from care.schemas import ConversationStateGraph

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMExtractor(Protocol):
    def extract_state(
        self, conversation_id: str, turns: list[dict], max_calls: int = 1
    ) -> ConversationStateGraph: ...


def _empty_graph(conversation_id: str, failed: bool = False) -> ConversationStateGraph:
    attrs = {"failed_extraction": True} if failed else {}
    return ConversationStateGraph(
        conversation_id=conversation_id,
        nodes=[],
        edges=[],
        attributes=attrs,
    )


def _parse_json_output(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _validate(raw: dict) -> ConversationStateGraph:
    return ConversationStateGraph.model_validate(raw)


class MockExtractor:
    """Loads pre-built graphs from JSON fixture files — no API calls needed."""

    def __init__(self, fixture_dir: Path):
        self.fixture_dir = fixture_dir

    def extract_state(
        self, conversation_id: str, turns: list[dict], max_calls: int = 1
    ) -> ConversationStateGraph:
        fixture_path = self.fixture_dir / f"{conversation_id}.json"
        if not fixture_path.exists():
            logger.warning("No fixture for %s, returning empty graph", conversation_id)
            return _empty_graph(conversation_id)
        with open(fixture_path) as f:
            raw = json.load(f)
        return ConversationStateGraph.model_validate(raw)


class OpenAIExtractor:
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_state(
        self, conversation_id: str, turns: list[dict], max_calls: int = 1
    ) -> ConversationStateGraph:
        from care.extraction.prompts import build_extraction_messages

        messages = build_extraction_messages(conversation_id, turns)
        raw_text = ""
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
                raw_text = response.choices[0].message.content
                return _validate(_parse_json_output(raw_text))
            except Exception as e:
                if attempt == 0:
                    logger.warning(
                        "Extraction attempt 1 failed for %s: %s. Retrying.", conversation_id, e
                    )
                    messages.append({"role": "assistant", "content": raw_text})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Your previous output was invalid. Error: {e}\n"
                            "Return only valid JSON matching the schema."
                        ),
                    })
                else:
                    logger.error("Extraction failed after retry for %s: %s", conversation_id, e)
                    return _empty_graph(conversation_id, failed=True)
        return _empty_graph(conversation_id, failed=True)


class AnthropicExtractor:
    def __init__(self, model: str = "claude-opus-4-7", api_key: str | None = None):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def extract_state(
        self, conversation_id: str, turns: list[dict], max_calls: int = 1
    ) -> ConversationStateGraph:
        from care.extraction.prompts import build_extraction_messages

        messages = build_extraction_messages(conversation_id, turns)
        system_prompt = messages[0]["content"]
        user_messages = [m for m in messages if m["role"] != "system"]

        raw_text = ""
        for attempt in range(2):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=user_messages,
                )
                raw_text = response.content[0].text
                return _validate(_parse_json_output(raw_text))
            except Exception as e:
                if attempt == 0:
                    logger.warning(
                        "Extraction attempt 1 failed for %s: %s. Retrying.", conversation_id, e
                    )
                    user_messages.append({"role": "assistant", "content": raw_text})
                    user_messages.append({
                        "role": "user",
                        "content": (
                            f"Your previous output was invalid. Error: {e}\n"
                            "Return only valid JSON in ```json ... ``` fences."
                        ),
                    })
                else:
                    logger.error("Extraction failed after retry for %s: %s", conversation_id, e)
                    return _empty_graph(conversation_id, failed=True)
        return _empty_graph(conversation_id, failed=True)
