# -*- coding: utf-8 -*-
"""
Agent A2A d’exemple « Echo+ ».

Ce petit serveur illustre un agent « ping‑pong » personnalisable :

* Choix de la transformation (« style ») : MAJUSCULES, minuscules,
  *snake_case*, etc.
* Mémoire très simple par `context_id` pour répondre à un ping‑pong de base.

Cette nouvelle version remplace l’ancien agent « Uppercase » en le
généralisant.
"""

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


# --------------------------------------------------------------------------- #
# Logique métier : transformer un texte selon un "style"                      #
# --------------------------------------------------------------------------- #
class EchoAgent:
    """Agent minimal permettant plusieurs styles de transformation."""

    async def transform(self, text: str, style: str) -> str:
        """Applique la transformation demandée."""
        await asyncio.sleep(0.1)  # petite latence simulée

        if style == "uppercase":
            return text.upper()
        if style == "lowercase":
            return text.lower()
        if style == "snake_case":
            return text.replace(" ", "_").lower()

        # Style inconnu : renvoyer tel quel
        return text


# --------------------------------------------------------------------------- #
# Exécuteur qui relie l’agent aux requêtes A2A                                #
# --------------------------------------------------------------------------- #
class EchoAgentExecutor(AgentExecutor):
    """Relie l’agent Echo+ aux requêtes A2A."""

    def __init__(self) -> None:
        self.agent = EchoAgent()
        self.memory: dict[str, list[Message]] = {}
        
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Gère les appels ``message/send`` et ``message/stream``."""

        # 1. Paramètres et petite mémoire
        params: MessageSendParams = getattr(context, "params", context._params)
        user_message: Message = params.message
        style = getattr(params, "style", "uppercase")
        context_id = getattr(params, "context_id", None)

        if context_id is not None:
            history = self.memory.setdefault(context_id, [])
            history.append(user_message)

        # 2. Concaténer les morceaux de texte
        user_text = " ".join(
            part.text for part in user_message.parts if getattr(part, "text", None)
        )

        # 3. Transformer selon le style demandé
        transformed = await self.agent.transform(user_text, style)

        # 4. Enfiler la réponse (IMPORTANT : await)
        response_message = new_agent_text_message(transformed)
        await event_queue.enqueue_event(response_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Annulation non prise en charge pour cet agent."""
        raise Exception("cancel not supported")


# --------------------------------------------------------------------------- #
# Définition du skill et de la carte agent                                    #
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
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
    supports_authenticated_extended_card=False,
)

# --------------------------------------------------------------------------- #
# Construction et démarrage de l’application Starlette                        #
# --------------------------------------------------------------------------- #
request_handler = DefaultRequestHandler(
    agent_executor=EchoAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

# Application ASGI exposée pour Uvicorn
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
).build()

# Lance le serveur avec :
#   uvicorn a2a_example:app --host 0.0.0.0 --port 9999 --reload
