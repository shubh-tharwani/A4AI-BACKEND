from fastapi import FastAPI
from routes import content, assessment, voice, planning, auth

app = FastAPI(title="A4AI Backend")

app.include_router(auth.router)
app.include_router(content.router)
app.include_router(assessment.router)
app.include_router(voice.router)
app.include_router(planning.router)

@app.get("/")
def root():
    return {"message": "A4AI Backend Running!"}
