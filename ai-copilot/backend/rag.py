import os
import re
from dotenv import load_dotenv
from typing import List, Optional
from huggingface_hub import InferenceClient

# Load from specific path
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

HF_API_KEY = os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY")
os.environ["HF_TOKEN"] = HF_API_KEY or ""  # Ensure SDK picks it up

CHAT_MODELS = [
    "meta-llama/Llama-3.1-8B-Instruct",  # PRIMARY - confirmed working
    "meta-llama/Llama-3.2-3B-Instruct",  # FALLBACK
    "Qwen/Qwen2.5-72B-Instruct",          # BACKUP
]

SYSTEM_PROMPT = """You are a document-grounded AI assistant.

You answer user questions conversationally, like ChatGPT.

You MUST follow these rules:

1. Use ONLY the provided document context.
   - Do NOT use outside knowledge.
   - Do NOT guess or hallucinate missing information.

2. If the answer is not in the documents:
   Say clearly: "This is not available in the provided documents."

3. Do NOT generate:
   - lesson structures
   - steps like STEP 1, STEP 2
   - practice/homework sections
   - repeated templates
   - summaries unless asked

4. Output style:
   - Natural conversational explanation
   - Like ChatGPT answering a question
   - Simple paragraphs or bullets only when needed

5. Be precise and minimal:
   - No repetition
   - No filler content
   - No invented examples unless present in documents

6. If user asks a question:
   - First try to answer directly from context
   - Then optionally clarify if needed

You are a retrieval-based assistant, not a teacher generator."""


class RAGPipeline:
    def __init__(self, faiss_engine):
        self.faiss_engine = faiss_engine
        self.client = InferenceClient(token=HF_API_KEY) if HF_API_KEY else None

    def call_llm(self, user_question: str, context: str) -> Optional[str]:
        if not self.client:
            return None

        user_message = f"""Document context:
---
{context}
---

User question: {user_question}"""

        for model in CHAT_MODELS:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=600,
                    temperature=0.2
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Model {model} failed: {e}")
                continue

        return None

    def answer_query(self, query: str, history: List[dict] = [], **kwargs) -> dict:
        # Retrieve relevant document chunks
        search_results = self.faiss_engine.search(query, k=5)
        context = "\n\n".join([chunk for chunk, score in search_results if score > 0.05])

        if not context.strip():
            return {
                "answer": "This is not available in the provided documents. Please upload a relevant PDF first.",
                "structured": None,
                "sources": []
            }

        answer = self.call_llm(query, context)

        if not answer:
            # Fallback: just return the raw context cleanly
            answer = f"Based on your documents:\n\n{context[:800]}"

        return {
            "answer": answer,
            "structured": None,  # No structured lesson — plain conversational response
            "sources": [chunk[:80] + "..." for chunk, score in search_results if score > 0.05]
        }
