from sentence_transformers import SentenceTransformer 
from qdrant_client import QdrantClient 
from qdrant_client.models import Distance, VectorParams, PointStruct 
import uuid 
 
COLLECTION = "medical_kb" 
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2") 
qdrant = QdrantClient(path="./qdrant_data") 
 
def setup_collection(): 
    existing = [c.name for c in qdrant.get_collections().collections] 
    if COLLECTION not in existing: 
        qdrant.create_collection( 
            collection_name=COLLECTION, 
            vectors_config=VectorParams(size=384, distance=Distance.COSINE) 
        ) 
 
def index_docs(docs: list): 
    setup_collection() 
    vectors = model.encode(docs).tolist() 
    points = [ 
        PointStruct(id=str(uuid.uuid4()), vector=v, payload={"text": d}) 
        for v, d in zip(vectors, docs) 
    ] 
    qdrant.upsert(collection_name=COLLECTION, points=points) 
 
def retrieve(query: str, top_k: int = 3) -> list: 
    vec = model.encode(query).tolist() 
    results = qdrant.search( 
        collection_name=COLLECTION, 
        query_vector=vec, 
        limit=top_k 
    ) 
    return [r.payload["text"] for r in results] 
 
def build_prompt(query: str, context_docs: list) -> str: 
    context = "\n".join(f"- {d}" for d in context_docs) 
    return ( 
        "You are a medical information assistant. Use ONLY the context below.\n\n" 
        f"Context:\n{context}\n\n" 
        f"Question: {query}\n\n" 
        "Answer (with disclaimer if uncertain):" 
    ) 
