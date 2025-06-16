Patient_chatbot

This is an advanced AI healthcare assistant that listens to patients (via audio or text), understands their symptoms using Gemini AI (Google Generative AI), and generates a clear, professional consultation summary in PDF format.

Built using Streamlit (frontend) and Python (backend), the chatbot stores the PDF only when the patient chooses to share it with a consultant. In that case, the PDF is securely saved in a SQLite3 database.
