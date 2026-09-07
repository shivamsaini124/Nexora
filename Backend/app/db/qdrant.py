from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

collections = {
    "documents": 1024,
    "memories": 1024
}

def connectQdrant(connectionURL: str):
    client = QdrantClient(
        url=connectionURL
    )

    # Used to test if connection is successful or not 
    collectionResponse = client.get_collections()

    initializeCollections(client, collectionResponse)

    return client


def initializeCollections(client: QdrantClient, collectionResponse):

    existingCollections = [
        collection.name
        for collection in collectionResponse.collections
    ]

    for collection_name, vector_size in collections.items():
        if collection_name not in existingCollections:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )


def upsert_points(client: QdrantClient, collection_name: str, points: list[PointStruct]):
    if points:
        client.upsert(collection_name=collection_name, points=points)


def search_documents(
    client: QdrantClient,
    vector: list[float],
    user_id: int,
    document_ids: list[int],
    limit: int,
):
    conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]
    if document_ids:
        conditions.append(
            FieldCondition(key="doc_id", match=MatchAny(any=document_ids))
        )
    return client.query_points(
        collection_name="documents",
        query=vector,
        query_filter=Filter(must=conditions),
        limit=limit,
    ).points


def search_memories(client: QdrantClient, vector: list[float], user_id: int, limit: int):
    return client.query_points(
        collection_name="memories",
        query=vector,
        query_filter=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        ),
        limit=limit,
    ).points


def delete_document_points(client: QdrantClient, doc_id: int):
    client.delete(
        collection_name="documents",
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )


def delete_memory_point(client: QdrantClient, memory_id: str):
    client.delete(collection_name="memories", points_selector=[memory_id])