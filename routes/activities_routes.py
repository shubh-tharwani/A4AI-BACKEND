from fastapi import APIRouter
from services.activities_service import generate_interactive_story, generate_ar_prompt, assign_badge

router = APIRouter(prefix="/activities", tags=["Activities"])

@router.get("/story")
async def get_story(grade: int, topic: str, language: str):
    return await generate_interactive_story(grade, topic, language)

@router.get("/ar-scene")
async def get_ar_scene(topic: str):
    return await generate_ar_prompt(topic)

@router.post("/reward/{user_id}")
async def reward_user(user_id: str, badge: str):
    return await assign_badge(user_id, badge)
