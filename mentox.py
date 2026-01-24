import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from langchain_groq import ChatGroq

# -----------------------------
# App setup
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# LLM (Groq)
# -----------------------------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

# -----------------------------
# Upload syllabus PDF
# -----------------------------
@app.post("/upload")
async def upload_syllabus(file: UploadFile = File(...)):
    reader = PdfReader(file.file)
    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    return {
        "syllabus_text": text.strip()
    }

# -----------------------------
# Generate study plan
# -----------------------------
@app.post("/generate-plan")
async def generate_plan(payload: dict):
    syllabus = payload.get("syllabus", "")
    timetable = payload.get("timetable", "")

    if not syllabus or not timetable:
        return {"error": "Missing syllabus or timetable"}

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

# -----------------------------
# Health check
# -----------------------------
@app.get("/")
def root():
    return {"status": "Backend running"}
