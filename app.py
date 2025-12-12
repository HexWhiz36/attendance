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

# --- SMART MODEL SELECTOR ---
def get_available_model(api_key):
    """
    Automatically finds a working model for this specific API Key.
    Prioritizes Flash -> Pro -> Legacy Vision.
    """
    genai.configure(api_key=api_key)
    
    # Preferred order of models (Fastest -> Strongest -> Legacy)
    preferences = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-pro-vision",  # Legacy (Stable)
        "gemini-1.0-pro-vision-latest"
    ]
    
    try:
        # Ask Google what models are actually available to THIS key
        available_models = [m.name.replace("models/", "") for m in genai.list_models()]
        
        # 1. Try to find a match from our preference list
        for model_name in preferences:
            if model_name in available_models:
                return genai.GenerativeModel(model_name)
        
        # 2. If no exact match, look for ANY flash model
        for m in available_models:
            if "flash" in m and "vision" not in m: # Flash usually supports vision by default
                return genai.GenerativeModel(m)
                
        # 3. Fallback: Just return Flash and hope for the best (standard default)
        return genai.GenerativeModel('gemini-1.5-flash')
        
    except Exception as e:
        # If listing fails, just return the safe default
        return genai.GenerativeModel('gemini-1.5-flash')

# --- CORE FUNCTIONS ---

def load_student_db():
    folder_path = "student_db"
    students = {}

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return students

    if not os.path.isdir(folder_path):
        st.error(f"⚠️ Error: 'student_db' is a file. Please delete it.")
        return students

    for file in os.listdir(folder_path):
        if file.lower().endswith((".jpg", ".png", ".jpeg")):
            name = os.path.splitext(file)[0]
            students[name] = os.path.join(folder_path, file)
            
    return students

def verify_identity(reference_path, webcam_image, api_key):
    # Use the Auto-Selector to get a working model
    model = get_available_model(api_key)
    
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
    
    # Retry logic for "Quota Exceeded" (429) errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content([prompt, ref_img, webcam_image])
            return response.text.strip()
        
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                wait_time = 5 * (attempt + 1)
                st.toast(f"⏳ System busy. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            elif "404" in error_msg:
                 # If the auto-selected model fails, try one last legacy fallback
                 try:
                     fallback = genai.GenerativeModel('gemini-pro-vision')
                     return fallback.generate_content([prompt, ref_img, webcam_image]).text.strip()
                 except:
                     return f"Model Error (404): Your API Key does not have access to Vision models."
            else:
                return f"API Error: {error_msg}"
    return "Error: System timed out."

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
