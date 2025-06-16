import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from dotenv import load_dotenv
import os
from datetime import datetime
import base64
import speech_recognition as sr
import re       #for emojis
import threading
import time
import tempfile
import sqlite3

# oad environment
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

# SQLite setup
conn = sqlite3.connect("consultations.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    data BLOB,
    timestamp TEXT
)
""")
conn.commit()

# page Setup
st.set_page_config(page_title="🩺 Healthcare Chatbot", layout="centered")
st.title("🩺 Patient Consultation Chatbot")
st.write("Describe your symptoms by voice or text. The chatbot will generate a summary report.")

# session state
if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""
if 'pdf_bytes' not in st.session_state:
    st.session_state.pdf_bytes = None
if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = None
if 'generated' not in st.session_state:
    st.session_state.generated = False

# input mode
input_mode = st.radio("Choose Input Method:", ["🎤 Voice", "✍️ Text"], horizontal=True)

def remove_emojis(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

def record_audio(stop_event, filepath):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, timeout=300, phrase_time_limit=300)
        with open(filepath, "wb") as f:
            f.write(audio.get_wav_data())

def transcribe_audio(filepath):
    recognizer = sr.Recognizer()
    with sr.AudioFile(filepath) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio)

# voice input
if input_mode == "🎤 Voice":
    st.subheader("Voice Recording")
    if not st.session_state.recording:
        if st.button("🔴 Start Recording"):
            st.session_state.recording = True
            stop_event = threading.Event()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            st.session_state.audio_file_path = temp_file.name

            thread = threading.Thread(target=record_audio, args=(stop_event, st.session_state.audio_file_path))
            thread.start()

            timer_placeholder = st.empty()
            start_time = time.time()

            while thread.is_alive():
                elapsed = int(time.time() - start_time)
                timer_placeholder.info(f"⏱️ Recording... {elapsed} seconds")
                time.sleep(1)
                if elapsed >= 300:
                    stop_event.set()
                    break

            st.session_state.recording = False
            timer_placeholder.success("✅ Recording complete.")
            try:
                text = transcribe_audio(st.session_state.audio_file_path)
                st.session_state.user_input = text
                st.success("📝 Voice Transcription Successful!")
            except sr.UnknownValueError:
                st.error("❌ Could not understand your speech.")
            except sr.RequestError:
                st.error("❌ Google API error.")
    else:
        st.warning("⏺️ Recording already in progress...")

#text input
elif input_mode == "✍️ Text":
    st.subheader("Enter Your Symptoms")
    user_text = st.text_area("Describe your symptoms here:")
    st.session_state.user_input = user_text

#generate summary
if st.button("📄 Generate Summary"):
    if not st.session_state.user_input.strip():
        st.warning("Please provide input via voice or text.")
    else:
        st.session_state.generated = True

# ✅ Run generation if flag is set
if st.session_state.generated:
    with st.spinner("Analyzing your input with Gemini AI..."):
        try:
            prompt = f"""
You're a medical assistant. From this description, extract a consultation summary in this format:

📄 Patient Consultation Summary

📅 Date: {datetime.today().strftime('%Y-%m-%d')}
👤 Patient Name: [Optional / Anonymous]
🆔 Patient ID: [Optional]

🧰 Reported Symptoms:
...

⏳ Duration of Symptoms:
...

⚖️ Severity:
...

📋 Medical History:
...

💊 Current Medications:
...

🧠 Additional Notes:
...

🦠 Suggested Next Steps:
...

📍 Location (Optional):
🗣 Language Detected:

Here is the patient input:
\"\"\"{st.session_state.user_input}\"\"\"
"""
            response = model.generate_content(prompt)
            summary = response.text

            # Generate PDF only if not already created
            if not st.session_state.pdf_bytes or not st.session_state.pdf_filename:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                clean_summary = remove_emojis(summary)
                for line in clean_summary.split("\n"):
                    pdf.multi_cell(0, 10, line)

                now = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"patient_summary_{now}.pdf"
                pdf_bytes = pdf.output(dest="S").encode("latin1")

                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pdf_filename = filename

            # Header + Buttons
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown("#### 📄 Generated Summary")
            with col2:
                st.download_button(
                    label="📥Download",
                    data=st.session_state.pdf_bytes,
                    file_name=st.session_state.pdf_filename,
                    mime="application/pdf",
                    key="download_button_top"
                )
            with col3:
                if st.button("📤Share to Consultant", key="share_button_top"):
                    try:
                        cursor.execute(
                            "INSERT INTO summaries (filename, data, timestamp) VALUES (?, ?, ?)",
                            (
                                st.session_state.pdf_filename,
                                st.session_state.pdf_bytes,
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                        )
                        conn.commit()
                        st.success("✅Shared")
                    except Exception as db_err:
                        st.error(f"❌ Error storing in DB: {db_err}")

            st.text_area(label="", value=summary, height=300)

        except Exception as e:
            st.error(f"❌ Gemini Error: {str(e)}")
