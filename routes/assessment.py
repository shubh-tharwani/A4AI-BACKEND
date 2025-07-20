from fastapi import APIRouter, Depends
from auth_middleware import firebase_auth
from services.assessment_agent import create_test, score_answer

router = APIRouter(prefix="/assessment-old", tags=["Assessment Agent"])

@router.get("/create-test", dependencies=[Depends(firebase_auth)])
def get_test(grade: int, subject: str):
    return {"test": create_test(grade, subject)}

@router.get("/score", dependencies=[Depends(firebase_auth)])
def get_score(question: str, answer: str):
    return {"score": score_answer(question, answer)}
