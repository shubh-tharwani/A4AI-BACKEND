import os
import sys
import vertexai
from vertexai.generative_models import GenerativeModel

# Add parent directory to path to import config.py from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Set credentials before initializing Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

# Initialize Vertex AI
vertexai.init(project=config.PROJECT_ID, location=config.LOCATION)

def generate_text(prompt: str) -> str:
    try:
        # Use the Gemini model
        model = GenerativeModel(config.VERTEX_MODEL)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating text: {str(e)}"
