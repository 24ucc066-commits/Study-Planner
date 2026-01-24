from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

import pdfplumber
import sqlite3

from langgraph.graph import StateGraph, END
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings
from langchain_groq import ChatGroq

# ---------------- APP ----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DB ----------------
conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS plans (week INTEGER, plan TEXT)"
)
conn.commit()

# ---------------- LLM ----------------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)

embeddings = FakeEmbeddings(size=768)

# ---------------- AGENTS ----------------
def ingest_agent(state):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    chunks = splitter.split_text(state["syllabus"])

    db = FAISS.from_texts(chunks, embeddings)
    db.save_local("syllabus_index")

    return {"topics": chunks[:5]}

def planner_agent(state):
    prompt = f"""
Create a weekly study plan using these topics:
{state['topics']}
"""
    response = llm.invoke(prompt)
    return {"plan": response.content}

def memory_agent(state):
    cursor.execute(
        "INSERT INTO plans VALUES (?, ?)",
        (1, state["plan"])
    )
    conn.commit()
    return state

# ---------------- GRAPH ----------------
graph = StateGraph(dict)

graph.add_node("ingest", ingest_agent)
graph.add_node("planner", planner_agent)
graph.add_node("memory", memory_agent)

graph.set_entry_point("ingest")
graph.add_edge("ingest", "planner")
graph.add_edge("planner", "memory")
graph.add_edge("memory", END)

app_graph = graph.compile()

# ---------------- API ----------------
from fastapi import FastAPI, UploadFile, File
from pypdf import PdfReader
import io

app = FastAPI()

@app.post("/upload")
async def upload_syllabus(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        reader = PdfReader(io.BytesIO(pdf_bytes))

        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

        if not text.strip():
            return {
                "syllabus_text": ""
            }

        return {
            "syllabus_text": text
        }

    except Exception as e:
        return {
            "syllabus_text": "",
            "error": str(e)
        }


@app.post("/generate-plan")
async def generate_plan(syllabus: str = Form(...)):
    return app_graph.invoke({"syllabus": syllabus})

@app.post("/ask-doubt")
async def ask_doubt(question: str = Form(...)):
    db = FAISS.load_local(
        "syllabus_index",
        embeddings,
        allow_dangerous_deserialization=True
    )

    docs = db.similarity_search(question, k=3)
    context = "\n".join(d.page_content for d in docs)

    prompt = f"""
Answer ONLY using the context below.

Context:
{context}

Question:
{question}
"""
    response = llm.invoke(prompt)
    return {"answer": response.content}

