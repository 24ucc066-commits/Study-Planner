import streamlit as st
import requests
import sqlite3

# ================= CONFIG =================
BACKEND = "http://localhost:8000"
DB_PATH = "memory.db"

st.set_page_config(page_title="PrepWise", layout="wide")

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_sessions (
    chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    role TEXT,
    message TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS exam_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    notes TEXT
)
""")
conn.commit()

# ================= SESSION =================
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
if "stop" not in st.session_state:
    st.session_state.stop = False
if "question" not in st.session_state:
    st.session_state.question = ""

# ================= SIDEBAR =================
with st.sidebar:
    st.markdown("## 🔥 Motivation")
    if st.button("💡 Get Motivation"):
        r = requests.get(f"{BACKEND}/motivation")
        st.success(r.json()["message"])

    st.divider()

    if st.button("➕ New Chat"):
        r = requests.get(f"{BACKEND}/new-chat")
        st.session_state.chat_id = r.json()["chat_id"]
        st.session_state.stop = False
        st.rerun()

    st.divider()
    st.markdown("## 💬 Your Chats")

    cursor.execute("SELECT chat_id, title FROM chat_sessions ORDER BY chat_id DESC")
    for cid, title in cursor.fetchall():
        display_title = title if title != "New Chat" else "New conversation"
        if st.button(display_title, key=f"chat_{cid}"):
            st.session_state.chat_id = cid
            st.session_state.stop = False
            st.rerun()

# ================= MAIN =================
st.title("📚 PrepWise")

# Ensure chat exists
if st.session_state.chat_id is None:
    r = requests.get(f"{BACKEND}/new-chat")
    st.session_state.chat_id = r.json()["chat_id"]

# ================= 1️⃣ UPLOAD SYLLABUS =================
st.header("1️⃣ Upload Syllabus PDF")

file = st.file_uploader("Upload syllabus PDF", type=["pdf"])
syllabus_text = ""

if file:
    res = requests.post(
        f"{BACKEND}/upload",
        files={"file": file}
    )
    syllabus_text = res.json()["syllabus_text"]
    st.success("Syllabus processed successfully")

# ================= 2️⃣ TIMETABLE =================
st.header("2️⃣ Enter Timetable")
timetable = st.text_area("Paste your weekly class & lab timetable")

# ================= 3️⃣ WEEKLY PLAN =================
st.header("3️⃣ Generate Weekly Study Plan")

if st.button("Generate Plan"):
    res = requests.post(
        f"{BACKEND}/generate-plan",
        data={
            "syllabus_text": syllabus_text,
            "timetable": timetable
        }
    )
    st.subheader("📅 Weekly Study Plan")
    st.write(res.json()["plan"])

if st.button("Approve Plan"):
    requests.post(f"{BACKEND}/approve")
    st.success("Plan approved")

# ================= CHAT =================
st.divider()
st.header("❓ Ask Doubts from Syllabus")

cursor.execute(
    "SELECT role, message FROM chat_history WHERE chat_id=? ORDER BY id",
    (st.session_state.chat_id,)
)
for role, msg in cursor.fetchall():
    with st.chat_message("user" if role == "student" else "assistant"):
        st.markdown(msg)

if st.button("⏹ Stop Reply"):
    st.session_state.stop = True

st.session_state.question = st.text_input(
    "Ask your doubt",
    value=st.session_state.question
)

# ================= SEND =================
if st.button("Send"):
    question = st.session_state.question.strip()
    if question and not st.session_state.stop:
        chat_id = int(st.session_state.chat_id)

        # 🔥 ChatGPT-style title (only first message)
        cursor.execute(
            "SELECT title FROM chat_sessions WHERE chat_id=?",
            (chat_id,)
        )
        row = cursor.fetchone()
        if row and row[0] == "New Chat":
            title = question.lower()
            for w in ["i want to", "please", "can you", "tell me", "explain", "what is", "who is"]:
                title = title.replace(w, "")
            title = title.strip().capitalize()[:20]

            cursor.execute(
                "UPDATE chat_sessions SET title=? WHERE chat_id=?",
                (title or "Chat", chat_id)
            )
            conn.commit()

        requests.post(
            f"{BACKEND}/ask-doubt",
            data={
                "question": question,
                "chat_id": chat_id
            }
        )

        st.session_state.question = ""
        st.rerun()

# ================= NOTES =================
st.divider()
st.header("📝 Exam Ready Notes")

topic = st.text_input("Enter topic (leave empty for full syllabus)")
if st.button("Generate Notes"):
    r = requests.post(
        f"{BACKEND}/generate-notes",
        data={"topic": topic}
    )
    st.markdown(r.json()["notes"])

st.subheader("📚 Saved Notes")
cursor.execute("SELECT topic, notes FROM exam_notes ORDER BY id DESC")
for t, n in cursor.fetchall():
    with st.expander(t):
        st.markdown(n)
