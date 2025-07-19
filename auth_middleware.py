from fastapi import Request, HTTPException
from firebase_config import verify_token

async def firebase_auth(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = auth_header.split(" ")[1]
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
    request.state.user = user
