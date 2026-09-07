from sqlalchemy import select
from sqlalchemy.orm import Session

from .db.postgres_models import Chat, Document, Message, User


class UserRepository:
    def create(self, session: Session, user: User) -> User:
        session.add(user)
        session.flush()
        return user

    def get(self, session: Session, user_id: int) -> User | None:
        return session.get(User, user_id)

    def by_email(self, session: Session, mail_id: str) -> User | None:
        return session.scalar(select(User).where(User.mailId == mail_id))


class ChatRepository:
    def create(self, session: Session, user_id: int, name: str | None) -> Chat:
        chat = Chat(userId=user_id, chatName=name)
        session.add(chat)
        session.flush()
        return chat

    def get_owned(self, session: Session, chat_id: int, user_id: int) -> Chat | None:
        return session.scalar(
            select(Chat).where(Chat.chatId == chat_id, Chat.userId == user_id)
        )

    def messages(self, session: Session, chat_id: int, limit: int) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.chatId == chat_id)
            .order_by(Message.dateTime.desc())
            .limit(limit)
        )
        return list(reversed(session.scalars(statement).all()))

    def save_exchange(
        self,
        session: Session,
        chat_id: int,
        prompt: str,
        response: str,
        intent: str,
        confidence: float,
        model_name: str,
    ) -> Message:
        message = Message(
            chatId=chat_id,
            prompt=prompt,
            response=response,
            intent=intent,
            classifierConfidence=confidence,
            modelName=model_name,
        )
        session.add(message)
        session.flush()
        return message


class DocumentRepository:
    def create(self, session: Session, document: Document) -> Document:
        session.add(document)
        session.flush()
        return document

    def by_hash(self, session: Session, file_hash: str) -> Document | None:
        return session.scalar(
            select(Document).where(Document.fileHash == file_hash)
        )

    def get(self, session: Session, doc_id: int) -> Document | None:
        return session.get(Document, doc_id)

    def delete(self, session: Session, document: Document) -> None:
        session.delete(document)
