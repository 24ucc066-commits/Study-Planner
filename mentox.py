

import os
import json
import sqlite3
from typing import List, Dict, TypedDict

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

import pdfplumber

from langgraph.graph import StateGraph, END
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings
from langchain_community.chains import RetrievalQA
from langchain_groq import ChatGroq
from dotenv import load_dotenv


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
async def ask_doubt(question: str = Form(...)):
    qa_chain = load_qa_chain()
    answer = qa_chain.run(question)
    return {"answer": answer}



