from fastapi import APIRouter, Depends
from auth_middleware import firebase_auth
from services.content_agent import generate_activity, generate_visual_aid

router = APIRouter(prefix="/content", tags=["Content Agent"])

@router.get("/activity", dependencies=[Depends(firebase_auth)])
def get_activity(grade: int, topic: str):
    return {"activity": generate_activity(grade, topic)}

@router.get("/visual-aid", dependencies=[Depends(firebase_auth)])
def get_visual_aid(concept: str):
    return {"visual_aid": generate_visual_aid(concept)}
