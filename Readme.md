# LLMS
## Coding - 8000
## General - 8001

# Databases
## PostgreSQL - 5432
## Qdrant - 6333 (HTTP)
## Qdrant - 6334 (gRPC)

### Classifier

The **Classifier** embeds the user's current request with `BAAI/bge-large-en` and passes the 1024-dimensional vector to the Joblib Logistic Regression model in `Backend/models/intent_classifier.pkl`. It returns a fine-grained intent and confidence, such as `coding.debug`, `coding.review`, `research.investigate`, or `writing.rewrite`.

The classifier output is used twice without another model call: `ModelRouter` sends every `coding.*` intent to the coding LLM on port `8000`, while other intents use the general LLM on port `8001`; `PromptGenerator` selects deterministic intent-specific instructions for the final LLM prompt.

### Context Builder

The **Context Builder** determines what information is relevant to the current request and should be provided to the LLM. It retrieves recent conversation history from PostgreSQL, relevant long-term memories and document chunks from the vector database, and information from attachments when required. It filters, prioritizes, and limits the retrieved information according to the model's context window before passing it to the Prompt Generator.

### Prompt Generator

The **Prompt Generator** converts the classifier's predicted intent, selected context, and user's request into the structured prompt expected by the LLM. It uses deterministic templates for coding, analysis, documentation, research, and writing intents. It does not call a model to generate or classify the prompt.

### Memory Service

The **Memory Service** processes only the current user input before the main LLM call. It adapts Mem0, which uses the local memory LLM on port `8003` to identify durable preferences, project facts, decisions, and requirements, then manages storage and retrieval in Qdrant. Ordinary or temporary conversation is discarded.


# NOTE: We are only supporting documents as attachments for now



### Procedure to run

Start PostgreSQL and Qdrant with `Database Infra/docker-compose.yaml`, start the coding, general, and memory vLLM services with `LLM infra/docker-compose.yaml`, activate `Backend/.venv`, and run:

```bash
./start_backend.sh
```

