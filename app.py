import streamlit as st
import requests

BACKEND = "https://study-planner-kvev.onrender.com"  

st.set_page_config(page_title="AI Study Planner", layout="centered")

st.title("📘 AI Study Planner")


st.header("1️⃣ Upload Syllabus PDF")

uploaded_file = st.file_uploader("Upload syllabus PDF", type=["pdf"])
syllabus_text = ""

if uploaded_file:
    res = requests.post(
        f"{BACKEND}/upload",
        files={"file": uploaded_file}
    ).json()

    if "syllabus_text" in res:
        syllabus_text = res["syllabus_text"]
        st.success("Syllabus uploaded")
    else:
        st.error("Backend failed to extract syllabus")


st.header("2️⃣ Enter Timetable")

timetable_text = st.text_area(
    "Paste your weekly timetable",
    height=150
)


st.header("3️⃣ Generate Weekly Study Plan")

if st.button("Generate Plan"):
    if not syllabus_text.strip():
        st.error("Upload syllabus first")
    elif not timetable_text.strip():
        st.error("Enter timetable")
    else:
        res = requests.post(
            f"{BACKEND}/generate-plan",
            json={
                "syllabus": syllabus_text,
                "timetable": timetable_text
            }
        ).json()

        if "study_plan" in res:
            st.subheader("📅 Study Plan")
            st.write(res["study_plan"])
        else:
            st.error("Plan generation failed")


st.header("4️⃣ Ask a Doubt")

question = st.text_input("Enter your doubt")

if st.button("Ask Doubt"):
    if not question.strip():
        st.error("Enter a question")
    else:
        res = requests.post(
            f"{BACKEND}/ask-doubt",
            json={
                "question": question,
                "syllabus": syllabus_text
            }
        ).json()

        if "answer" in res:
            st.subheader("🧠 Answer")
            st.write(res["answer"])
        else:
            st.error("Doubt solver failed")

