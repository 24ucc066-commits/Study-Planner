import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from langchain_groq import ChatGroq


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2,
    groq_api_key=os.getenv("GROQ_API_KEY"),
)


@app.post("/upload")
async def upload_syllabus(file: UploadFile = File(...)):
    reader = PdfReader(file.file)
    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    return {
        "syllabus_text": text.strip()
    }


@app.post("/generate-plan")
async def generate_plan(payload: dict):
    syllabus = payload.get("syllabus", "")
    timetable = payload.get("timetable", "")

    if not syllabus or not timetable:
        return {"error": "syllabus and timetable required"}

    prompt = f"""
You are an AI study planner.

SYLLABUS:
{syllabus}

TIMETABLE:
{timetable}

Create a clear weekly study plan.
"""

    response = llm.invoke(prompt)

    return {
        "study_plan": response.content
    }


@app.post("/ask-doubt")
async def ask_doubt(payload: dict):
    question = payload.get("question", "")
    syllabus = payload.get("syllabus", "")

    if not question:
        return {"error": "question required"}

    prompt = f"""
You are a helpful teacher.

SYLLABUS CONTEXT:
{syllabus}

STUDENT QUESTION:
{question}

Answer clearly and simply.
"""

    response = llm.invoke(prompt)

    return {
        "answer": response.content
    }


@app.get("/")
def root():
    return {"status": "Backend running"}

