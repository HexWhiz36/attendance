import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="API Diagnostics", page_icon="🔧")
st.title("🔧 Gemini API Diagnostics")

# 1. Print Library Version
st.write(f"**Library Version:** `google-generativeai {genai.__version__}`")

# 2. Get API Key
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.success("✅ API Key found in secrets.")
else:
    api_key = st.text_input("Enter API Key", type="password")

if st.button("Run Diagnostics") and api_key:
    genai.configure(api_key=api_key)
    
    st.divider()
    st.subheader("1. Testing Access...")
    
    # TEST A: List Available Models
    try:
        st.write("Asking Google: *'What models am I allowed to use?'*")
        models = list(genai.list_models())
        
        found_vision = False
        st.write("### 📋 Models Available to YOU:")
        
        for m in models:
            # We only care about models that can generate content
            if 'generateContent' in m.supported_generation_methods:
                st.code(f"{m.name}")
                if "vision" in m.name or "flash" in m.name:
                    found_vision = True
        
        if not found_vision:
            st.error("❌ CRITICAL: Your API key has access to text models, but NO vision models!")
        else:
            st.success("✅ Your key HAS access to vision models.")

    except Exception as e:
        st.error(f"❌ API CONNECTION FAILED: {str(e)}")
        st.stop()

    st.divider()
    st.subheader("2. Testing a Simple Request...")
    
    # TEST B: Try a simple text prompt (No images)
    try:
        # Use the first available model
        test_model_name = 'gemini-1.5-flash'
        st.write(f"Attempting to say 'Hello' using `{test_model_name}`...")
        model = genai.GenerativeModel(test_model_name)
        response = model.generate_content("Hello, are you working?")
        st.success(f"✅ SUCCESS! The model replied: '{response.text}'")
    except Exception as e:
        st.error(f"❌ Text Generation Failed: {e}")
