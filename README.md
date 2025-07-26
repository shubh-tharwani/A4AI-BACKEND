# AI Education Backend

## Features
✅ 4 AI Agents:
- Content Agent (Activities & Visual Aids)
- Assessment Agent (Tests & Scoring)
- Voice Agent (Speech-to-Text)
- Planning Agent (Lesson Scheduling)

✅ Vertex AI (Gemini) Integration  
✅ Firebase Authentication  
✅ Google Cloud Speech-to-Text  
✅ Dockerized for Cloud Run  
✅ Postman Collection Included  

## Setup
1. Create `.env` file from `.env.example`

```bash
# Create virtual environment in the root directory
python -m venv .venv

# Activate (each new terminal)
# macOS/Linux:
source .venv/bin/activate
# Windows CMD:
.venv\Scripts\activate.bat
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

# Start the server:

C:/Users/gauth/Documents/BACKEND_A4AI/A4AI-BACKEND/.venv/Scripts/python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Alternative (if virtual environment is activated):
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Stop the server:

Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force

---
