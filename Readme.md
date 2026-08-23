# LLMS
## Coding - 8000
## General - 8001

# Databases
## PostgreSQL - 5432
## Qdrant - 6333 (HTTP)
## Qdrant - 6334 (gRPC)

### Classifier

The **Classifier** analyzes the user's current request, along with a small amount of recent conversation when necessary, to determine the type of task being requested, such as coding, reasoning, or general assistance. This classification is used to route the request to the most appropriate specialized LLM, ensuring that each task is handled by a model optimized for that particular type of workload.

### Context Builder

The **Context Builder** determines what information is relevant to the current request and should be provided to the LLM. It retrieves recent conversation history from PostgreSQL, relevant long-term memories and document chunks from the vector database, and information from attachments when required. It filters, prioritizes, and limits the retrieved information according to the model's context window before passing it to the Prompt Generator.

### Prompt Generator

The **Prompt Generator** converts the selected context and the user's request into the structured prompt expected by the LLM. It organizes system instructions, relevant context, previous conversation messages, and the current request into the appropriate chat message format and applies model-specific generation parameters before sending the request to the selected vLLM endpoint.

### Memory Extractor

The **Memory Extractor** analyzes the completed user-assistant conversation to identify information that may be useful in future interactions, such as user preferences, project facts, important decisions, or persistent requirements. Only relevant information is extracted and converted into memory records, which are then embedded and stored in the vector database for future semantic retrieval, while ordinary or temporary conversation is discarded.