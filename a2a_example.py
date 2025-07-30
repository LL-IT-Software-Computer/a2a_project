# -*- coding: utf-8 -*-
"""
Agent A2A d’exemple « Echo+ » – version 1.0.3
Transforme le texte reçu (uppercase / lowercase / snake_case).
"""

import asyncio
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, MessageSendParams
from a2a.utils import new_agent_text_message
from a2a.server.apps import A2AStarletteApplication


# --------------------------------------------------------------------------- #
# Logique de transformation                                                   #
# --------------------------------------------------------------------------- #
class EchoAgent:
    async def transform(self, text: str, style: str) -> str:
        await asyncio.sleep(0.05)
        if style == "uppercase":
            return text.upper()
        if style == "lowercase":
            return text.lower()
        if style == "snake_case":
            return text.replace(" ", "_").lower()
        return text


# --------------------------------------------------------------------------- #
# Executor                                                                    #
# --------------------------------------------------------------------------- #
class EchoAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = EchoAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        # -- 1. Paramètres ---------------------------------------------------
        params: MessageSendParams = getattr(context, "params", context._params)
        user_message = params.message                       # obj ou dict
        style = getattr(params, "style", "uppercase")

        # -- 2. Re‑sérialiser pour avoir un dict JSON homogène --------------
        raw_msg: dict[str, Any] = (
            user_message.model_dump()                      # Pydantic -> dict
            if hasattr(user_message, "model_dump")
            else user_message                              # déjà dict
        )

        # -- 3. Extraire le texte -------------------------------------------
        texts = [
            part.get("text", "")
            for part in raw_msg.get("parts", [])
            if part.get("kind") == "text"
        ]
        user_text = " ".join(texts).strip()

        # -- 4. Transformer et répondre -------------------------------------
        transformed = await self.agent.transform(user_text, style)
        await event_queue.enqueue_event(new_agent_text_message(transformed))

    async def cancel(self, *_):
        raise Exception("cancel not supported")


# --------------------------------------------------------------------------- #
# AgentCard & application                                                     #
# --------------------------------------------------------------------------- #
skill = AgentSkill(
    id="echo-plus",
    name="Echo+",
    description="Retourne le texte selon le style demandé.",
    tags=["echo", "style"],
    examples=["bonjour", "hello"],
    input_modes=["text"],
    output_modes=["text"],
)

agent_card = AgentCard(
    name="Echo+ Agent",
    description="Un agent qui applique différents styles aux messages.",
    url="http://localhost:9999/",
    version="1.0.3",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
    supports_authenticated_extended_card=False,
)

request_handler = DefaultRequestHandler(
    agent_executor=EchoAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
).build()
