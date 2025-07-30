# -*- coding: utf-8 -*-
"""A2A agent exposing LLM and document analysis skills."""

import os
import asyncio
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Message,
    MessageSendParams,
)
from a2a.utils import new_agent_text_message
from a2a.server.apps import A2AStarletteApplication

from llm_agent import LLMProxy, DocumentAnalyzer, SkillRouter


class RouterExecutor(AgentExecutor):
    """Executor dispatching to the SkillRouter."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        llm = LLMProxy(api_key)
        self.router = SkillRouter(llm, DocumentAnalyzer(llm))
        self.memory: dict[str, list[Message]] = {}

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        params: MessageSendParams = getattr(context, "params", context._params)
        user_message: Message = params.message
        context_id = getattr(params, "context_id", None)

        if context_id is not None:
            history = self.memory.setdefault(context_id, [])
            history.append(user_message)

        user_text = " ".join(
            part.text for part in user_message.parts if getattr(part, "text", None)
        )
        try:
            transformed = await self.router.execute(user_text)
        except Exception as exc:
            transformed = f"Erreur: {exc}"

        response_message = new_agent_text_message(transformed)
        await event_queue.enqueue_event(response_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("cancel not supported")


llm_skill = AgentSkill(
    id="llm-proxy",
    name="LLM",
    description="Proxy vers le modèle GPT/Claude via OpenAI API.",
    tags=["llm"],
    examples=["bonjour"],
    input_modes=["text"],
    output_modes=["text"],
)

summary_skill = AgentSkill(
    id="doc-summary",
    name="Analyse de documents",
    description="Télécharge un PDF/URL et renvoie un résumé.",
    tags=["summary"],
    examples=["https://example.com/doc.pdf"],
    input_modes=["text"],
    output_modes=["text"],
)

agent_card = AgentCard(
    name="LLM Agent",
    description="Proxy LLM avec résumé de documents.",
    url="http://localhost:9999/",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[llm_skill, summary_skill],
    supports_authenticated_extended_card=False,
)

request_handler = DefaultRequestHandler(
    agent_executor=RouterExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
).build()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("a2a_llm_agent:app", host="0.0.0.0", port=9999, reload=True)
