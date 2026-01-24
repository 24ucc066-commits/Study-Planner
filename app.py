

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


if st.button("Generate Plan"):
    if not syllabus_text.strip():
        st.error("Please upload syllabus first")
        st.stop()

    if not timetable_text.strip():
        st.error("Please enter timetable")
        st.stop()

    payload = {
        "syllabus": syllabus_text,
        "timetable": timetable_text
    }

    response = requests.post(
        f"{BACKEND}/generate-plan",
        json=payload
    )

    data = response.json()
    st.write("Backend response:", data)

    plan = data.get("study_plan") or data.get("plan") or data.get("result")

    if not plan:
        st.error("Backend did not return a study plan")
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






