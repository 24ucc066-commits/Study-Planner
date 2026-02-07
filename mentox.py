
import os
import json
import sqlite3,random
from typing import List, Dict, TypedDict

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

import pdfplumber

from langgraph.graph import StateGraph, END
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from dotenv import load_dotenv


MOTIVATIONS = [
    "Small steps every day lead to big success.",
    "Consistency beats motivation. Just start.",
    "Study now so future you can relax.",
    "You don’t need to be perfect, just persistent.",
    "One focused hour is better than ten distracted ones.",
    "Discipline today = freedom tomorrow.",
    "You are closer than you think. Keep going.",
]




load_dotenv()
app = FastAPI(title="Backend (ChatGroq)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
conn.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    role TEXT,
    message TEXT
)
""")
conn.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS exam_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    notes TEXT
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_sessions (
    chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT
               )
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    role TEXT,
    message TEXT
)
 """)
conn.commit()



llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)

embeddings = FakeEmbeddings(size=768)


class PlannerState(TypedDict):
    syllabus_text: str
    timetable: str
    topics: List[str]
    free_slots: List[str]
    plan: Dict
    progress: int



def ingestion_agent(state: PlannerState):
    """Reads syllabus text, creates vector DB"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    chunks = splitter.split_text(state["syllabus_text"])

    vectordb = FAISS.from_texts(chunks, embeddings)
    vectordb.save_local("syllabus_index")

    return {"topics": chunks[:5]}


def timetable_agent(state: PlannerState):
    """Identifies free study slots (simple demo logic)"""
    return {"free_slots": ["6–7 AM", "7–8 PM", "9–10 PM"]}


def planner_agent(state: PlannerState):
    """Generates weekly study plan"""
    prompt = f"""
    You are an academic study planner.

    Topics: {state['topics']}
    Available free slots: {state['free_slots']}

    Create a clear 7-day weekly study plan.
    """

    response = llm.invoke(prompt)

    return {
        "plan": {
            "week_plan": response.content
        }
    }


def feedback_agent(state: PlannerState):
    """Tracks progress (placeholder)"""
    return {"progress": state.get("progress", 100)}


def memory_agent(state: PlannerState):
    """Stores plan in SQLite"""
    cursor.execute(
        "INSERT INTO plans VALUES (?,?,?)",
        (1, json.dumps(state["plan"]), 0)
    )
    conn.commit()
    return state


def get_chat_history(chat_id: int):
    cursor.execute(
        "SELECT role, message FROM chat_history WHERE chat_id=? ORDER BY id",
        (chat_id,)
    )
    return cursor.fetchall()


def save_message(chat_id: int, role: str, message: str):
    cursor.execute(
        "INSERT INTO chat_history (chat_id, role, message) VALUES (?,?,?)",
        (chat_id, role, message)
    )
    conn.commit()


def get_topic_context(topic: str):
    vectordb = FAISS.load_local(
        "syllabus_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
    docs = vectordb.similarity_search(topic, k=5)
    return "\n".join([d.page_content for d in docs])



workflow = StateGraph(PlannerState)

workflow.add_node("ingest", ingestion_agent)
workflow.add_node("timetable_agent", timetable_agent)
workflow.add_node("planner", planner_agent)
workflow.add_node("feedback", feedback_agent)
workflow.add_node("memory", memory_agent)

workflow.set_entry_point("ingest")
workflow.add_edge("ingest", "timetable_agent")
workflow.add_edge("timetable_agent", "planner")
workflow.add_edge("planner", "feedback")
workflow.add_edge("feedback", "memory")
workflow.add_edge("memory", END)

app_graph = workflow.compile()



@app.post("/upload")
async def upload_syllabus(file: UploadFile = File(...)):
    text = ""
    with pdfplumber.open(file.file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return {"syllabus_text": text}


@app.post("/generate-plan")
async def generate_plan(
    syllabus_text: str = Form(...),
    timetable: str = Form(...)
):
    result = app_graph.invoke({
        "syllabus_text": syllabus_text,
        "timetable": timetable,
        "progress": 100
    })
    return result


@app.post("/approve")
async def approve_plan():
    cursor.execute("UPDATE plans SET approved=1 WHERE week=1")
    conn.commit()
    return {"status": "approved"}



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


@app.post("/ask-doubt")
async def ask_doubt(
    question: str = Form(...),
    chat_id: int = Form(...)
):
    qa_chain = load_qa_chain()

    history = get_chat_history(chat_id)

    context = ""
    for role, msg in history:
        context += f"{role}: {msg}\n"

    full_question = f"""
You are a friendly and knowledgeable tutor.

Answer the question in a clear, student-friendly, and slightly detailed way.

Guidelines:
- Explain in simple language
- Add 1–2 extra lines of context or examples
- Do NOT be overly brief
- Do NOT assume prior knowledge
- Avoid bullet points unless needed

Use syllabus context if available, otherwise general knowledge is allowed.

Chat history (for context only):
{context}

Question:
{question}
"""

    answer = qa_chain.invoke({"query": full_question})["result"]


    save_message(chat_id, "student", question)
    save_message(chat_id, "tutor", answer)

    return {"answer": answer}


@app.get("/motivation")
def get_motivation():
    return {
        "message": random.choice(MOTIVATIONS)
    }



@app.get("/new-chat")
def new_chat():
    cursor.execute(
        "INSERT INTO chat_sessions (title) VALUES (?)",
        ("New Chat",)
    )
    conn.commit()
    return {"chat_id": cursor.lastrowid}


@app.post("/generate-notes")
async def generate_exam_notes(
    topic: str = Form("")
):
    # ✅ FULL SYLLABUS MODE
    if not topic.strip():
        topic = "Full Syllabus"

        vectordb = FAISS.load_local(
            "syllabus_index",
            embeddings,
            allow_dangerous_deserialization=True
        )

        docs = vectordb.similarity_search("", k=10)
        context = "\n".join([d.page_content for d in docs])

    # ✅ TOPIC MODE
    else:
        context = get_topic_context(topic)

    prompt = f"""
    You are an expert exam preparation tutor.

    Generate EXAM-READY NOTES.

    Topic: {topic}

    Rules:
    - Very concise
    - Bullet points
    - Definitions + formulas
    - Important exam points
    - No long paragraphs

    Syllabus content:
    {context}
    """

    response = llm.invoke(prompt)

    cursor.execute(
        "INSERT INTO exam_notes (topic, notes) VALUES (?,?)",
        (topic, response.content)
    )
    conn.commit()

    return {"notes": response.content}
