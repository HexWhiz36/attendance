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
    """ Tries multiple models until one works """
    genai.configure(api_key=api_key)
    
    # 1. Load Reference Image
    try:
        ref_img = Image.open(reference_path)
    except Exception as e:
        return f"Error loading reference image: {e}"

    # 2. Define the Prompt
    prompt = """
    You are a Biometric Security Agent.
    I will provide two images.
    Image 1: Reference Photo.
    Image 2: Webcam Photo.
    Task: Determine if these two images show the SAME person.
    Output: Return ONLY the word "MATCH" or "NO_MATCH".
    """

    # 3. THE BRUTE FORCE LIST: Try these models in order
    candidate_models = [
        "gemini-1.5-flash",          # Newest, Fast
        "gemini-1.5-flash-latest",   # Alternative name
        "gemini-1.5-pro",            # High Quality
        "gemini-pro-vision",         # Legacy (Old Reliable)
        "gemini-1.0-pro-vision-latest" # Deep Fallback
    ]

    last_error = ""

    # 4. Loop through models until one works
    for model_name in candidate_models:
        try:
            print(f"Trying model: {model_name}...") # Logs to console
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, ref_img, webcam_image])
            
            # If we get here, it worked!
            return response.text.strip()
        
        except Exception as e:
            # If it fails, save error and try the next one
            last_error = str(e)
            continue

    # 5. If ALL fail, return the error
    return f"ALL MODELS FAILED. Last error: {last_error}"

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

# DEBUGGER IN SIDEBAR (To help you see what's wrong)
with st.sidebar:
    if api_key:
        st.success("API Key Loaded")
        if st.button("Check Available Models"):
            try:
                genai.configure(api_key=api_key)
                models = [m.name for m in genai.list_models()]
                st.write(models)
            except Exception as e:
                st.error(f"Error listing models: {e}")

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
            with st.spinner("🤖 AI is analyzing... (Trying multiple models)"):
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
                    st.warning(f"System Error: {result}")

st.divider()
st.subheader("📋 Attendance Log")
if os.path.exists("attendance.csv"):
    df = pd.read_csv("attendance.csv")
    st.dataframe(df.sort_values(by="Time", ascending=False))import streamlit as st
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
    """ Tries multiple models until one works """
    genai.configure(api_key=api_key)
    
    # 1. Load Reference Image
    try:
        ref_img = Image.open(reference_path)
    except Exception as e:
        return f"Error loading reference image: {e}"

    # 2. Define the Prompt
    prompt = """
    You are a Biometric Security Agent.
    I will provide two images.
    Image 1: Reference Photo.
    Image 2: Webcam Photo.
    Task: Determine if these two images show the SAME person.
    Output: Return ONLY the word "MATCH" or "NO_MATCH".
    """

    # 3. THE BRUTE FORCE LIST: Try these models in order
    candidate_models = [
        "gemini-1.5-flash",          # Newest, Fast
        "gemini-1.5-flash-latest",   # Alternative name
        "gemini-1.5-pro",            # High Quality
        "gemini-pro-vision",         # Legacy (Old Reliable)
        "gemini-1.0-pro-vision-latest" # Deep Fallback
    ]

    last_error = ""

    # 4. Loop through models until one works
    for model_name in candidate_models:
        try:
            print(f"Trying model: {model_name}...") # Logs to console
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, ref_img, webcam_image])
            
            # If we get here, it worked!
            return response.text.strip()
        
        except Exception as e:
            # If it fails, save error and try the next one
            last_error = str(e)
            continue

    # 5. If ALL fail, return the error
    return f"ALL MODELS FAILED. Last error: {last_error}"

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

# DEBUGGER IN SIDEBAR (To help you see what's wrong)
with st.sidebar:
    if api_key:
        st.success("API Key Loaded")
        if st.button("Check Available Models"):
            try:
                genai.configure(api_key=api_key)
                models = [m.name for m in genai.list_models()]
                st.write(models)
            except Exception as e:
                st.error(f"Error listing models: {e}")

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
            with st.spinner("🤖 AI is analyzing... (Trying multiple models)"):
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
                    st.warning(f"System Error: {result}")

st.divider()
st.subheader("📋 Attendance Log")
if os.path.exists("attendance.csv"):
    df = pd.read_csv("attendance.csv")
    st.dataframe(df.sort_values(by="Time", ascending=False))
