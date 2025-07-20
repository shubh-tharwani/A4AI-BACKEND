from fastapi import APIRouter, Form
from services.planning_service import generate_lesson_plan

#router = APIRouter(prefix="/planning", tags=["Lesson Planning"])

#@router.post("/generate")
async def create_plan(class_id: str = Form(...), plan_type: str = Form("weekly"), duration: int = Form(7)):
    return await generate_lesson_plan(class_id, plan_type, duration)
