
import streamlit as st
import sqlite3
import uuid
import random

# ================= CONFIG =================
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

    motivations = [
        "Stay consistent, success will follow.",
        "Small steps daily create big results.",
        "Focus today, succeed tomorrow.",
        "Your future self will thank you.",
        "Discipline beats motivation."
    ]

    if st.button("💡 Get Motivation"):
        st.success(random.choice(motivations))

    st.divider()

    # NEW CHAT
    if st.button("➕ New Chat"):
        cursor.execute(
            "INSERT INTO chat_sessions (title) VALUES (?)",
            ("New Chat",)
        )
        conn.commit()

        st.session_state.chat_id = cursor.lastrowid
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

    cursor.execute(
        "INSERT INTO chat_sessions (title) VALUES (?)",
        ("New Chat",)
    )
    conn.commit()

    st.session_state.chat_id = cursor.lastrowid

# ================= 1️⃣ UPLOAD SYLLABUS =================
st.header("1️⃣ Upload Syllabus PDF")

file = st.file_uploader("Upload syllabus PDF", type=["pdf"])

if file:
    st.success("Syllabus uploaded successfully (processing disabled in this version)")

# ================= 2️⃣ TIMETABLE =================
st.header("2️⃣ Enter Timetable")

timetable = st.text_area("Paste your weekly class & lab timetable")

# ================= 3️⃣ WEEKLY PLAN =================
st.header("3️⃣ Generate Weekly Study Plan")

if st.button("Generate Plan"):

    if timetable.strip() == "":
        st.warning("Please enter timetable first")
    else:

        plan = f"""
Monday - Revise class topics  
Tuesday - Practice problems  
Wednesday - Lab preparation  
Thursday - Concept revision  
Friday - Mock test  
Saturday - Weak topic revision  
Sunday - Full syllabus review
"""

        st.subheader("📅 Weekly Study Plan")
        st.write(plan)

if st.button("Approve Plan"):
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

        # Save student question
        cursor.execute(
            "INSERT INTO chat_history (chat_id, role, message) VALUES (?, ?, ?)",
            (chat_id, "student", question)
        )

        # Dummy AI response
        answer = "This is a placeholder answer. Connect an AI model later."

        cursor.execute(
            "INSERT INTO chat_history (chat_id, role, message) VALUES (?, ?, ?)",
            (chat_id, "assistant", answer)
        )

        conn.commit()

        st.session_state.question = ""
        st.rerun()

# ================= NOTES =================
st.divider()
st.header("📝 Exam Ready Notes")

topic = st.text_input("Enter topic (leave empty for full syllabus)")

if st.button("Generate Notes"):

    notes = f"""
### Notes for: {topic if topic else "Full Syllabus"}

• Revise key concepts  
• Practice previous year questions  
• Make short summary notes  
• Focus on weak areas
"""

    cursor.execute(
        "INSERT INTO exam_notes (topic, notes) VALUES (?, ?)",
        (topic if topic else "General", notes)
    )
    conn.commit()

    st.markdown(notes)

st.subheader("📚 Saved Notes")

cursor.execute("SELECT topic, notes FROM exam_notes ORDER BY id DESC")

for t, n in cursor.fetchall():

    with st.expander(t):
        st.markdown(n)


