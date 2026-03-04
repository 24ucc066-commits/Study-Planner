import streamlit as st
import sqlite3

from backend_logic import (
    new_chat,
    get_motivation,
    extract_pdf_text,
    generate_study_plan,
    approve_plan,
    ask_doubt,
    generate_exam_notes
)

# ================= CONFIG =================
st.set_page_config(page_title="PrepWise", layout="wide")
DB_PATH = "memory.db"

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# ================= SESSION =================
if "chat_id" not in st.session_state:
    st.session_state.chat_id = new_chat()

if "stop" not in st.session_state:
    st.session_state.stop = False

if "question" not in st.session_state:
    st.session_state.question = ""

if "syllabus_text" not in st.session_state:
    st.session_state.syllabus_text = ""

# ================= SIDEBAR =================
with st.sidebar:
    st.markdown("## 🔥 Motivation")

    if st.button("💡 Get Motivation"):
        st.success(get_motivation())

    st.divider()

    if st.button("➕ New Chat"):
        st.session_state.chat_id = new_chat()
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

# ================= 1️⃣ UPLOAD SYLLABUS =================
st.header("1️⃣ Upload Syllabus PDF")

file = st.file_uploader("Upload syllabus PDF", type=["pdf"])

if file:
    st.session_state.syllabus_text = extract_pdf_text(file)
    st.success("Syllabus processed successfully")

# ================= 2️⃣ TIMETABLE =================
st.header("2️⃣ Enter Timetable")
timetable = st.text_area("Paste your weekly class & lab timetable")

# ================= 3️⃣ WEEKLY PLAN =================
st.header("3️⃣ Generate Weekly Study Plan")

if st.button("Generate Plan"):
    if st.session_state.syllabus_text:
        plan = generate_study_plan(
            st.session_state.syllabus_text,
            timetable
        )
        st.subheader("📅 Weekly Study Plan")
        st.write(plan)
    else:
        st.warning("Please upload syllabus first.")

if st.button("Approve Plan"):
    st.success(approve_plan())

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

        # 🔥 Auto-generate chat title (first message only)
        cursor.execute(
            "SELECT title FROM chat_sessions WHERE chat_id=?",
            (chat_id,)
        )
        row = cursor.fetchone()

        if row and row[0] == "New Chat":
            title = question.lower()
            for w in ["i want to", "please", "can you", "tell me",
                      "explain", "what is", "who is"]:
                title = title.replace(w, "")

            title = title.strip().capitalize()[:20]

            cursor.execute(
                "UPDATE chat_sessions SET title=? WHERE chat_id=?",
                (title or "Chat", chat_id)
            )
            conn.commit()

        answer = ask_doubt(question, chat_id)

        st.session_state.question = ""
        st.rerun()

# ================= NOTES =================
st.divider()
st.header("📝 Exam Ready Notes")

topic = st.text_input("Enter topic (leave empty for full syllabus)")

if st.button("Generate Notes"):
    notes = generate_exam_notes(topic)
    st.markdown(notes)

st.subheader("📚 Saved Notes")

cursor.execute("SELECT topic, notes FROM exam_notes ORDER BY id DESC")
for t, n in cursor.fetchall():
    with st.expander(t):
        st.markdown(n)
