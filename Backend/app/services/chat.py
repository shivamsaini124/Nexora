from ..schemas import ChatMessageRequest, MessageResponse


class ConversationService:
    def __init__(self, session, repository):
        self.session = session
        self.repository = repository

    def get_recent_messages(self, chat_id: int, limit: int):
        return self.repository.messages(self.session, chat_id, limit)

    def save_exchange(
        self, chat_id: int, prompt: str, response: str, metadata: dict
    ):
        message = self.repository.save_exchange(
            self.session,
            chat_id,
            prompt,
            response,
            metadata["intent"],
            metadata["confidence"],
            metadata["model_name"],
        )
        self.session.commit()
        return message


class ChatOrchestrator:
    def __init__(
        self,
        classifier,
        memory_service,
        context_builder,
        prompt_generator,
        model_router,
        conversation_service,
    ):
        self.classifier = classifier
        self.memory_service = memory_service
        self.context_builder = context_builder
        self.prompt_generator = prompt_generator
        self.model_router = model_router
        self.conversation_service = conversation_service

    async def respond(
        self, user_id: int, chat_id: int, request: ChatMessageRequest
    ) -> MessageResponse:
        classification = self.classifier.classify(request.content)
        memories = await self.memory_service.process(
            user_id=user_id,
            chat_id=chat_id,
            user_prompt=request.content,
        )
        context = await self.context_builder.build(
            user_id=user_id,
            chat_id=chat_id,
            query=request.content,
            history_limit=request.history_limit,
            document_ids=request.document_ids,
            new_memories=memories,
            include_memories=request.include_memories,
        )
        client = self.model_router.route(classification["intent"])
        messages = self.prompt_generator.build_messages(
            intent=classification["intent"],
            query=request.content,
            context=context,
        )
        response = await client.complete(
            messages,
            **self.prompt_generator.generation_parameters(classification["intent"]),
        )
        message = self.conversation_service.save_exchange(
            chat_id,
            request.content,
            response,
            {
                "intent": classification["intent"],
                "confidence": classification["confidence"],
                "model_name": client.model_name,
            },
        )
        return MessageResponse(
            message_id=message.messageId,
            chat_id=message.chatId,
            content=response,
            intent=classification["intent"],
            confidence=classification["confidence"],
            model_name=client.model_name,
            created_at=message.dateTime,
        )
