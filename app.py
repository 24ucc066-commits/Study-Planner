import streamlit as st
import requests
import os

# =========================
# CONFIG
# =========================
BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://study-planner-kvev.onrender.com"  # 🔁 CHANGE only if your backend URL is different
)

st.set_page_config(page_title="Study Planner", layout="centered")

st.title("📘 AI Study Planner")

# =========================
# STEP 1: UPLOAD SYLLABUS
# =========================
st.subheader("1️⃣ Upload Syllabus PDF")

uploaded_file = st.file_uploader(
    "Upload syllabus PDF",
    type=["pdf"]
)

syllabus_text = ""

if uploaded_file is not None:
    with st.spinner("Uploading syllabus..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/upload",
                files={"file": uploaded_file}
            )

            if response.status_code != 200:
                st.error("Backend error while uploading syllabus")
                st.stop()

            data = response.json()
            syllabus_text = data.get("syllabus_text", "")

            if not syllabus_text:
                st.error("No syllabus text returned from backend")
                st.stop()

            st.success("Syllabus uploaded successfully!")

        except Exception as e:
            st.error(f"Upload failed: {e}")
            st.stop()

# =========================
# STEP 2: ENTER TIMETABLE
# =========================
st.subheader("2️⃣ Enter Timetable")

timetable_text = st.text_area(
    "Paste your weekly class & lab timetable",
    height=150,
    placeholder="Monday:\n10–11 AM Math\n12–1 PM Physics"
)

# =========================
# STEP 3: GENERATE PLAN
# =========================
st.subheader("3️⃣ Generate Weekly Study Plan")

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

    with st.spinner("Generating study plan..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/generate-plan",
                json=payload
            )

            if response.status_code != 200:
                st.error("Backend error while generating plan")
                st.write(response.text)
                st.stop()

            data = response.json()

            study_plan = (
                data.get("study_plan")
                or data.get("plan")
            )

            if not study_plan:
                st.error("Backend did not return a study plan")
                st.write(data)
                st.stop()

            st.success("✅ Study Plan Generated")
            st.markdown(study_plan)

        except Exception as e:
            st.error(f"Request failed: {e}")
