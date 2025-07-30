import asyncio
from uuid import uuid4

from httpx import AsyncClient
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)

def extract_text(response_obj) -> str:
    """
    Renvoie la chaîne de texte contenue dans la réponse A2A
    (non‑streaming ou chunk streaming), quel que soit le type d’objet.
    """
    data = response_obj.model_dump()          # -> dict Python
    return data["result"]["parts"][0]["text"] # 'SALUT', 'bonjour_les_amis', …

async def main() -> None:
    base_url = "http://localhost:9999"

    async with AsyncClient() as httpx_client:
        # 1. Découvrir la carte A2A
        resolver   = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        client     = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

        # 2. Charger le payload
        payload = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "Bonjour les amis"}],
                "messageId": uuid4().hex,
            },
            "style": "snake_case",
            "context_id": "demo",
        }

        # ----------- Non‑streaming -----------
        req = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))
        res = await client.send_message(req)
        print("Réponse non‑streaming :", extract_text(res))

        # ----------- Streaming ---------------
        stream_req = SendStreamingMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**payload)
        )
        print("Chunks streaming :")
        async for chunk in client.send_message_streaming(stream_req):
            print(" •", extract_text(chunk))

if __name__ == "__main__":
    asyncio.run(main())
