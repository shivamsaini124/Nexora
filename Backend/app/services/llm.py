from openai import AsyncOpenAI


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model_name: str):
        self.model_name = model_name
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def complete(self, messages: list[dict[str, str]], **params) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **params,
        )
        return response.choices[0].message.content or ""

    async def close(self) -> None:
        await self.client.close()


class ModelRouter:
    def __init__(self, coding_client: LLMClient, general_client: LLMClient):
        self.coding_client = coding_client
        self.general_client = general_client

    def route(self, intent: str) -> LLMClient:
        return (
            self.coding_client
            if intent.lower().startswith("coding")
            else self.general_client
        )
