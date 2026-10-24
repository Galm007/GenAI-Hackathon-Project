"""Explicitly fictional, offline providers for FAKE_LLM. Never use for real evaluations."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from . import llm

FIXTURES = Path(__file__).resolve().parents[3] / "data/fixtures"


def install():
    from .agents.nodes import dossier_parser

    originals = llm.parse, llm.stream_text, dossier_parser.embed_one

    async def parse(schema, **_):
        await asyncio.sleep(0)
        return schema.model_validate_json((FIXTURES / f"{schema.__name__}.json").read_text())

    async def stream_text(*, messages, on_text, **_):
        text = json.dumps(messages[-1]["content"])
        turn = min(4, text.count("[Turn ") + 1)
        content = json.loads((FIXTURES / "debate.json").read_text())[str(turn)]
        for piece in re.findall(r"\S+\s*", content):
            on_text(piece)
            await asyncio.sleep(0)
        return content

    async def embed_one(_):
        # Shape fixture only: this zero vector is not a semantic embedding or retrieval evidence.
        return json.loads((FIXTURES / "profile_embedding.json").read_text())

    llm.parse, llm.stream_text, dossier_parser.embed_one = parse, stream_text, embed_one

    def restore():
        llm.parse, llm.stream_text, dossier_parser.embed_one = originals

    return restore
