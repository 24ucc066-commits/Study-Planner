import streamlit as st
import requests

# -----------------------------
# CONFIG
# -----------------------------
BACKEND_URL = "https://study-planner-kvev.onrender.com"  # 🔴 CHANGE ONLY THIS

st.set_page_config(page_title="AI Study Planner", layout="centered")

st.title("📘 AI Study Planner")

# -----------------------------
# Step 1: Upload syllabus
# -----------------------------
st.header("1️⃣ Upload Syllabus PDF")

uploaded_file = st.file_uploader("Upload syllabus PDF", type=["pdf"])

syllabus_text = ""

if uploaded_file:
    response = requests.post(
        f"{BACKEND_URL}/upload",
        files={"file": uploaded_file}
    )

    data = response.json()

    if "syllabus_text" in data:
        syllabus_text = data["syllabus_text"]
        st.success("Syllabus uploaded successfully")
    else:
        st.error("No syllabus text returned from backend")

# -----------------------------
# Step 2: Enter timetable
# -----------------------------
st.header("2️⃣ Enter Timetable")

timetable_text = st.text_area(
    "Paste your weekly timetable",
    height=150
)

# -----------------------------
# Step 3: Generate plan
# -----------------------------
st.header("3️⃣ Generate Weekly Study Plan")

if st.button("Generate Plan"):
    if not syllabus_text.strip():
        st.error("Upload syllabus first")
    elif not timetable_text.strip():
        st.error("Enter timetable")
    else:
        response = requests.post(
            f"{BACKEND_URL}/generate-plan",
            json={
                "syllabus": syllabus_text,
                "timetable": timetable_text
            }
        )

        data = response.json()

        if "study_plan" in data:
            st.subheader("📅 Your Study Plan")
            st.write(data["study_plan"])
        else:
            st.error("Backend did not return a study plan")


