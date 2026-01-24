

import streamlit as st
import requests

BACKEND = "https://study-planner-kvev.onrender.com"


st.set_page_config(
    page_title="CAESAR Lite",
    layout="wide"
)

st.title("📚 Agentic AI Study Planner")


st.header("1️⃣ Upload Syllabus PDF")

file = st.file_uploader(
    "Upload syllabus PDF",
    type=["pdf"]
)

syllabus_text = ""

if file:
    response = requests.post(
        f"{BACKEND}/upload",
        files={"file": file}
    )
    syllabus_text = response.json()["syllabus"]
    st.success("Syllabus processed successfully")


st.header("2️⃣ Enter Timetable")

timetable = st.text_area(
    "Paste your weekly class & lab timetable"
)


st.header("3️⃣ Generate Weekly Study Plan")

if st.button("Generate Plan"):
    response = requests.post(
        f"{BACKEND}/generate-plan",
        data={
            "syllabus_text": syllabus_text,
            "timetable": timetable
        }
    )
data = response.json()

st.write("Backend response:", data)  # debug (safe)

if "study_plan" in data:
    plan = data["study_plan"]
elif "plan" in data:
    plan = data["plan"]
elif "result" in data:
    plan = data["result"]
elif "answer" in data:
    plan = data["answer"]
elif "output" in data:
    plan = data["output"]
else:
    st.error("Backend did not return a study plan.")
    st.stop()

st.subheader("Your Weekly Study Plan")
st.write(plan)
  

    
    


if st.button("Approve Plan"):
    requests.post(f"{BACKEND}/approve")
    st.success("Plan approved and stored in memory")


st.header("❓ Ask Doubts from Syllabus")

question = st.text_input("Enter your doubt")

if st.button("Ask Tutor"):
    response = requests.post(
        f"{BACKEND}/ask-doubt",
        data={"question": question}
    )
    st.subheader("📘 Tutor Answer")
    st.write(response.json()["answer"])





