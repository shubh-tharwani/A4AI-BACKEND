import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "a4ai-10bf3")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
VERTEX_MODEL = os.getenv("VERTEX_MODEL", "gemini-2.0-flash-001")
GOOGLE_GEMINI_MODEL = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash-001")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "./firebase_key.json")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./vertex_ai_key.json")
