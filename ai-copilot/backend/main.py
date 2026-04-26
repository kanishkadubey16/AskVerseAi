from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import shutil
import uuid
from utils import extract_text_from_pdf, clean_text, chunk_text
from .faiss_engine import FAISSEngine
from .rag import RAGPipeline

app = FastAPI(title="AskVerse AI - Premium Backend")

# Initialize engines
faiss_engine = FAISSEngine()
rag_pipeline = RAGPipeline(faiss_engine)

UPLOAD_DIR = "uploaded_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class Message(BaseModel):
    role: str
    content: str
    structured: Optional[dict] = None

class QueryRequest(BaseModel):
    query: str
    history: List[Message] = []

@app.get("/")
async def root():
    return {"status": "online", "message": "AskVerse AI Premium Backend is active"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    try:
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        raw_text = extract_text_from_pdf(file_path)
        cleaned = clean_text(raw_text)
        chunks = chunk_text(cleaned)
        faiss_engine.add_documents(chunks)
        
        return {"filename": file.filename, "chunks_indexed": len(chunks), "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query(request: QueryRequest):
    try:
        history = [{"role": m.role, "content": m.content} for m in request.history]
        response = rag_pipeline.answer_query(request.query, history=history)
        return response
    except Exception as e:
        print(f"Query Error: {e}")
        return {
            "answer": "Sorry, something went wrong. Please try again.",
            "structured": None,
            "sources": []
        }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
