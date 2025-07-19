import os
import vertexai
from vertexai.generative_models import GenerativeModel
from config import PROJECT_ID, LOCATION, VERTEX_MODEL, GOOGLE_APPLICATION_CREDENTIALS

# Set credentials before initializing Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

def generate_text(prompt: str) -> str:
    try:
        # Use the Gemini model
        model = GenerativeModel(VERTEX_MODEL)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating text: {str(e)}"
