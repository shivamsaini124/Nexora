import asyncio
from datetime import datetime, timezone
from typing import Any

from ..schemas import MemoryRecord


class MemoryService:
    """Application adapter around Mem0's memory lifecycle."""

    def __init__(self, memory: Any | None = None):
        self.memory = memory

    async def process(
        self,
        user_id: int,
        chat_id: int,
        user_prompt: str,
    ) -> list[MemoryRecord]:
        if self.memory is None:
            return []
        result = await asyncio.to_thread(
            self.memory.add,
            [{"role": "user", "content": user_prompt}],
            user_id=str(user_id),
            metadata={"chat_id": chat_id},
        )
        return self._records(result, user_id)

    async def search(
        self, user_id: int, query: str, limit: int
    ) -> list[MemoryRecord]:
        if self.memory is None:
            return []
        result = await asyncio.to_thread(
            self.memory.search, query, user_id=str(user_id), limit=limit
        )
        return self._records(result, user_id, include_score=True)

    async def delete(self, user_id: int, memory_id: str) -> None:
        if self.memory is not None:
            await asyncio.to_thread(self.memory.delete, memory_id)

    @staticmethod
    def _records(
        result: Any, user_id: int, include_score: bool = False
    ) -> list[MemoryRecord]:
        if isinstance(result, dict):
            values = result.get("results") or result.get("memories") or []
        else:
            values = result or []
        records = []
        for item in values:
            if isinstance(item, str):
                memory_id = item
                text = item
                score = None
            else:
                memory_id = str(item.get("id") or item.get("memory_id") or "")
                text = str(item.get("memory") or item.get("text") or "")
                score = item.get("score") if include_score else None
            if not memory_id or not text:
                continue
            records.append(
                MemoryRecord(
                    memory_id=memory_id,
                    user_id=user_id,
                    text=text,
                    memory_type="general",
                    score=score,
                    created_at=datetime.now(timezone.utc),
                )
            )
        return records
