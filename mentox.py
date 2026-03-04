import os
import json
import sqlite3
import random
from typing import List, Dict, TypedDict

import pdfplumber
import streamlit as st

from langgraph.graph import StateGraph, END
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq


# =========================
# 🔐 LOAD API KEY FROM STREAMLIT SECRETS
# =========================
os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]


# =========================
# 💬 MOTIVATION
# =========================
MOTIVATIONS = [
    "Small steps every day lead to big success.",
    "Consistency beats motivation. Just start.",
    "Study now so future you can relax.",
    "You don’t need to be perfect, just persistent.",
    "One focused hour is better than ten distracted ones.",
    "Discipline today = freedom tomorrow.",
    "You are closer than you think. Keep going.",
]


# =========================
# 🗄 DATABASE
# =========================
conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS plans (
    week INTEGER,
    plan TEXT,
    approved INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS progress (
    week INTEGER,
    completed INTEGER
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_sessions (
    chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT
)
""")

conn.commit()


# =========================
# 🤖 LLM + EMBEDDINGS
# =========================
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)

embeddings = FakeEmbeddings(size=768)


# =========================
# 📘 PLANNER STATE
# =========================
class PlannerState(TypedDict):
    syllabus_text: str
    timetable: str
    topics: List[str]
    free_slots: List[str]
    plan: Dict
    progress: int


# =========================
# 📥 INGESTION
# =========================
def ingest_syllabus_text(text: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = splitter.split_text(text)
    vectordb = FAISS.from_texts(chunks, embeddings)
    vectordb.save_local("syllabus_index")

    return chunks[:5]


def extract_pdf_text(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


# =========================
# 🗓 PLANNER WORKFLOW
# =========================
def timetable_agent():
    return ["6–7 AM", "7–8 PM", "9–10 PM"]


def planner_agent(topics, free_slots):
    prompt = f"""
You are an academic study planner.

Topics: {topics}
Available free slots: {free_slots}

Create a clear 7-day weekly study plan.
"""
    response = llm.invoke(prompt)
    return response.content


def generate_study_plan(syllabus_text, timetable):
    topics = ingest_syllabus_text(syllabus_text)
    free_slots = timetable_agent()
    plan_text = planner_agent(topics, free_slots)

    cursor.execute(
        "INSERT INTO plans VALUES (?,?,?)",
        (1, json.dumps({"week_plan": plan_text}), 0)
    )
    conn.commit()

    return plan_text


def approve_plan():
    cursor.execute("UPDATE plans SET approved=1 WHERE week=1")
    conn.commit()
    return "Plan Approved ✅"


# =========================
# 💬 CHAT SYSTEM
# =========================
def new_chat():
    cursor.execute(
        "INSERT INTO chat_sessions (title) VALUES (?)",
        ("New Chat",)
    )
    conn.commit()
    return cursor.lastrowid


def get_chat_history(chat_id):
    cursor.execute(
        "SELECT role, message FROM chat_history WHERE chat_id=? ORDER BY id",
        (chat_id,)
    )
    return cursor.fetchall()


def save_message(chat_id, role, message):
    cursor.execute(
        "INSERT INTO chat_history (chat_id, role, message) VALUES (?,?,?)",
        (chat_id, role, message)
    )
    conn.commit()


def load_qa_chain():
    vectordb = FAISS.load_local(
        "syllabus_index",
        embeddings,
        allow_dangerous_deserialization=True
    )

    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectordb.as_retriever(search_kwargs={"k": 3})
    )


def ask_doubt(question, chat_id):
    qa_chain = load_qa_chain()
    history = get_chat_history(chat_id)

    context = ""
    for role, msg in history:
        context += f"{role}: {msg}\n"

    full_question = f"""
You are a friendly and knowledgeable tutor.

Chat history:
{context}

Question:
{question}
"""

    answer = qa_chain.invoke({"query": full_question})["result"]

    save_message(chat_id, "student", question)
    save_message(chat_id, "tutor", answer)

    return answer


# =========================
# 📝 NOTES
# =========================
def generate_exam_notes(topic=""):
    if not topic.strip():
        topic = "Full Syllabus"
        vectordb = FAISS.load_local(
            "syllabus_index",
            embeddings,
            allow_dangerous_deserialization=True
        )
        docs = vectordb.similarity_search("", k=10)
        context = "\n".join([d.page_content for d in docs])
    else:
        vectordb = FAISS.load_local(
            "syllabus_index",
            embeddings,
            allow_dangerous_deserialization=True
        )
        docs = vectordb.similarity_search(topic, k=5)
        context = "\n".join([d.page_content for d in docs])

    prompt = f"""
Generate EXAM-READY NOTES.

Topic: {topic}

Rules:
- Bullet points
- Definitions
- Important formulas
- Concise

Content:
{context}
"""

    response = llm.invoke(prompt)

    cursor.execute(
        "INSERT INTO exam_notes (topic, notes) VALUES (?,?)",
        (topic, response.content)
    )
    conn.commit()

    return response.content


# =========================
# 🔥 MOTIVATION
# =========================
def get_motivation():
    return random.choice(MOTIVATIONS)
