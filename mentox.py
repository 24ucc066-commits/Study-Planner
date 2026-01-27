import streamlit as st
import requests, sqlite3

BACKEND = "http://localhost:8000"

st.set_page_config(
    page_title="CAESAR Lite",
    layout="wide"
)

# ---------------- SESSION ----------------
if "chat_id" not in st.session_state:
    response = requests.get(f"{BACKEND}/new-chat")
    st.session_state.chat_id = response.json()["chat_id"]

st.title("📚 Agentic AI Study Planner")

# ---------------- STUDY PLANNER ----------------
st.header("1️⃣ Upload Syllabus PDF")

file = st.file_uploader("Upload syllabus PDF", type=["pdf"])
syllabus_text = ""

if file:
    response = requests.post(
        f"{BACKEND}/upload",
        files={"file": file}
    )
    syllabus_text = response.json()["syllabus_text"]
    st.success("Syllabus processed successfully")

st.header("2️⃣ Enter Timetable")
timetable = st.text_area("Paste your weekly class & lab timetable")

st.header("3️⃣ Generate Weekly Study Plan")

if st.button("Generate Plan"):
    response = requests.post(
        f"{BACKEND}/generate-plan",
        data={
            "syllabus_text": syllabus_text,
            "timetable": timetable
        }
    )
    st.subheader("📅 Weekly Study Plan")
    st.write(response.json()["plan"])

if st.button("Approve Plan"):
    requests.post(f"{BACKEND}/approve")
    st.success("Plan approved and stored in memory")

# =====================================================
# 🔑 ONLY UI FIX: TABS
# =====================================================
tab1, tab2 = st.tabs(["💬 Ask Doubts", "📝 Exam Ready Notes"])

# ---------------- CHAT TAB ----------------
with tab1:
    st.header("❓ Ask Doubts from Syllabus")
    st.subheader("💬 Chat")

    conn = sqlite3.connect("memory.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role, message FROM chat_history WHERE chat_id=? ORDER BY id",
        (st.session_state.chat_id,)
    )

    messages = cursor.fetchall()

    for role, msg in messages:
        with st.chat_message("user" if role == "student" else "assistant"):
            st.markdown(msg)

    question = st.chat_input("Ask your doubt...")

    if question:
        response = requests.post(
            f"{BACKEND}/ask-doubt",
            data={
                "question": question,
                "chat_id": st.session_state.chat_id
            }
        )
        st.rerun()

# ---------------- NOTES TAB ----------------
with tab2:
    st.header("📝 Exam Ready Notes")

    topic = st.text_input(
        "Enter topic name (or leave empty for syllabus-based notes)"
    )

    if st.button("Generate Notes"):
        response = requests.post(
            f"{BACKEND}/generate-notes",
            data={"topic": topic}
        )
        st.subheader("📘 Notes")
        st.markdown(response.json()["notes"])

    st.subheader("📚 Saved Notes")

    conn = sqlite3.connect("memory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT topic, notes FROM exam_notes ORDER BY id DESC")

    for topic, notes in cursor.fetchall():
        with st.expander(topic):
            st.markdown(notes)

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("### 🔥 Motivation")

if st.sidebar.button("💡 Get Motivation"):
    response = requests.get(f"{BACKEND}/motivation")
    st.sidebar.success(response.json()["message"])

st.sidebar.markdown("### 💬 Doubt Chats")

if st.sidebar.button("➕ New Chat"):
    response = requests.get(f"{BACKEND}/new-chat")
    st.session_state.chat_id = response.json()["chat_id"]
    st.rerun()
