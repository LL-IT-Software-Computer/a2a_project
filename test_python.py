import asyncio
from uuid import uuid4
from httpx import AsyncClient
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest, SendStreamingMessageRequest

async def main():
    base_url = "http://localhost:9999"
    async with AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

        # Non-streaming
        payload = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "salut"}],
                "messageId": uuid4().hex,
            },
            "style": "snake_case",
            "context_id": "demo",
        }
        req = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))
        res = await client.send_message(req)
        print("Réponse non‑streaming :", res.model_dump())

        # Streaming
        stream_req = SendStreamingMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))
        async for chunk in client.send_message_streaming(stream_req):
            print("Chunk streaming :", chunk.model_dump())

if __name__ == "__main__":
    asyncio.run(main())
