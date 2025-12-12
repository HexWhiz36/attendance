import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import pandas as pd
from datetime import datetime

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
    """Loads student names from the image filenames in student_db folder"""
    folder_path = "student_db"
    students = {}

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return students

    if not os.path.isdir(folder_path):
        st.error(f"⚠️ Error: 'student_db' is a file, not a folder. Please delete it.")
        return students

    for file in os.listdir(folder_path):
        if file.lower().endswith((".jpg", ".png", ".jpeg")):
            name = os.path.splitext(file)[0]
            students[name] = os.path.join(folder_path, file)
            
    return students

def verify_identity(reference_path, webcam_image, api_key):
    """Sends both images to Gemini to check if they are the same person"""
    genai.configure(api_key=api_key)
    
    # Try the standard Flash model
    model_name = 'gemini-1.5-flash'
    model = genai.GenerativeModel(model_name)

    try:
        ref_img = Image.open(reference_path)
    except Exception as e:
        return f"Error loading reference image: {e}"

    prompt = """
    You are a Biometric Security Agent.
    I will provide two images.
    Image 1: Reference Photo (The true owner of the ID).
    Image 2: Webcam Photo (The person trying to sign in).

    Task:
    Analyze facial features strictly.
    Determine if these two images show the SAME person.
    
    Output:
    Return ONLY the word "MATCH" or "NO_MATCH".
    """
    
    try:
        # Send images to the model
        response = model.generate_content([prompt, ref_img, webcam_image])
        return response.text.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"

def mark_attendance(name):
    """Saves the record to a CSV file"""
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

# 1. Load Data
student_db = load_student_db()
student_names = list(student_db.keys())

# 2. Sidebar Info
with st.sidebar:
    st.info("Upload photos to 'student_db' folder.")
    if api_key:
        st.success("API Key Loaded Securely")

if not student_names:
    st.warning("⚠️ No database found. Please add student photos (e.g., 'john.jpg') to the `student_db` folder.")
else:
    # 3. Main Interface
    st.subheader("1. Who are you?")
    selected_user = st.selectbox("Select your name", student_names)

    st.subheader("2. Verify Identity")
    webcam_pic = st.camera_input("Take a selfie")

    if webcam_pic and st.button("Verify & Mark Attendance"):
        if not api_key:
            st.error("❌ Missing API Key. Please configure Streamlit Secrets or enter it in the sidebar.")
        else:
            with st.spinner("🤖 AI is analyzing your face..."):
                user_img = Image.open(webcam_pic)
                ref_path = student_db[selected_user]
                
                result = verify_identity(ref_path, user_img, api_key)
                
                if "MATCH" in result:
                    st.success(f"✅ Identity Verified! Welcome, {selected_user}.")
                    log_msg = mark_attendance(selected_user)
                    st.toast(log_msg)
                    st.balloons()
                elif "NO_MATCH" in result:
                    st.error("❌ Verification Failed. Face does not match our records.")
                else:
                    st.warning(f"AI Error: {result}")

# 4. Logs
st.divider()
st.subheader("📋 Attendance Log")
if os.path.exists("attendance.csv"):
    df = pd.read_csv("attendance.csv")
    st.dataframe(df.sort_values(by="Time", ascending=False))
else:
    st.caption("No records yet.")
