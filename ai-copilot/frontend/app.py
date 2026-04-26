import streamlit as st
import requests
import uuid
import json
import os
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000"
HISTORY_FILE = "chat_sessions.json"

st.set_page_config(page_title="AskVerse AI", page_icon="🌌", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp { background-color: #0D1117; color: #E6EDF3; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #21262D; }
    
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
    
    /* Sidebar buttons */
    .stButton button {
        background: transparent; border: 1px solid #30363D;
        color: #E6EDF3; border-radius: 8px; text-align: left;
        font-size: 0.85rem; width: 100%;
    }
    .stButton button:hover { background: #21262D; border-color: #1F6FEB; }
</style>
""", unsafe_allow_html=True)


# --- PERSISTENCE ---
def load_sessions():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_sessions(sessions):
    with open(HISTORY_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


# --- STATE ---
if "chats" not in st.session_state:
    st.session_state.chats = load_sessions()
if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = st.session_state.chats[0]["id"] if st.session_state.chats else None


# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## 🌌 AskVerse AI")
    st.caption("Document-grounded assistant")

    if st.button("＋  New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.chats.insert(0, {
            "id": new_id, "title": "New Chat",
            "messages": [], "timestamp": datetime.now().strftime("%H:%M")
        })
        st.session_state.active_chat_id = new_id
        save_sessions(st.session_state.chats)
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="chat-title">Recent Chats</div>', unsafe_allow_html=True)

    for chat in st.session_state.chats:
        col1, col2 = st.columns([5, 1])
        with col1:
            label = f"💬  {chat['title'][:22]}"
            btn_type = "primary" if chat["id"] == st.session_state.active_chat_id else "secondary"
            if st.button(label, key=f"sel_{chat['id']}", type=btn_type, use_container_width=True):
                st.session_state.active_chat_id = chat["id"]
                st.rerun()
        with col2:
            if st.button("🗑", key=f"del_{chat['id']}", help="Delete this chat"):
                st.session_state.chats = [c for c in st.session_state.chats if c["id"] != chat["id"]]
                # Switch to next available chat
                if st.session_state.active_chat_id == chat["id"]:
                    st.session_state.active_chat_id = st.session_state.chats[0]["id"] if st.session_state.chats else None
                save_sessions(st.session_state.chats)
                st.rerun()

    st.markdown("---")
    st.markdown('<div class="chat-title">📚 Documents</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
    if st.button("Index Document", use_container_width=True) and uploaded:
        with st.spinner("Indexing..."):
            try:
                res = requests.post(f"{API_BASE_URL}/upload", files={"file": uploaded})
                if res.status_code == 200:
                    st.success(f"✅ Indexed {res.json().get('chunks_indexed', '?')} chunks")
                else:
                    st.error("Upload failed")
            except:
                st.error("Backend not reachable")


# --- MAIN CHAT ---
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
    # Render message history
    for msg in active_chat["messages"]:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ai-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
            if msg.get("sources"):
                src_html = " ".join([f'<span class="source-chip">📄 {s}</span>' for s in msg["sources"][:3]])
                st.markdown(src_html, unsafe_allow_html=True)

    # Chat input
    if prompt := st.chat_input("Ask anything about your documents..."):
        active_chat["messages"].append({"role": "user", "content": prompt})
        if active_chat["title"] == "New Chat":
            active_chat["title"] = prompt[:30]

        with st.spinner("Searching documents..."):
            try:
                payload = {
                    "query": prompt,
                    "history": [
                        {"role": m["role"], "content": m["content"]}
                        for m in active_chat["messages"][:-1]
                    ]
                }
                res = requests.post(f"{API_BASE_URL}/query", json=payload, timeout=60)
                if res.status_code == 200:
                    data = res.json()
                    active_chat["messages"].append({
                        "role": "assistant",
                        "content": data.get("answer", "No answer returned."),
                        "sources": data.get("sources", [])
                    })
                    save_sessions(st.session_state.chats)
                else:
                    active_chat["messages"].append({
                        "role": "assistant",
                        "content": "Sorry, I encountered an error. Please try again.",
                        "sources": []
                    })
            except Exception as e:
                active_chat["messages"].append({
                    "role": "assistant",
                    "content": "Connection error. Please check the backend is running.",
                    "sources": []
                })

        save_sessions(st.session_state.chats)
        st.rerun()
