from dataclasses import dataclass, field

from ..schemas import DocumentSearchResult, MemoryRecord


@dataclass
class ContextBundle:
    history: list[dict[str, str]] = field(default_factory=list)
    memories: list[MemoryRecord] = field(default_factory=list)
    documents: list[DocumentSearchResult] = field(default_factory=list)
    character_count: int = 0


class ContextBuilder:
    def __init__(self, conversation_service, memory_service, document_search_service):
        self.conversation_service = conversation_service
        self.memory_service = memory_service
        self.document_search_service = document_search_service

    async def build(
        self,
        user_id: int,
        chat_id: int,
        query: str,
        history_limit: int,
        document_ids: list[int],
        new_memories: list[MemoryRecord] | None = None,
        include_memories: bool = True,
    ) -> ContextBundle:
        history = self.conversation_service.get_recent_messages(
            chat_id, history_limit
        )
        history_data = [
            {"prompt": item.prompt, "response": item.response or ""}
            for item in history
        ]
        memories = list(new_memories or [])
        if include_memories:
            existing = await self.memory_service.search(user_id, query, limit=5)
            known_ids = {memory.memory_id for memory in memories}
            memories.extend(
                memory for memory in existing if memory.memory_id not in known_ids
            )
        documents = await self.document_search_service.search(
            user_id, query, document_ids, limit=5
        )
        character_count = sum(
            len(item.get("prompt", "")) + len(item.get("response", ""))
            for item in history_data
        )
        character_count += sum(len(memory.text) for memory in memories)
        character_count += sum(len(document.text) for document in documents)
        return ContextBundle(
            history=history_data,
            memories=memories,
            documents=documents,
            character_count=character_count,
        )
