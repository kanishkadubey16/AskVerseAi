import streamlit as st
import uuid
import json
import os
from datetime import datetime

# 🔥 IMPORT YOUR BACKEND LOGIC DIRECTLY
from utils import extract_text_from_pdf, clean_text, chunk_text
from faiss_engine import FAISSEngine
from rag import RAGPipeline

# --- CONFIG ---
HISTORY_FILE = "chat_sessions.json"
UPLOAD_DIR = "uploaded_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="AskVerse AI | Document Assistant", page_icon="🌌", layout="wide")

# --- INIT ENGINE (IMPORTANT) ---
if "faiss_engine" not in st.session_state:
    st.session_state.faiss_engine = FAISSEngine()
    st.session_state.rag_pipeline = RAGPipeline(st.session_state.faiss_engine)

faiss_engine = st.session_state.faiss_engine
rag_pipeline = st.session_state.rag_pipeline

# --- UI STYLE ---
st.markdown("""
<style>
.stApp { background-color: #0E1117; color: #E5E7EB; }
[data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }

/* Chat bubbles */
.user-bubble {
    background: #1F6FEB; color: white; padding: 14px 18px;
    border-radius: 18px 18px 4px 18px; margin: 8px 0 8px auto;
    max-width: 75%; word-wrap: break-word; font-size: 0.95rem; line-height: 1.6;
}
.ai-bubble {
    background: #161B22; border: 1px solid #30363D; color: #E6EDF3;
    padding: 16px 20px; border-radius: 4px 18px 18px 18px;
    margin: 8px auto 8px 0; max-width: 80%; font-size: 0.95rem; line-height: 1.7;
}
.source-chip {
    display: inline-block; background: #21262D; color: #8B949E;
    font-size: 0.7rem; padding: 3px 10px; border-radius: 20px;
    border: 1px solid #30363D; margin: 4px 3px 0 0;
}
.chat-title {
    color: #8B949E; font-size: 0.75rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;
}
div[data-testid="stChatInput"] > div { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# --- STORAGE ---
def load_sessions():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_sessions(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --- STATE ---
if "chats" not in st.session_state:
    st.session_state.chats = load_sessions()

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = st.session_state.chats[0]["id"] if st.session_state.chats else None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🌌 AskVerse AI")

    if st.button("➕ New Chat"):
        new_id = str(uuid.uuid4())
        st.session_state.chats.insert(0, {
            "id": new_id,
            "title": "New Chat",
            "messages": [],
            "timestamp": datetime.now().strftime("%H:%M")
        })
        st.session_state.active_chat_id = new_id
        save_sessions(st.session_state.chats)
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="chat-title">Recent Chats</div>', unsafe_allow_html=True)

    for chat in st.session_state.chats:
        col1, col2 = st.columns([5, 1])
        with col1:
            btn_type = "primary" if chat["id"] == st.session_state.active_chat_id else "secondary"
            if st.button(chat["title"][:20] or "Chat", key=f"sel_{chat['id']}", type=btn_type, use_container_width=True):
                st.session_state.active_chat_id = chat["id"]
                st.rerun()
        with col2:
            if st.button("🗑", key=f"del_{chat['id']}", help="Delete this chat"):
                st.session_state.chats = [c for c in st.session_state.chats if c["id"] != chat["id"]]
                if st.session_state.active_chat_id == chat["id"]:
                    st.session_state.active_chat_id = st.session_state.chats[0]["id"] if st.session_state.chats else None
                save_sessions(st.session_state.chats)
                st.rerun()

    st.markdown("---")
    st.markdown('<div class="chat-title">📚 Documents</div>', unsafe_allow_html=True)

    # 🔥 FILE UPLOAD (NOW LOCAL)
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

    if st.button("Index Document", use_container_width=True) and uploaded_file:
        with st.spinner("Processing..."):
            path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{uploaded_file.name}")

            with open(path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            text = extract_text_from_pdf(path)
            cleaned = clean_text(text)
            chunks = chunk_text(cleaned)

            faiss_engine.add_documents(chunks)

            st.success(f"Indexed {len(chunks)} chunks")

# --- MAIN ---
active_chat = next((c for c in st.session_state.chats if c["id"] == st.session_state.active_chat_id), None)

if not active_chat:
    st.markdown("""
    <div style='text-align:center; padding:80px 20px; color:#8B949E;'>
        <h2 style='color:#E6EDF3;'>Welcome to AskVerse AI 🌌</h2>
        <p>Upload a PDF and ask anything about it.</p>
        <p style='font-size:0.85rem;'>Click <b>New Chat</b> to get started.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in active_chat["messages"]:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ai-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
            if msg.get("sources"):
                src_html = " ".join([f'<span class="source-chip">📄 {s}</span>' for s in msg["sources"][:3]])
                st.markdown(src_html, unsafe_allow_html=True)

    if prompt := st.chat_input("Ask anything about your documents..."):
        active_chat["messages"].append({"role": "user", "content": prompt})
        
        # update title on first message
        if active_chat["title"] == "New Chat":
            active_chat["title"] = prompt[:30]

        with st.spinner("Thinking..."):
            try:
                response = rag_pipeline.answer_query(
                    prompt,
                    history=active_chat["messages"]
                )

                active_chat["messages"].append({
                    "role": "assistant",
                    "content": response["answer"],
                    "sources": response.get("sources", [])
                })

                save_sessions(st.session_state.chats)

            except Exception as e:
                st.error(f"Error: {e}")

        st.rerun()