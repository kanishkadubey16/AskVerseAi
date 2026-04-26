import faiss
import numpy as np
import os
import pickle
from sentence_transformers import SentenceTransformer
from typing import List, Tuple

class FAISSEngine:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', index_path: str = "faiss_index.bin", chunks_path: str = "chunks.pkl"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index_path = index_path
        self.chunks_path = chunks_path
        
        # Load existing index if available
        if os.path.exists(self.index_path) and os.path.exists(self.chunks_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.chunks_path, "rb") as f:
                self.chunks = pickle.load(f)
            print(f"Loaded FAISS index with {len(self.chunks)} chunks.")
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunks = []

    def add_documents(self, chunks: List[str]):
        if not chunks:
            return
        embeddings = self.model.encode(chunks)
        faiss.normalize_L2(embeddings)
        self.index.add(np.array(embeddings).astype('float32'))
        self.chunks.extend(chunks)
        self.save()

    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        if self.index.ntotal == 0:
            return []
        
        query_vector = self.model.encode([query])
        faiss.normalize_L2(query_vector)
        
        distances, indices = self.index.search(np.array(query_vector).astype('float32'), k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.chunks):
                results.append((self.chunks[idx], float(distances[0][i])))
        
        return results

    def save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.chunks_path, "wb") as f:
            pickle.dump(self.chunks, f)

    def reset(self):
        self.index = faiss.IndexFlatIP(self.dimension)
        self.chunks = []
        if os.path.exists(self.index_path): os.remove(self.index_path)
        if os.path.exists(self.chunks_path): os.remove(self.chunks_path)
