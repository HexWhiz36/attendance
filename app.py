import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Attendance", page_icon="📸")
st.title("📸 Gemini AI Attendance System")

# --- AUTHENTICATION ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    with st.sidebar:
        st.warning("⚠️ API Key not found in Secrets")
        api_key = st.text_input("Enter Gemini API Key manually", type="password")

# --- FUNCTIONS ---

def load_student_db():
    folder_path = "student_db"
    students = {}

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return students

    if not os.path.isdir(folder_path):
        st.error(f"⚠️ Error: 'student_db' is a file. Delete it.")
        return students

    for file in os.listdir(folder_path):
        if file.lower().endswith((".jpg", ".png", ".jpeg")):
            name = os.path.splitext(file)[0]
            students[name] = os.path.join(folder_path, file)
            
    return students

def verify_identity(reference_path, webcam_image, api_key):
    genai.configure(api_key=api_key)
    
    # 1. USE THE STABLE MODEL ONLY (Avoids the 'limit: 0' error)
    model = genai.GenerativeModel('gemini-1.5-flash')

    try:
        ref_img = Image.open(reference_path)
    except Exception as e:
        return f"Error loading reference image: {e}"

    prompt = """
    You are a Biometric Security Agent.
    I will provide two images.
    Image 1: Reference Photo.
    Image 2: Webcam Photo.
    Task: Determine if these two images show the SAME person.
    Output: Return ONLY the word "MATCH" or "NO_MATCH".
    """
    
    # 2. RETRY LOGIC (Handles the "429 Quota" error)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content([prompt, ref_img, webcam_image])
            return response.text.strip()
        
        except Exception as e:
            error_msg = str(e)
            # If it's a "Too Many Requests" error (429)
            if "429" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1) # Wait 5s, then 10s...
                    st.toast(f"⏳ API Busy. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return "Error: System is too busy (429). Please wait a minute."
            else:
                # If it's any other error, stop immediately
                return f"API Error: {error_msg}"

def mark_attendance(name):
    file_path = "attendance.csv"
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    if not os.path.isfile(file_path):
        df = pd.DataFrame(columns=["Name", "Date", "Time", "Status"])
        df.to_csv(file_path, index=False)
    
    new_data = pd.DataFrame([[name, date_str, time_str, "Present"]], columns=["Name", "Date", "Time", "Status"])
    new_data.to_csv(file_path, mode='a', header=False, index=False)
    return f"Marked {name} at {time_str}"

# --- APP INTERFACE ---

student_db = load_student_db()
student_names = list(student_db.keys())

with st.sidebar:
    if api_key:
        st.success("API Key Loaded")

if not student_names:
    st.warning("⚠️ No database found. Please add student photos to 'student_db'.")
else:
    st.subheader("1. Who are you?")
    selected_user = st.selectbox("Select your name", student_names)

    st.subheader("2. Verify Identity")
    webcam_pic = st.camera_input("Take a selfie")

    if webcam_pic and st.button("Verify & Mark Attendance"):
        if not api_key:
            st.error("❌ Missing API Key.")
        else:
            with st.spinner("🤖 AI is analyzing..."):
                user_img = Image.open(webcam_pic)
                ref_path = student_db[selected_user]
                
                result = verify_identity(ref_path, user_img, api_key)
                
                if "MATCH" in result:
                    st.success(f"✅ Identity Verified! Welcome, {selected_user}.")
                    log_msg = mark_attendance(selected_user)
                    st.toast(log_msg)
                    st.balloons()
                elif "NO_MATCH" in result:
                    st.error("❌ Verification Failed.")
                else:
                    st.warning(f"{result}")

st.divider()
st.subheader("📋 Attendance Log")
if os.path.exists("attendance.csv"):
    df = pd.read_csv("attendance.csv")
    st.dataframe(df.sort_values(by="Time", ascending=False))
