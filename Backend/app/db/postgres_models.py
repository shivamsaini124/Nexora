from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    userId: Mapped[int] = mapped_column(primary_key=True, index=True)
    mailId: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    firstName: Mapped[str] = mapped_column(String(100), nullable=False)
    lastName: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"User(userId={self.userId!r}, firstName={self.firstName!r}, "
            f"lastName={self.lastName!r})"
        )


class Chat(Base):
    __tablename__ = "chats"

    chatId: Mapped[int] = mapped_column(primary_key=True, index=True)
    userId: Mapped[int] = mapped_column(ForeignKey("users.userId"), nullable=False)
    chatName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"Chat(chatId={self.chatId!r}, userId={self.userId!r})"


class Document(Base):
    __tablename__ = "documents"

    docId: Mapped[int] = mapped_column(primary_key=True, index=True)
    chatId: Mapped[int] = mapped_column(ForeignKey("chats.chatId"), nullable=False)

    def __repr__(self) -> str:
        return f"Document(docId={self.docId!r}, chatId={self.chatId!r})"


class Message(Base):
    __tablename__ = "messages"

    messageId: Mapped[int] = mapped_column(primary_key=True, index=True)
    chatId: Mapped[int] = mapped_column(ForeignKey("chats.chatId"), nullable=False)
    dateTime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"Message(messageId={self.messageId!r}, chatId={self.chatId!r})"


class Admin(Base):
    __tablename__ = "admins"

    adminId: Mapped[int] = mapped_column(primary_key=True, index=True)
    mailId: Mapped[str] = mapped_column(String(255), nullable=False)
    firstName: Mapped[str] = mapped_column(String(100), nullable=False)
    lastName: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"Admin(adminId={self.adminId!r}, firstName={self.firstName!r}, "
            f"lastName={self.lastName!r})"
        )

