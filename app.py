
import streamlit as st
import sqlite3
import random
import os
from langchain_groq import ChatGroq

# ================= CONFIG =================
st.set_page_config(page_title="PrepWise", layout="wide")
DB_PATH = "memory.db"

# ================= AI MODEL =================
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_sessions(
chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
title TEXT)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_history(
id INTEGER PRIMARY KEY AUTOINCREMENT,
chat_id INTEGER,
role TEXT,
message TEXT)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS exam_notes(
id INTEGER PRIMARY KEY AUTOINCREMENT,
topic TEXT,
notes TEXT)
""")

conn.commit()

# ================= SESSION =================
if "chat_id" not in st.session_state:
    st.session_state.chat_id=None

if "question" not in st.session_state:
    st.session_state.question=""

# ================= MOTIVATION =================
MOTIVATIONS=[
"Small steps every day lead to big success.",
"Consistency beats motivation.",
"Study now so future you can relax.",
"You don’t need to be perfect, just persistent.",
"One focused hour is better than ten distracted ones.",
]

# ================= SIDEBAR =================
with st.sidebar:

    st.markdown("## 🔥 Motivation")

    if st.button("💡 Get Motivation"):
        st.success(random.choice(MOTIVATIONS))

    st.divider()

    if st.button("➕ New Chat"):

        cursor.execute(
        "INSERT INTO chat_sessions(title) VALUES(?)",
        ("New Chat",)
        )

        conn.commit()
        st.session_state.chat_id=cursor.lastrowid
        st.rerun()

    st.divider()
    st.markdown("## 💬 Your Chats")

    cursor.execute(
    "SELECT chat_id,title FROM chat_sessions ORDER BY chat_id DESC"
    )

    for cid,title in cursor.fetchall():

        display_title = title if title!="New Chat" else "New conversation"

        if st.button(display_title,key=f"chat_{cid}"):

            st.session_state.chat_id=cid
            st.rerun()

# ================= MAIN =================
st.title("📚 PrepWise")

if st.session_state.chat_id is None:

    cursor.execute(
    "INSERT INTO chat_sessions(title) VALUES(?)",
    ("New Chat",)
    )

    conn.commit()
    st.session_state.chat_id=cursor.lastrowid

# ================= SYLLABUS =================
st.header("1️⃣ Upload Syllabus PDF")

file=st.file_uploader("Upload syllabus PDF",type=["pdf"])

if file:
    st.success("Syllabus uploaded successfully")

# ================= TIMETABLE =================
st.header("2️⃣ Enter Timetable")

timetable=st.text_area("Paste your weekly class & lab timetable")

# ================= STUDY PLAN =================
st.header("3️⃣ Generate Weekly Study Plan")

if st.button("Generate Plan"):

    if timetable.strip()=="":

        st.warning("Please enter timetable")

    else:

        prompt=f"""
You are a study planner.

Create a simple weekly study plan.

Timetable:
{timetable}

Give a 7 day study plan.
"""

        response=llm.invoke(prompt)

        st.subheader("📅 Weekly Study Plan")
        st.write(response.content)

if st.button("Approve Plan"):
    st.success("Plan approved")

# ================= CHAT =================
st.divider()
st.header("❓ Ask Doubts")

cursor.execute(
"SELECT role,message FROM chat_history WHERE chat_id=? ORDER BY id",
(st.session_state.chat_id,)
)

for role,msg in cursor.fetchall():

    with st.chat_message("user" if role=="student" else "assistant"):
        st.markdown(msg)

st.session_state.question=st.text_input(
"Ask your doubt",
value=st.session_state.question
)

# ================= SEND =================
if st.button("Send"):

    question=st.session_state.question.strip()

    if question:

        chat_id=int(st.session_state.chat_id)

        cursor.execute(
        "INSERT INTO chat_history(chat_id,role,message) VALUES(?,?,?)",
        (chat_id,"student",question)
        )

        history=""

        cursor.execute(
        "SELECT role,message FROM chat_history WHERE chat_id=?",
        (chat_id,)
        )

        for r,m in cursor.fetchall():
            history+=f"{r}:{m}\n"

        prompt=f"""
You are a helpful tutor.

Chat history:
{history}

Student question:
{question}

Explain clearly in simple language.
"""

        response=llm.invoke(prompt)
        answer=response.content

        cursor.execute(
        "INSERT INTO chat_history(chat_id,role,message) VALUES(?,?,?)",
        (chat_id,"assistant",answer)
        )

        conn.commit()

        st.session_state.question=""
        st.rerun()

# ================= NOTES =================
st.divider()
st.header("📝 Exam Ready Notes")

topic=st.text_input("Enter topic")

if st.button("Generate Notes"):

    prompt=f"""
Create exam ready notes.

Topic: {topic}

Rules:
• bullet points
• short definitions
• important formulas
• exam focused
"""

    response=llm.invoke(prompt)
    notes=response.content

    cursor.execute(
    "INSERT INTO exam_notes(topic,notes) VALUES(?,?)",
    (topic,notes)
    )

    conn.commit()

    st.markdown(notes)

st.subheader("📚 Saved Notes")

cursor.execute(
"SELECT topic,notes FROM exam_notes ORDER BY id DESC"
)

for t,n in cursor.fetchall():

    with st.expander(t):
        st.markdown(n)


