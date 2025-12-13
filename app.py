# --- THE NUCLEAR FIX: FORCE INSTALL LATEST LIBRARY ---
import subprocess
import sys
import os

try:
    import google.generativeai
    if google.generativeai.__version__ < "0.7.2":
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai"])
        os.execv(sys.executable, ['python'] + sys.argv)
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai"])
# -----------------------------------------------------

import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURATION & STYLE ---
st.set_page_config(page_title="AI Attendance", page_icon="📸", layout="centered")

st.markdown("""
    <style>
        .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'page' not in st.session_state: st.session_state.page = 'attendance'
if 'show_logs' not in st.session_state: st.session_state.show_logs = False
if 'log_mode' not in st.session_state: st.session_state.log_mode = None

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

# --- DYNAMIC MODEL FINDER ---
def get_working_model(api_key):
    genai.configure(api_key=api_key)
    try:
        all_models = list(genai.list_models())
        # Priority: Flash -> Vision -> Pro
        for m in all_models:
            if 'flash' in m.name and 'generateContent' in m.supported_generation_methods: return genai.GenerativeModel(m.name)
        for m in all_models:
            if 'vision' in m.name and 'generateContent' in m.supported_generation_methods: return genai.GenerativeModel(m.name)
        return genai.GenerativeModel('gemini-1.5-pro')
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

# --- CORE LOGIC ---
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

def delete_student(student_id):
    folder_path = "student_db"
    file_path = os.path.join(folder_path, f"{student_id}.jpg")
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

def verify_identity(reference_path, webcam_image, api_key):
    model = get_working_model(api_key)
    try:
        ref_img = Image.open(reference_path)
    except:
        return "Error loading reference image."

    # --- SCORE-BASED PROMPT (STRICT) ---
    prompt = """
    You are a strict biometric security system.
    Task: Compare Image 1 (ID Card) vs Image 2 (Live Face).
    
    1. Ignore clothes, background, and lighting. Focus ONLY on facial structure (eyes, nose, jaw).
    2. Rate the probability that these are the SAME PERSON on a scale of 0 to 100.
    
    - 100 = Identical person.
    - 50 = Looks somewhat similar, but could be a sibling/cousin.
    - 0 = Clearly different people.
    
    CRITICAL OUTPUT RULE: Return ONLY the number (integer). Do not write any words.
    """
    
    for attempt in range(3):
        try:
            response = model.generate_content([prompt, ref_img, webcam_image])
            try:
                # Convert response to integer score
                score = int(response.text.strip())
                return score
            except ValueError:
                # If AI returns text instead of a number, fail safe
                return 0 
        except Exception as e:
            if "429" in str(e): time.sleep(2); continue
            return 0 # Fail on error
    return 0

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

# --- UI LAYOUT ---
col1, col2 = st.columns([2, 2])
with col1:
    st.title("📸 AI Attendance")

with col2:
    if st.session_state.page == 'attendance':
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.button("👥 Student List", on_click=navigate_to, args=('student_list',), key='nav_list')
        with btn_col2:
            st.button("➕ Register New", on_click=navigate_to, args=('register',), key='nav_register')
    else:
        st.button("⬅ Back to Home", on_click=navigate_to, args=('attendance',), key='nav_home')

if not api_key:
    with st.expander("⚙️ Settings (API Key Required)", expanded=True):
        api_key = st.text_input("Enter Gemini API Key", type="password")
        if not api_key: st.warning("Please enter your API Key to proceed."); st.stop()

# --- PAGE: ATTENDANCE ---
if st.session_state.page == 'attendance':
    student_db = load_student_db()
    student_ids = list(student_db.keys())

    if not student_ids:
        st.info("👋 Welcome! Click 'Register New' to get started.")
    else:
        with st.container(border=True):
            selected_id = st.selectbox("Select Student ID", student_ids)
            webcam_pic = st.camera_input("Verify Identity", label_visibility="hidden")
            
            if webcam_pic:
                if st.button("Verify Identity", type="primary", key='verify_btn'):
                    with st.spinner("Calculating Match Score..."):
                        ref_path = student_db[selected_id]
                        user_img = Image.open(webcam_pic)
                        
                        # Get the Score (0-100)
                        match_score = verify_identity(ref_path, user_img, api_key)
                        
                        # --- THRESHOLD LOGIC ---
                        # STRICT: Match score must be higher than 75 to pass
                        if match_score >= 75:
                            st.success(f"✅ Verified! Match Score: {match_score}%")
                            mark_attendance(selected_id)
                            st.balloons()
                        elif match_score == 0:
                             st.error("❌ Error: Could not analyze face.")
                        else:
                            st.error(f"❌ Verification Failed. Match Score: {match_score}% (Too Low)")
                            st.warning("⚠️ Face does not match the ID record.")

    # --- HISTORY SECTION ---
    st.divider()
    if st.button("📜 View Attendance Log", key='toggle_logs'):
        st.session_state.show_logs = not st.session_state.show_logs

    if st.session_state.show_logs:
        st.markdown("### 🗂️ Attendance Records")
        col_hist1, col_hist2 = st.columns(2)
        with col_hist1:
            if st.button("👤 By Student ID", key='btn_sort_id'): st.session_state.log_mode = 'id'
        with col_hist2:
            if st.button("📅 By Date", key='btn_sort_date'): st.session_state.log_mode = 'date'
        
        if os.path.exists("attendance.csv"):
            df = pd.read_csv("attendance.csv")
            if st.session_state.log_mode == 'id':
                st.info("Showing history for specific student.")
                search_id = st.selectbox("Select Student ID:", df['Name'].unique())
                subset = df[df['Name'] == search_id]
                st.dataframe(subset, use_container_width=True)
            elif st.session_state.log_mode == 'date':
                st.info("Showing students present on specific date.")
                unique_dates = df['Date'].unique()
                search_date = st.selectbox("Select Date:", unique_dates)
                subset = df[df['Date'] == search_date]
                st.dataframe(subset, use_container_width=True)
        else:
            st.warning("No attendance records found yet.")

    # --- TODAY'S ACTIVITY ---
    st.divider()
    st.markdown("### ⚡ Today's Live Activity")
    if os.path.exists("attendance.csv"):
        df = pd.read_csv("attendance.csv")
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

        if st.button("Save Profile", type="primary", key='btn_save_profile'):
            if not new_id or not reg_pic:
                st.error("Please fill in the ID and take a photo.")
            else:
                path = register_student(new_id, reg_pic)
                st.success(f"✅ Registered {new_id}!")
                time.sleep(1.5)
                navigate_to('attendance')

# --- PAGE: STUDENT LIST ---
elif st.session_state.page == 'student_list':
    st.subheader("👥 Registered Students")
    student_db = load_student_db()
    student_ids = list(student_db.keys())
    
    if not student_ids:
        st.warning("No students registered yet.")
    else:
        df_students = pd.DataFrame(student_ids, columns=["Student ID"])
        st.dataframe(df_students, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🗑️ Delete Student")
        st.warning("Warning: This action cannot be undone.")
        
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            delete_target = st.selectbox("Select Student to Delete", student_ids, key='del_select')
        with col_del2:
            st.write("")
            st.write("")
            if st.button("❌ Delete", type="primary", key='btn_delete_confirm'):
                if delete_student(delete_target):
                    st.success(f"Deleted Student: {delete_target}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Error deleting file.")
