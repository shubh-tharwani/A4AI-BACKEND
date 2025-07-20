from fastapi import APIRouter, Form
from services.visual_aid_service import generate_visual_aid

router = APIRouter(prefix="/visual-aid", tags=["Visual Aids"])

@router.post("/image")
async def create_image(prompt: str = Form(...)):
    return await generate_visual_aid(prompt, asset_type="image")

@router.post("/video")
async def create_video(prompt: str = Form(...)):
    return await generate_visual_aid(prompt, asset_type="video")
