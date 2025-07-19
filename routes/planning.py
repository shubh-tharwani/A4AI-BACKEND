from fastapi import APIRouter, Depends
from auth_middleware import firebase_auth
from services.planning_agent import generate_lesson_plan

router = APIRouter(prefix="/planning", tags=["Planning Agent"])

@router.get("/lesson-plan", dependencies=[Depends(firebase_auth)])
def get_lesson_plan(grades: str, topics: str):
    return {"lesson_plan": generate_lesson_plan(grades, topics)}
