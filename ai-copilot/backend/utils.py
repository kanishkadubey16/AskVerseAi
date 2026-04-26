import PyPDF2
import re
from typing import List

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error parsing PDF: {e}")
    return text

def clean_text(text: str) -> str:
    # Remove extra whitespaces
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that don't add meaning
    text = re.sub(r'[^\w\s\.,!\?]', '', text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    chunks = []
    words = text.split()
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def extract_keywords(query: str) -> List[str]:
    # Simple keyword extraction (lowercase and filter short words)
    words = re.findall(r'\w+', query.lower())
    return [w for w in words if len(w) > 3]
