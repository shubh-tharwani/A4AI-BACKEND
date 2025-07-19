from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os

router = APIRouter(prefix="/auth", tags=["Authentication"])

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(request: LoginRequest):
    if not FIREBASE_API_KEY:
        raise HTTPException(status_code=500, detail="Firebase API key not configured")
    
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": request.email,
        "password": request.password,
        "returnSecureToken": True
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")
