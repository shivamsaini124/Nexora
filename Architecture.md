# Application Architecture

## 1. Purpose and Scope

This repository is the backend foundation for a privacy-first local AI application. The application preprocesses the user's request to identify intent and extract useful long-term memories before generating the response, gathers the relevant short-term conversation, long-term memories, and document context, routes the request to a local LLM endpoint, and persists the conversation.

The repository contains the infrastructure and a working V1 implementation of the persistence, preprocessing, orchestration, document ingestion, memory, and API layers. External databases and local LLM endpoints are still required for full runtime behavior.

### Supported scope

- Text chat requests.
- User, chat, message, and document persistence.
- Document attachments only; other attachment types are out of scope.
- Semantic search over document chunks and long-term memories.
- Intent classification and routing to coding or general LLM endpoints.
- Pre-response memory processing from the user's input.

### Non-goals for the first version

- Multi-tenant authorization and role management beyond the existing user/admin tables.
- Image, audio, or video attachments.
- Distributed workers or a message queue.
- Public cloud model APIs.
- Streaming responses unless explicitly added to the API contract later.

## 2. Current Repository State

| Area | Current state |
| --- | --- |
| FastAPI application | `Backend/app/main.py` creates the application, initializes shared resources, and exposes the API. |
| Routes | `Backend/app/routes.py` exposes health, readiness, user, chat, document upload, and memory routes. |
| PostgreSQL | `Postgres` creates an SQLAlchemy engine/session factory and creates tables from `Base`. |
| Relational models | `User`, `Chat`, `Document`, `ChatDocument`, `Message`, and `Admin` are defined. |
| Qdrant | `connectQdrant()` connects and creates `documents` and `memories` collections with 1024-dimensional cosine vectors. |
| Embeddings | `load_embedding_model()` loads `BAAI/bge-large-en`. |
| Classifier | `Classifier` loads `Backend/models/intent_classifier.pkl` and predicts a fine-grained intent from a normalized BGE embedding. |
| Memory service | `MemoryService` adapts Mem0 and processes only the current user prompt before generation. |
| API schemas | `Backend/app/schemas.py` defines the request and response contracts. |
| Document processing | `DocumentService` supports text, Markdown, CSV, and JSON ingestion, chunking, embedding, and Qdrant indexing. |
| LLM clients | `LLMClient` calls the OpenAI-compatible coding, general, and memory endpoints; prompt construction itself is deterministic. |
| Infrastructure | PostgreSQL, Qdrant, coding LLM, general LLM, and memory LLM compose files exist. |

The architecture below documents the implemented V1 design. Items explicitly marked **planned** are future extensions or boundaries that can be expanded as the application grows.

## 3. High-Level Architecture

```mermaid
flowchart TD
    Client[Client] --> API[FastAPI API]
    API --> ChatOrchestrator[ChatOrchestrator]
    ChatOrchestrator --> Preprocessing[Preprocessing]
    Preprocessing --> Classifier[IntentClassifier\nBGE + Logistic Regression]
    Preprocessing --> MemoryService[MemoryService\nMem0 + memory SLM]
    MemoryService --> MemoryLLM[Memory vLLM :8003]
    MemoryService --> Qdrant[Qdrant :6333]
    ChatOrchestrator --> ContextBuilder[ContextBuilder]
    ContextBuilder --> ConversationRepo[Conversation repositories]
    ContextBuilder --> MemorySearch[MemorySearchService]
    ContextBuilder --> DocumentSearch[DocumentSearchService]
    Preprocessing --> ContextBuilder
    ChatOrchestrator --> PromptGenerator[PromptGenerator]
    PromptGenerator --> ModelRouter[ModelRouter]
    ModelRouter --> CodingLLM[Coding vLLM :8000]
    ModelRouter --> GeneralLLM[General vLLM :8001]
    ChatOrchestrator --> ConversationRepo
    DocumentPipeline[Document ingestion] --> PostgreSQL[PostgreSQL :5432]
    DocumentPipeline --> Embeddings
    DocumentPipeline --> Qdrant
    ConversationRepo --> PostgreSQL
    MemorySearch --> Qdrant
    DocumentSearch --> Qdrant
```

### Request lifecycle

1. The client sends a chat request with a user ID, chat ID or new-chat instruction, the user message, and optional document IDs.
2. FastAPI validates the request with Pydantic schemas.
3. The chat orchestrator loads recent conversation history.
4. The intent classifier embeds the user's prompt with BGE-large-en and predicts an intent and confidence using Logistic Regression.
5. The memory service processes only the user's prompt through Mem0 and the local memory LLM.
6. Preprocessing returns the classification result and new or updated memories.
7. The context builder combines recent conversation, relevant existing memories, newly extracted memories, and document chunks.
8. The prompt generator builds the model-specific chat messages.
9. The model router selects the coding or general vLLM endpoint.
10. The selected model produces the assistant response.
11. The user message and assistant response are persisted in PostgreSQL.
12. The API returns the assistant response and metadata.

### Preprocessing layer

Preprocessing operates on the current user prompt before context construction and before the main LLM call. Intent classification and memory processing are independent components:

```text
Intent classification:
User prompt -> BAAI/bge-large-en -> 1024-dimensional embedding -> Logistic Regression -> intent + confidence

Memory processing:
User prompt -> Mem0 -> Qwen/Qwen2.5-0.5B-Instruct -> memory extraction/update -> Qdrant
```

The combined result is a `PreprocessingResult` containing `intent`, `confidence`, and `new_memories`. The memory LLM does not replace the Logistic Regression classifier, and neither component receives the assistant response.

## 4. Repository Layout

```text
.
├── Architecture.md
├── Readme.md
├── start_backend.sh
├── Backend/
│   ├── requirements.txt
│   ├── models/
│   │   └── intent_classifier.pkl
│   └── app/
│       ├── main.py                 # application factory and lifespan
│       ├── routes.py               # FastAPI routers
│       ├── schemas.py              # Pydantic API contracts
│       ├── config.py               # settings and environment validation
│       ├── db/
│       │   ├── postgres.py         # engine and session factory
│       │   ├── postgres_models.py  # SQLAlchemy models
│       │   └── qdrant.py           # Qdrant connection and collections
│       ├── repositories.py          # database access layer
│       └── services/
│           ├── classifier.py       # intent classifier
│           ├── embedding.py        # embedding model loader
│           ├── memory.py           # Mem0 memory adapter
│           ├── chat.py             # request orchestration
│           ├── context.py          # context retrieval and budgeting
│           ├── documents.py        # upload, parsing, chunking, indexing
│           ├── llm.py              # vLLM/OpenAI-compatible clients
│           └── prompts.py           # deterministic intent prompts
├── Backend Infra/docker-compose.yaml
├── Database Infra/docker-compose.yaml
└── LLM infra/docker-compose.yaml
```

The repository can initially keep repositories and schemas in fewer files, but the ownership boundaries above should remain explicit as the application grows.

## 5. Runtime Components and Configuration

### PostgreSQL

- Image: `postgres:17`.
- Host port: `5432`.
- Database: `project_db`.
- User: `app`.
- Current development password: `app_password`.
- Stores users, chats, documents, chat-document associations, messages, and admins.
- Connection is supplied through `POSTGRES_URL`.

### Qdrant

- Image: `qdrant/qdrant:latest`.
- HTTP port: `6333`.
- gRPC port: `6334`.
- Collections:
  - `documents`: 1024-dimensional cosine vectors.
  - `memories`: 1024-dimensional cosine vectors.
- Connection is supplied through `QDRANT_URL`.

### LLM services

| Service | Host port | Model | Responsibility |
| --- | ---: | --- | --- |
| Coding | 8000 | `Qwen/Qwen2.5-Coder-0.5B-Instruct-GPTQ-Int4` | Coding requests |
| General | 8001 | `JunHowie/Qwen3-0.6B-GPTQ-Int4` | General questions and non-coding requests |
| Memory | 8003 | `Qwen/Qwen2.5-0.5B-Instruct` | Memory extraction and update decisions |

All three services expose an OpenAI-compatible API inside the vLLM container. The backend should use configurable base URLs, for example `http://localhost:8000/v1`, `http://localhost:8001/v1`, and `http://localhost:8003/v1`.

### Environment settings

The application should load and validate these settings at startup:

```text
POSTGRES_URL=postgresql+psycopg2://app:app_password@localhost:5432/project_db
QDRANT_URL=http://localhost:6333
CODING_LLM_URL=http://localhost:8000/v1
GENERAL_LLM_URL=http://localhost:8001/v1
MEMORY_LLM_URL=http://localhost:8003/v1
LLM_API_KEY=local
CLASSIFIER_MODEL_PATH=Backend/models/intent_classifier.pkl
EMBEDDING_MODEL_NAME=BAAI/bge-large-en
EMBEDDING_DIMENSION=1024
```

Secrets and local credentials belong in `.env` and must not be committed.

## 6. FastAPI Application Layer

### `app/main.py`

Responsibilities:

- Load settings.
- Create the FastAPI application.
- Register routers.
- Initialize and store shared resources during lifespan startup.
- Dispose SQLAlchemy and Qdrant resources during shutdown.
- Expose health/readiness checks.

The current lifespan has two concrete defects that must be fixed before startup is reliable:

1. It assigns undefined names `engine` and `sessionLocal` instead of values from the `Postgres` instance.
2. It calls `Classifier()` without the required model argument.

The startup state should contain a typed container similar to:

```python
app.state.postgres = postgres
app.state.qdrant = qdrant
app.state.encoder = encoder
app.state.classifier = classifier
app.state.chat_service = chat_service
```

### `app/routes.py`

Routes should be split into routers when the surface grows. The initial route set is:

| Method | Path | Purpose | Status |
| --- | --- | --- | --- |
| `GET` | `/` | Basic service response | Implemented in `main.py` |
| `GET` | `/health` | Process health check | Implemented |
| `GET` | `/ready` | Verify Qdrant readiness | Implemented |
| `POST` | `/users` | Create a user | Implemented |
| `POST` | `/chats` | Create a chat | Implemented |
| `GET` | `/chats/{chat_id}` | Read chat metadata and recent messages | Planned |
| `POST` | `/chats/{chat_id}/messages` | Run the complete chat pipeline | Implemented |
| `POST` | `/documents` | Upload and index a document | Implemented |
| `GET` | `/documents/{document_id}` | Read document metadata and indexing status | Planned |
| `DELETE` | `/documents/{document_id}` | Remove document metadata and vectors | Planned |
| `GET` | `/memories/search` | Search a user's long-term memories | Implemented |
| `DELETE` | `/memories/{memory_id}` | Remove a memory | Implemented |

### Route responsibilities

Routes should remain thin. A route validates input, obtains dependencies, invokes one application service, and converts the service result to a response schema. Database queries, model calls, chunking, and memory decisions must not be embedded in route functions.

## 7. Pydantic API Schemas

Create `Backend/app/schemas.py` with request and response models. IDs should use `int` while the current SQLAlchemy models use integer primary keys. Timestamps should be timezone-aware datetimes.

### User schemas

```python
class UserCreate(BaseModel):
    mail_id: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)

class UserResponse(UserCreate):
    user_id: int
    model_config = ConfigDict(from_attributes=True)
```

### Chat schemas

```python
class ChatCreate(BaseModel):
    user_id: int
    chat_name: str | None = Field(default=None, max_length=255)

class ChatResponse(BaseModel):
    chat_id: int
    user_id: int
    chat_name: str | None
    model_config = ConfigDict(from_attributes=True)
```

### Message schemas

```python
class ChatMessageRequest(BaseModel):
    user_id: int
    content: str = Field(min_length=1)
    document_ids: list[int] = Field(default_factory=list)
    include_memories: bool = True
    history_limit: int = Field(default=12, ge=0, le=50)

class MessageResponse(BaseModel):
    message_id: int
    chat_id: int
    content: str
    intent: str
    confidence: float = Field(ge=0, le=1)
    created_at: datetime
```

The implemented `Message` table stores the user's prompt, response, intent, classifier confidence, selected model, and timestamp. A production deployment should still manage these schema changes through an explicit migration rather than relying on `create_all()`.

```text
messages.prompt          TEXT NOT NULL
messages.response        TEXT NULL
messages.intent          VARCHAR(100) NULL
messages.classifier_confidence FLOAT NULL
messages.model_name      VARCHAR(255) NULL
messages.date_time       TIMESTAMPTZ NOT NULL
```

### Classification schemas

```python
class ClassificationResponse(BaseModel):
    intent: str
    confidence: float = Field(ge=0, le=1)
```

The classifier artifact currently returns these versioned labels:

```text
analysis.analyze
analysis.compare
analysis.evaluate
analysis.troubleshoot
coding.debug
coding.explain
coding.generate
coding.refactor
coding.review
documentation.create
documentation.explain
documentation.summarize
documentation.update
research.compare
research.investigate
research.retrieve
writing.create
writing.rewrite
writing.summarize
writing.translate
```

`ModelRouter` sends `coding.*` labels to port `8000`; all other labels use port `8001`. `PromptGenerator` selects deterministic instruction templates from the same labels without calling another model.

### Document schemas

```python
class DocumentResponse(BaseModel):
    doc_id: int
    file_name: str
    file_type: str
    file_size: int
    file_hash: str
    uploaded_at: datetime
    status: str

class DocumentSearchResult(BaseModel):
    doc_id: int
    chunk_id: str
    text: str
    score: float
```

### Memory schemas

```python
class MemoryRecord(BaseModel):
    memory_id: str
    user_id: int
    text: str
    memory_type: str
    score: float | None = None
    created_at: datetime | None = None

class MemorySearchRequest(BaseModel):
    user_id: int
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
```

### Error schema

All handled API errors should use one shape:

```python
class ErrorResponse(BaseModel):
    detail: str
    code: str
    request_id: str | None = None
```

## 8. Relational Data Model

The existing SQLAlchemy models are the source of truth for the first relational schema.

```mermaid
erDiagram
    USER ||--o{ CHAT : owns
    CHAT ||--o{ MESSAGE : contains
    CHAT }o--o{ DOCUMENT : attaches
    USER {
        int userId PK
        string mailId UK
        string firstName
        string lastName
    }
    CHAT {
        int chatId PK
        int userId FK
        string chatName
    }
    MESSAGE {
        int messageId PK
        int chatId FK
        datetime dateTime
        text response
    }
    DOCUMENT {
        int docId PK
        string fileName
        string fileType
        int fileSize
        string fileHash UK
        datetime uploadedAt
    }
    CHAT_DOCUMENT {
        int chatId PK,FK
        int docId PK,FK
    }
    ADMIN {
        int adminId PK
        string mailId
        string firstName
        string lastName
    }
```

### SQLAlchemy model classes

#### `Base`

- Inherits `DeclarativeBase`.
- Parent class for all SQLAlchemy models.
- Used by `Base.metadata.create_all()` during current startup.
- Production should use Alembic migrations instead of relying on table creation.

#### `User`

- Table: `users`.
- Fields: `userId`, `mailId`, `firstName`, `lastName`.
- Relationships: one user owns many chats.
- Repository methods: `create_user`, `get_user`, `get_user_by_email`.

#### `Chat`

- Table: `chats`.
- Fields: `chatId`, `userId`, `chatName`.
- Relationships: belongs to one user, contains messages, attaches documents.
- Repository methods: `create_chat`, `get_chat`, `assert_chat_owner`.

#### `Document`

- Table: `documents`.
- Fields: `docId`, `fileName`, `fileType`, `fileSize`, `fileHash`, `uploadedAt`.
- `fileHash` provides upload deduplication.
- Repository methods: `create_document`, `get_document`, `get_by_hash`, `delete_document`.

#### `ChatDocument`

- Join table between chats and documents.
- Composite primary key: `chatId`, `docId`.
- Repository methods: `attach_document`, `detach_document`, `list_chat_documents`.

#### `Message`

- Table: `messages`.
- Current fields: `messageId`, `chatId`, `dateTime`, `response`.
- Required extension: store the user's prompt and response metadata as described in the schema section.
- Repository methods: `create_message`, `list_recent_messages`, `get_message`.

#### `Admin`

- Table: `admins`.
- Intended for operational administration and moderation.
- No admin route or authentication flow currently exists.

### `Postgres`

Current class: `app.db.postgres.Postgres`.

```python
class Postgres:
    def __init__(self, connectionString: str, Base) -> None: ...
    def get_session(self) -> Session: ...       # recommended addition
    def dispose(self) -> None: ...              # recommended addition
```

The session factory should be exposed through a dependency that commits or rolls back each request and always closes the session.

## 9. Vector Data Model

Qdrant stores vectors while PostgreSQL stores authoritative relational metadata.

### `documents` collection

Each point should contain:

```text
id: stable point ID, such as "document:{doc_id}:chunk:{chunk_index}"
vector: 1024-dimensional embedding
payload:
  doc_id: integer
  chunk_id: string
  user_id: integer or null
  chat_id: integer or null
  file_name: string
  text: string
  chunk_index: integer
```

### `memories` collection

Each point should contain:

```text
id: stable memory UUID
vector: 1024-dimensional embedding
payload:
  user_id: integer
  text: string
  memory_type: string
  source_chat_id: integer or null
  source_message_id: integer or null
  created_at: ISO timestamp
  updated_at: ISO timestamp
```

All searches must filter by `user_id` for memories. Document searches must filter to documents the user is allowed to access, preferably by user/chat association rather than by trusting client-supplied IDs.

### `app/db/qdrant.py`

Current functions:

- `connectQdrant(connectionURL)`: creates a `QdrantClient`, tests connectivity, and initializes collections.
- `initializeCollections(client, collectionResponse)`: creates missing collections with cosine distance and vector size 1024.

Recommended additions:

```python
def upsert_document_chunks(client, points) -> None: ...
def search_documents(client, vector, user_id, document_ids, limit): ...
def upsert_memories(client, points) -> None: ...
def search_memories(client, vector, user_id, limit): ...
def delete_document_points(client, doc_id) -> None: ...
def delete_memory_point(client, memory_id) -> None: ...
```

## 10. Service Classes and Methods

The V1 service layer is:

```text
EmbeddingService
IntentClassifier
MemoryService
DocumentService
DocumentSearchService
ConversationService
ContextBuilder
PromptGenerator
LLMClient
ModelRouter
ChatOrchestrator
```

The key boundary is that `MemoryService` adapts Mem0 rather than implementing a second memory-management system.

### `EmbeddingService`

Current module: `app.services.embedding`.

The current module exposes `load_embedding_model()` and returns a `SentenceTransformer` for `BAAI/bge-large-en`. Wrap it in a class when the service is used by multiple workflows:

```python
class EmbeddingService:
    def __init__(self, model_name: str, dimension: int) -> None: ...
    def embed(self, text: str) -> list[float]: ...
    def embed_many(self, texts: list[str]) -> list[list[float]]: ...
```

The service must normalize embeddings consistently with classifier training and Qdrant search.

### `IntentClassifier`

Current module: `app.services.classifier`, class currently named `Classifier`.

```python
class IntentClassifier:
    def __init__(self, model_path: str, embedding_service: EmbeddingService) -> None: ...
    def classify(self, user_prompt: str) -> ClassificationResponse: ...
```

The existing implementation loads `joblib` model data and calls `predict_proba()`. It should receive the model path explicitly rather than constructing a fragile relative path (`../../models/...`). The embedding shape should be one sample with 1024 features, and the classifier should return the best class and probability.

### `MemoryService`

Module: `app.services.memory`. `MemoryService` is an application-level adapter around Mem0; it must not reimplement memory extraction, update, deduplication, or vector persistence.

```python
class MemoryService:
    def __init__(self, mem0_memory) -> None: ...
    async def process(
        self,
        user_id: int,
        chat_id: int,
        user_prompt: str,
    ) -> list[MemoryRecord]: ...
    async def search(self, user_id: int, query: str, limit: int) -> list[MemoryRecord]: ...
    async def delete(self, user_id: int, memory_id: str) -> None: ...
```

`process()` receives only the current user input. It passes that input to Mem0, which uses `Qwen/Qwen2.5-0.5B-Instruct` through the local memory endpoint to identify useful long-term information and manages storage in Qdrant. Examples of memory-worthy input include preferences, project facts, technical choices, and persistent constraints. Greetings, temporary questions, one-off answers, and secrets should normally be discarded.

The memory path is independent of the main generation model:

```text
User prompt -> Mem0 -> local memory LLM -> memory extraction/update -> Qdrant
```

The adapter exposes normalized `MemoryRecord` values to the rest of the application while Mem0 remains responsible for memory management and vector persistence.

### `PreprocessingResult`

The preprocessing stage combines the independent classifier and memory service results:

```python
class PreprocessingResult(BaseModel):
    intent: str
    confidence: float = Field(ge=0, le=1)
    new_memories: list[MemoryRecord] = Field(default_factory=list)
```

The classifier remains a lightweight BGE embedding plus Logistic Regression component. It is not replaced by the memory LLM.

### `DocumentService`

Planned module: `app.services.documents`.

```python
class DocumentService:
    async def ingest(
        self, user_id: int, chat_id: int | None, upload: UploadFile
    ) -> DocumentResponse: ...
    def parse(self, file_name: str, file_type: str, content: bytes) -> str: ...
    def chunk(self, text: str, max_chars: int, overlap: int) -> list[str]: ...
    async def index(self, document: Document, chunks: list[str]) -> None: ...
    async def delete(self, document_id: int) -> None: ...
```

The first supported parsers should cover plain text and common document formats selected by the team. Every upload must validate size and extension, compute a SHA-256 hash, persist metadata, chunk the extracted text, embed chunks, and upsert them to Qdrant.

### `DocumentSearchService`

```python
class DocumentSearchService:
    async def search(
        self,
        user_id: int,
        query: str,
        document_ids: list[int],
        limit: int,
    ) -> list[DocumentSearchResult]: ...
```

It embeds the query, applies ownership/access filters, queries the `documents` collection, and returns only the top relevant chunks.

### `ConversationService`

Planned repository-backed service:

```python
class ConversationService:
    def create_chat(self, user_id: int, name: str | None) -> ChatResponse: ...
    def get_chat(self, chat_id: int, user_id: int) -> ChatResponse: ...
    def get_recent_messages(self, chat_id: int, limit: int) -> list[Message]: ...
    def save_exchange(self, chat_id: int, prompt: str, response: str, metadata) -> Message: ...
```

### `ContextBuilder`

Planned module: `app.services.context`.

```python
class ContextBuilder:
    async def build(
        self,
        user_id: int,
        chat_id: int,
        query: str,
        history_limit: int,
        document_ids: list[int],
    ) -> ContextBundle: ...
```

`ContextBundle` contains recent messages, relevant existing memories, newly extracted memories, relevant document chunks, and token/character estimates. It runs after preprocessing and must enforce a context budget before prompt generation.

### `PromptGenerator`

Module: `app.services.prompts`.

```python
class PromptGenerator:
    def build_messages(
        self, intent: str, query: str, context: ContextBundle
    ) -> list[dict[str, str]]: ...
    def generation_parameters(self, intent: str) -> dict: ...
```

It owns deterministic intent-specific system instructions, ordering of retrieved context, truncation, and model-specific generation parameters. Retrieved document text must be clearly delimited and treated as reference material rather than executable instructions. It does not call an LLM.

### `LLMClient` and `ModelRouter`

Module: `app.services.llm`.

```python
class LLMClient:
    def __init__(self, base_url: str, api_key: str, model_name: str) -> None: ...
    async def complete(self, messages: list[dict[str, str]], **params) -> str: ...

class ModelRouter:
    def route(self, intent: str) -> LLMClient: ...
```

The router maps coding intents to port 8000 and all other supported intents to port 8001. It should apply timeouts, translate upstream failures to application errors, and never expose API keys in logs.

### `ChatOrchestrator`

Module: `app.services.chat`.

```python
class ChatOrchestrator:
    async def respond(
        self,
        user_id: int,
        chat_id: int,
        request: ChatMessageRequest,
    ) -> MessageResponse: ...
```

This is the application use case that coordinates preprocessing, context, prompting, model routing, and persistence. Its dependency order is:

```python
async def respond(...):
    classification = classifier.classify(user_prompt)
    memories = await memory_service.process(
        user_id=user_id,
        chat_id=chat_id,
        user_prompt=user_prompt,
    )
    context = await context_builder.build(
        user_id=user_id,
        chat_id=chat_id,
        query=user_prompt,
        ...,
    )
    messages = prompt_generator.build_messages(
        intent=classification.intent,
        query=user_prompt,
        context=context,
    )
    llm = model_router.route(classification.intent)
    response = await llm.complete(messages)
    await conversation_service.save_exchange(...)
    return response
```

Memory processing must complete before context construction and must not depend on the main LLM response.

## 11. Document Ingestion Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI
    participant D as DocumentService
    participant P as PostgreSQL
    participant E as EmbeddingService
    participant Q as Qdrant

    C->>A: POST /documents (document file)
    A->>D: validate and ingest upload
    D->>D: hash, parse, and chunk
    D->>P: insert document metadata
    D->>E: embed chunks
    E-->>D: 1024-D vectors
    D->>Q: upsert document points
    D-->>A: document status and metadata
    A-->>C: DocumentResponse
```

Deduplication is performed using `Document.fileHash`. Re-uploading the same content should reuse or return the existing document rather than creating duplicate vector points.

## 12. Chat and Memory Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI
    participant O as ChatOrchestrator
    participant X as IntentClassifier
    participant M as MemoryService
    participant B as ContextBuilder
    participant R as ModelRouter
    participant L as vLLM
    participant DB as PostgreSQL/Qdrant

    C->>A: POST /chats/{chat_id}/messages
    A->>O: validated request
    O->>X: classify prompt
    X-->>O: intent and confidence
    O->>M: process current user prompt
    M->>DB: Mem0 memory extraction/update
    DB-->>M: new or updated memories
    M-->>O: memory records
    O->>B: build context
    B->>DB: recent messages and vector search
    DB-->>B: context bundle
    O->>R: route by intent
    R->>L: complete prompt
    L-->>R: assistant response
    O->>DB: persist exchange
    O-->>A: response metadata
    A-->>C: MessageResponse
```

Memory processing happens before context construction and the main LLM call. A failure in memory processing should be observable and should follow an explicit dependency policy: strict mode may fail preprocessing, while degraded mode may continue without newly extracted memories. It must never receive or depend on the assistant response.

## 13. Persistence and Transaction Rules

- Use one SQLAlchemy session per request or service operation.
- Commit only after a successful write operation.
- Roll back on exceptions and always close the session.
- Process the user's prompt through `MemoryService` before context construction and generation.
- Persist the chat exchange after the main LLM response is generated.
- Treat Qdrant writes as a separate operation and make them idempotent using stable point IDs.
- If PostgreSQL succeeds but Qdrant fails during document indexing, expose an `indexing_failed` state and retry rather than silently reporting success.
- Use Alembic migrations for schema changes, especially the required message prompt/metadata fields.
- Add foreign-key indexes for `userId`, `chatId`, and join-table columns.

## 14. Validation, Security, and Reliability

- Validate uploaded file type, extension, size, and extracted text length.
- Enforce user ownership for chats, documents, and memories on every read/search/delete operation.
- Do not accept arbitrary Qdrant collection names or model URLs from requests.
- Keep secrets in environment variables and out of logs.
- Apply request and upstream LLM timeouts.
- Return stable error codes for validation, not-found, dependency-unavailable, and upstream-model failures.
- Add structured request IDs to logs and error responses.
- Never store raw credentials or sensitive tokens as memories.
- Sanitize or delimit document text to reduce prompt-injection risk.
- Add health checks that do not load a second copy of the embedding model.

## 15. Startup and Shutdown

The launcher currently runs `Database Infra/docker-compose.yaml`, waits three seconds, then starts Uvicorn from `Backend`:

```bash
./start_backend.sh
```

The launcher does not currently start `LLM infra/docker-compose.yaml` or `Backend Infra/docker-compose.yaml`. The deployment procedure must therefore document or automate starting the LLM services before making chat requests. The fixed startup sequence should be:

1. Start PostgreSQL and Qdrant.
2. Start coding, general, and memory vLLM services when model-backed features are required.
3. Set environment variables.
4. Start Uvicorn with `app.main:app`.
5. Run readiness checks before accepting traffic.

On shutdown, close the SQLAlchemy engine, Qdrant client, and HTTP clients. Model objects can be released by process shutdown.

## 16. Observability and Testing

### Tests to add

- Unit tests for classifier output shape and label mapping.
- Unit tests for document hashing and deterministic chunking.
- Unit tests for prompt generation and context budgets.
- Unit tests for memory extraction schema validation and filtering.
- Repository tests against PostgreSQL.
- Qdrant integration tests for collection creation, filtered search, upsert, and delete.
- FastAPI tests for health, chat, document, and memory routes.
- End-to-end test with mocked LLM clients covering classification through persistence.

### Metrics and logs

Because the project focuses on efficient private AI, record classification accuracy and latency, memory processing latency and usefulness/precision, retrieval latency, main LLM latency, total request latency, selected model, GPU VRAM usage, GPU utilization, tokens generated, tokens per second, and the number of calls to larger models. For model comparisons, measure quality, latency, VRAM consumption, and throughput. Do not log full prompts or responses by default because they may contain private user data.

## 17. Implementation Order

1. Add typed settings and fix the FastAPI lifespan resource wiring.
2. Add SQLAlchemy session dependencies.
3. Migrate the `Message` model to store user prompts and metadata.
4. Add Pydantic schemas and thin health/user/chat routes.
5. Fix and test the BGE plus Logistic Regression classifier.
6. Implement LLM clients and `ModelRouter`.
7. Implement `MemoryService` around Mem0 and the local memory LLM.
8. Implement `ContextBuilder` with history, existing/new memories, and documents.
9. Implement `PromptGenerator`.
10. Implement `ChatOrchestrator` using the preprocessing-first flow.
11. Implement document upload, parsing, chunking, indexing, and document search.
12. Add ownership checks, migrations, readiness checks, structured errors, and integration tests.
13. Add performance and quality measurements.

## 18. Known Gaps and Decisions to Resolve

- Chat metadata/document read and delete routes remain future additions.
- Mem0 remains optional at import time; full memory processing requires the `mem0ai` package and the memory LLM endpoint.
- The classifier constructor requires a model argument but `main.py` does not provide one.
- `main.py` stores undefined `engine` and `sessionLocal` names during lifespan setup.
- The current `requirements.txt` does not include every package implied by the architecture, such as a direct OpenAI-compatible HTTP client, document parsers, or migration tooling.
- The current startup script starts databases only; LLM services require a separate compose command.
- Authentication and authorization are not implemented. Until they are, user IDs must not be treated as trustworthy identity in a production deployment.
- `Base.metadata.create_all()` is suitable for early development only; schema migrations are required for deployment.

The application is a privacy-first local AI application with an application-level orchestration layer. It uses existing infrastructure such as FastAPI, vLLM, Qdrant, Mem0, PostgreSQL, Sentence Transformers, and Joblib; it does not claim to have invented model fleets, model routing, or inference orchestration.

V1 routing remains intentionally small:

```text
coding -> coding model on :8000
everything else -> general model on :8001
```

More specialized models, dynamic fleets, GPU/VRAM-aware routing, and advanced scheduling are future extensions rather than V1 requirements. A future compute-aware router could select a model using intent, model capability, available VRAM, GPU utilization, latency, context size, and current load.

This document is the target contract for completing the backend while preserving the existing PostgreSQL, Qdrant, Sentence Transformers, Joblib, FastAPI, Mem0, and vLLM choices.
