from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

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