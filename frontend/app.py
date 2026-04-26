import streamlit as st
import requests
import uuid
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
API_BASE_URL = "http://127.0.0.1:8000"
HISTORY_FILE = "chat_sessions.json"

st.set_page_config(page_title="AskVerse AI | Anti-Gravity", page_icon="🎓", layout="wide")

# --- UI STYLE ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E5E7EB; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    
    .module-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 30px; border-radius: 20px; margin-bottom: 35px; text-align: center;
    }
    .section-box {
        background-color: #161B22; border: 1px solid #30363D; padding: 25px;
        border-radius: 15px; margin-bottom: 20px;
    }
    .label {
        font-weight: 800; font-size: 0.75rem; text-transform: uppercase;
        letter-spacing: 1.5px; color: #60a5fa; margin-bottom: 10px; display: block;
    }
    .formula-display {
        background-color: #0D1117; padding: 40px; border-radius: 12px;
        border: 2px solid #7c3aed; margin: 25px 0; font-size: 1.8rem;
        text-align: center; color: white;
    }
    .hw-box {
        background-color: #2d1b1b; border: 1px dashed #ef4444; padding: 20px;
        border-radius: 12px; margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)

def render_premium_lesson(data):
    if not data: return
    sections = data.get("sections", {})
    
    # Module Title
    st.markdown(f'<div class="module-header"><h1 style="color:white; margin:0;">🎓 {data.get("module")}</h1></div>', unsafe_allow_html=True)
    
    # Concept & Intuition
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-box"><span class="label">🎯 Concept</span>' + sections.get("concept", "") + '</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="section-box"><span class="label">🧠 Intuition</span>' + sections.get("intuition", "") + '</div>', unsafe_allow_html=True)
    
    # Formula
    formula = sections.get("formula", {})
    if isinstance(formula, dict) and formula.get("type") == "math":
        st.markdown('<span class="label" style="text-align:center;">📊 Core Formula</span>', unsafe_allow_html=True)
        st.latex(formula.get("content", formula.get("latex", "")))
    
    # Example
    example = sections.get("example", {})
    if example:
        st.markdown(f'<div class="section-box"><span class="label">🧩 Example ({example.get("domain", "New Scenario")})</span>' + example.get("problem", "") + '</div>', unsafe_allow_html=True)
        with st.expander("🪜 VIEW SOLUTION", expanded=True):
            for i, step in enumerate(example.get("step_by_step_solution", [])):
                st.write(f"**Step {i+1}:** {step}")
            st.success(f"**Final Answer:** {example.get('final_answer')}")
            
    # Practice
    st.markdown('<div class="section-box"><span class="label">🧪 Practice Question</span>' + sections.get("practice_question", "") + '</div>', unsafe_allow_html=True)
    
    # Homework
    st.markdown(f'<div class="hw-box"><span class="label" style="color:#ef4444;">🏁 Homework</span>{sections.get("homework", "")}</div>', unsafe_allow_html=True)

# --- PERSISTENCE ---
def load_sessions():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_sessions(sessions):
    with open(HISTORY_FILE, "w") as f: json.dump(sessions, f, indent=2)

# --- STATE ---
if "chats" not in st.session_state: st.session_state.chats = load_sessions()
if "active_chat_id" not in st.session_state: st.session_state.active_chat_id = st.session_state.chats[0]["id"] if st.session_state.chats else None
if "used_domains" not in st.session_state: st.session_state.used_domains = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("🌌 AskVerse AI")
    if st.button("➕ New Lesson", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.chats.insert(0, {"id": new_id, "title": "New Lesson", "messages": [], "timestamp": datetime.now().strftime("%H:%M")})
        st.session_state.active_chat_id = new_id
        st.session_state.used_domains = [] # Reset domains for new session
        save_sessions(st.session_state.chats)
        st.rerun()
    st.markdown("---")
    for chat in st.session_state.chats:
        if st.button(f"💬 {chat['title'][:20]}", key=f"sel_{chat['id']}", type="primary" if chat["id"] == st.session_state.active_chat_id else "secondary", use_container_width=True):
            st.session_state.active_chat_id = chat["id"]
            st.rerun()
    st.markdown("---")
    with st.expander("📚 Documents"):
        up = st.file_uploader("Upload PDF", type=["pdf"])
        if st.button("Index", use_container_width=True) and up:
            with st.spinner("Indexing..."):
                requests.post(f"{API_BASE_URL}/upload", files={"file": up})
                st.success("Done!")

# --- MAIN ---
active_chat = next((c for c in st.session_state.chats if c["id"] == st.session_state.active_chat_id), None)
if active_chat:
    for msg in active_chat["messages"]:
        if msg.get("structured"): render_premium_lesson(msg["structured"])
        else:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
    
    if prompt := st.chat_input("What would you like to learn today?"):
        active_chat["messages"].append({"role": "user", "content": prompt})
        if active_chat["title"] == "New Lesson": active_chat["title"] = prompt[:30]
        
        with st.spinner("Generating Unrepeated Lesson..."):
            try:
                payload = {
                    "query": prompt, 
                    "history": active_chat["messages"][:-1],
                    "used_domains": st.session_state.used_domains
                }
                res = requests.post(f"{API_BASE_URL}/query", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    active_chat["messages"].append({"role": "assistant", "content": data["answer"], "structured": data.get("structured")})
                    
                    # Track domain to prevent repetition
                    if data.get("domain_used"):
                        st.session_state.used_domains.append(data["domain_used"])
                    
                    save_sessions(st.session_state.chats)
                else: st.error("AI Error")
            except: st.error("Connection Error")
        st.rerun()
else: st.info("Start a new lesson.")
