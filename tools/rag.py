import os
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from functools import lru_cache

# Load mo hinh embedding
@lru_cache(maxsize=1)
def load_model():
    local_model_path = r"D:/Chatbot_Data4Life/v1/models/Vietnamese_Embedding"
    model = SentenceTransformer(local_model_path)
    return model

@lru_cache(maxsize=1)
def connect_chroma_db():
    # 📂 Đường dẫn tới thư mục chứa chroma.sqlite3
    persist_dir = r"D:/Chatbot_Data4Life/v1/chroma_db/chroma_db_faqs"  

    # Kết nối ChromaDB
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_collection("faqs_collection")
    return collection


def get_embedding(text: str) -> list[float]:
    if not text.strip():
        print("Attempted to get embedding for empty text.")
        return []

    model = load_model()
    embedding = model.encode(text)

    return embedding.tolist()

def search_project_documents(query: str):
    query_embed = get_embedding(query)
    answer = []
    collection = connect_chroma_db()
    results = collection.query(
        query_embeddings=[query_embed],  # danh sách các vector query
        n_results=5  # số kết quả muốn lấy
    )
    for doc in results["metadatas"][0]:
        answer.append(doc.get("answer_text"))
    return answer






