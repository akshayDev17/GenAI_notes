from uuid import uuid4

import importlib.metadata

from  qdrant_client import QdrantClient
from qdrant_client.http.models import (VectorParams, Distance, PointVectors, 
                                       PointStruct, Payload, Filter)

from sentence_transformers import SentenceTransformer

def get_client_version():
    """
    sample function to get the client version
    source: qdrant_client.qdrant_remote.QdrantRemote
    """
    client_version = importlib.metadata.version("qdrant-client")
    return client_version

def print_collections(qclient: QdrantClient) -> None:
    """
    print all collections given a qdrant client
    """
    collections = qclient.get_collections().collections
    for collection in collections:
        print(collection.name)

def init_fill_collection(
        collection_name: str,
        sentences: list[str],
        topics: list[str],
        qclient: QdrantClient,
        encoder: SentenceTransformer
) -> None:
    # define some "Points" to store in your vector DB, i.e. the collection

    # PointVector: used usually to update the vector for a given id
    # PointStruct: used to fill up the collection
    points_vector = [
        PointStruct(id = str(uuid4()), vector = encoder.encode(sentences[id]).tolist(), payload={"topic": topics[id]})
        for id in range(len(sentences))
    ]

    qclient.upload_points(collection_name='my_first_collection', points=points_vector, batch_size=2)

def upsert_points_w_diff_payload(collection_name: str, qclient: QdrantClient, 
                                 encoder: SentenceTransformer) -> None:
    """
    Upload to the given collection a new set of points having a different payload
    than the ones already existing in the collection
    """
    new_sentences = [
        "The future of AI is not about machines replacing humans, but about humans and machines collaborating to solve the impossible.",
        "A story is not just a mirror of society; it’s a hammer with which to shape it.",
        "Curiosity is the spark behind every great discovery—never let the world extinguish it.",
        "Healing begins when we stop running from our pain and finally dare to face it with compassion.",
        "Champions aren’t made by their wins, but by how they rise after every fall."
    ]
    new_payload = [
        {"author": "Elon Musk", "topic": "Technology"},
        {"author": "Margaret Atwood", "topic": "Literature"},
        {"author": "Dr. Jane Goodall", "topic": "Science"},
        {"author": "Dr. Gabor Maté", "topic": "Psychology"},
        {"author": "Serena Williams", "topic": "Sports"}
    ]
    new_points = [PointStruct(id = str(uuid4()), 
                              vector=encoder.encode(new_sentences[id]).tolist(),
                              payload=new_payload[id])
                for id in range(len(new_sentences))]
    
    # Note: this method overwrites those points within the collection having the 
    # same indices as the points about to be inserted.
    qclient.upload_points(collection_name=collection_name, points=new_points)

def main() -> None:
    """
    main function to execute all basics
    """
    qclient = QdrantClient(host = 'localhost', port = 6333, check_compatibility=False)

    encoder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    encoder_embed_dim = encoder.get_sentence_embedding_dimension()

    sentences = [
        "The double-slit experiment reveals the bizarre duality of particles behaving as both waves and discrete entities, challenging our classical notions of reality.",
        "The Norse god Odin sacrificed his eye at Mímir's well to gain infinite wisdom, embodying the timeless theme of knowledge requiring profound personal cost.",
        "Fermentation, once a mere preservation method, has evolved into a sophisticated culinary art, transforming humble ingredients like cabbage into globally celebrated dishes such as kimchi."
    ]
    topics = ["Physics", "Mythology", "Biology"]

    if not qclient.collection_exists(collection_name='my_first_collection'):
        # create a collection
        qclient.create_collection(
            collection_name='my_first_collection',
            vectors_config=VectorParams(size = encoder_embed_dim, distance=Distance.COSINE)
        )
    
    qclient.delete('my_first_collection', points_selector=list(range(5)))

    # # print all available connections for this client
    # print_collections(qclient)

    # initialise the empty collection with 
    init_fill_collection('my_first_collection', sentences, topics, qclient, encoder)

    # # retrieve most relevant points for given user query
    # query_resp = qclient.query_points(
    #     collection_name='my_first_collection',
    #     query = encoder.encode("tell me about light's dual nature.").tolist(),
    #     score_threshold=0.5,
    #     limit=2,
    #     with_vectors=True
    # )
    # print([point.payload for point in query_resp.points])
    # print([point.vector for point in query_resp.points])

    # # upsert into a pre-existing collection, a new array of points with a 
    # # different payload than previously existing points in the collection
    # upsert_points_w_diff_payload(collection_name = 'my_first_collection', 
    #                              qclient=qclient, encoder = encoder)
    
    # Note: the upsert works fine.

    # Lets try and filter on queried points using a payload not present for all points
    query_resp = qclient.query_points(
        collection_name='my_first_collection',
        query = encoder.encode("Tell me about science").tolist(),
        limit=4
    )
    print([(point.id, point.score, point.payload) for point in query_resp.points])

if __name__ == '__main__':
    main()
