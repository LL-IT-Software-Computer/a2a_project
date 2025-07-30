# -*- coding: utf-8 -*-
"""LLM and document summarization agent."""

import os
import asyncio

try:
    import openai  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    openai = None

import httpx


class LLMProxy:
    """Very small wrapper around the OpenAI chat API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    async def run(self, prompt: str) -> str:
        if openai is None:
            raise RuntimeError("openai package is not installed")
        client = openai.AsyncOpenAI(api_key=self.api_key)
        resp = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content


class DocumentAnalyzer:
    """Fetches a document from a URL and returns a short summary using the LLMProxy."""

    def __init__(self, llm: LLMProxy) -> None:
        self.llm = llm

    async def analyze(self, url: str) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10.0)
            r.raise_for_status()
            text = r.text[:2000]
        prompt = f"Résume en français ce contenu:\n{text}"
        return await self.llm.run(prompt)


class SkillRouter:
    """Naive router that chooses the right skill based on parameters."""

    def __init__(self, llm: LLMProxy, analyzer: DocumentAnalyzer) -> None:
        self.llm = llm
        self.analyzer = analyzer

    async def execute(self, message: str) -> str:
        if message.startswith("http://") or message.startswith("https://"):
            return await self.analyzer.analyze(message)
        return await self.llm.run(message)


async def demo() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    router = SkillRouter(LLMProxy(api_key), DocumentAnalyzer(LLMProxy(api_key)))
    res = await router.execute("Bonjour")
    print(res)


if __name__ == "__main__":
    asyncio.run(demo())
