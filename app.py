import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURATION & STYLE ---
st.set_page_config(page_title="AI Attendance", page_icon="📸", layout="centered")

# Custom CSS for Minimalist UI
st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            height: 3em;
            font-weight: bold;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1 {
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 700;
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE SETUP ---
if 'page' not in st.session_state:
    st.session_state.page = 'attendance'

def navigate_to(page):
    st.session_state.page = page
    st.rerun()

# --- AUTHENTICATION ---
api_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except:
    pass

# --- LOGIC FUNCTIONS (Keep same as before) ---
def get_available_model(api_key):
    genai.configure(api_key=api_key)
    try:
        preferences = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro-vision"]
        return genai.GenerativeModel(preferences[0])
    except:
        return genai.GenerativeModel("gemini-1.5-flash")

def load_student_db():
    folder_path = "student_db"
    if not os.path.exists(folder_path): os.makedirs(folder_path)
    students = {}
    for file in os.listdir(folder_path):
        if file.lower().endswith((".jpg", ".png", ".jpeg")):
            name = os.path.splitext(file)[0]
            students[name] = os.path.join(folder_path, file)
    return students

def register_student(student_id, image_buffer):
    folder_path = "student_db"
    if not os.path.exists(folder_path): os.makedirs(folder_path)
    file_path = os.path.join(folder_path, f"{student_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(image_buffer.getbuffer())
    return file_path

def verify_identity(reference_path, webcam_image, api_key):
    model = get_available_model(api_key)
    try:
        ref_img = Image.open(reference_path)
    except:
        return "Error loading reference image."

    prompt = """
    Biometric Analysis:
    Image 1: Reference ID.
    Image 2: Webcam User.
    Output: 'MATCH' or 'NO_MATCH' only.
    """
    
    for attempt in range(3):
        try:
            response = model.generate_content([prompt, ref_img, webcam_image])
            return response.text.strip()
        except Exception as e:
            if "429" in str(e):
                time.sleep(2)
                continue
            return f"Error: {str(e)}"
    return "System Busy"

def mark_attendance(name):
    file_path = "attendance.csv"
    now = datetime.now()
    if not os.path.isfile(file_path):
        df = pd.DataFrame(columns=["Name", "Date", "Time", "Status"])
        df.to_csv(file_path, index=False)
    
    new_data = pd.DataFrame([[name, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "Present"]], 
                            columns=["Name", "Date", "Time", "Status"])
    new_data.to_csv(file_path, mode='a', header=False, index=False)
    return f"Marked {name} at {now.strftime('%H:%M:%S')}"

# --- TOP BAR UI ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📸 AI Attendance")
with col2:
    if st.session_state.page == 'attendance':
        st.button("➕ Register New", on_click=navigate_to, args=('register',))
    else:
        st.button("⬅ Back to Home", on_click=navigate_to, args=('attendance',))

# --- API KEY CHECK (Discreet) ---
if not api_key:
    with st.expander("⚙️ Settings (API Key Required)", expanded=True):
        api_key = st.text_input("Enter Gemini API Key", type="password")
        if not api_key:
            st.warning("Please enter your API Key to proceed.")
            st.stop()

# --- PAGE: ATTENDANCE (Main) ---
if st.session_state.page == 'attendance':
    student_db = load_student_db()
    student_ids = list(student_db.keys())

    if not student_ids:
        st.info("👋 Welcome! It looks like empty here. Click 'Register New' to get started.")
    else:
        # Minimal Container for Action
        with st.container(border=True):
            selected_id = st.selectbox("Select Student ID", student_ids)
            webcam_pic = st.camera_input("Verify Identity", label_visibility="hidden")
            
            if webcam_pic:
                if st.button("Verify Identity", type="primary"):
                    with st.spinner("Analyzing..."):
                        ref_path = student_db[selected_id]
                        user_img = Image.open(webcam_pic)
                        result = verify_identity(ref_path, user_img, api_key)
                        
                        if "MATCH" in result:
                            st.success(f"✅ Verified: {selected_id}")
                            mark_attendance(selected_id)
                            st.balloons()
                        elif "NO_MATCH" in result:
                            st.error("❌ Mismatch: Face does not match ID.")
                        else:
                            st.warning(result)

    # Attendance Log (Clean Table)
    st.markdown("### 📅 Today's Activity")
    if os.path.exists("attendance.csv"):
        df = pd.read_csv("attendance.csv")
        # Show only today's records for cleaner look
        today_str = datetime.now().strftime("%Y-%m-%d")
        df_today = df[df['Date'] == today_str]
        
        if not df_today.empty:
            st.dataframe(df_today.sort_values("Time", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.caption("No attendance marked today.")
    else:
        st.caption("No records yet.")

# --- PAGE: REGISTER ---
elif st.session_state.page == 'register':
    with st.container(border=True):
        st.subheader("New Student Registration")
        new_id = st.text_input("Enter Student ID (e.g., 5001)")
        reg_pic = st.camera_input("Capture Reference Photo")

        if st.button("Save Profile", type="primary"):
            if not new_id or not reg_pic:
                st.error("Please fill in the ID and take a photo.")
            else:
                path = register_student(new_id, reg_pic)
                st.success(f"✅ Registered {new_id}!")
                time.sleep(1.5) # Let user see success message
                navigate_to('attendance')
