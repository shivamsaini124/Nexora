from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from .db.postgres_models import User
from .repositories import ChatRepository, UserRepository
from .schemas import (
	ChatCreate,
	ChatMessageRequest,
	ChatResponse,
	DocumentResponse,
	UserCreate,
	UserResponse,
)

router = APIRouter()
users = UserRepository()
chats = ChatRepository()


def session_for(request: Request):
	return request.app.state.postgres.get_session()


@router.get("/health")
async def health():
	return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request):
	session = session_for(request)
	try:
		request.app.state.qdrant.get_collections()
		return {"status": "ready"}
	except Exception as exc:
		raise HTTPException(status_code=503, detail=str(exc)) from exc
	finally:
		session.close()


@router.post("/users", response_model=UserResponse)
async def create_user(request: Request, payload: UserCreate):
	session = session_for(request)
	try:
		if users.by_email(session, str(payload.mail_id)):
			raise HTTPException(status_code=409, detail="User already exists")
		user = users.create(
			session,
			User(
				mailId=str(payload.mail_id),
				firstName=payload.first_name,
				lastName=payload.last_name,
			),
		)
		session.commit()
		return UserResponse(
			user_id=user.userId,
			mail_id=user.mailId,
			first_name=user.firstName,
			last_name=user.lastName,
		)
	finally:
		session.close()


@router.post("/chats", response_model=ChatResponse)
async def create_chat(request: Request, payload: ChatCreate):
	session = session_for(request)
	try:
		if users.get(session, payload.user_id) is None:
			raise HTTPException(status_code=404, detail="User not found")
		chat = chats.create(session, payload.user_id, payload.chat_name)
		session.commit()
		return ChatResponse(
			chat_id=chat.chatId, user_id=chat.userId, chat_name=chat.chatName
		)
	finally:
		session.close()


@router.post("/chats/{chat_id}/messages")
async def send_message(request: Request, chat_id: int, payload: ChatMessageRequest):
	session = session_for(request)
	try:
		if chats.get_owned(session, chat_id, payload.user_id) is None:
			raise HTTPException(status_code=404, detail="Chat not found")
		service = request.app.state.chat_service(session)
		return await service.respond(payload.user_id, chat_id, payload)
	except HTTPException:
		raise
	except Exception as exc:
		session.rollback()
		raise HTTPException(status_code=500, detail=str(exc)) from exc
	finally:
		session.close()


@router.post("/documents", response_model=DocumentResponse)
async def upload_document(
	request: Request,
	user_id: int,
	chat_id: int | None = None,
	file: UploadFile = File(...),
):
	session = session_for(request)
	try:
		service = request.app.state.document_service(session)
		return await service.ingest(user_id, chat_id, file)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	finally:
		session.close()


@router.get("/memories/search")
async def search_memories(
	request: Request,
	user_id: int,
	query: str,
	limit: int = 5,
):
	return await request.app.state.memory_service.search(
		user_id, query, min(max(limit, 1), 20)
	)


@router.delete("/memories/{memory_id}")
async def delete_memory(request: Request, memory_id: str, user_id: int):
	await request.app.state.memory_service.delete(user_id, memory_id)
	return {"deleted": True, "memory_id": memory_id}
