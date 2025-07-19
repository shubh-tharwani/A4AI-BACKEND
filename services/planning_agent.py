from services.vertex_ai import generate_text

def generate_lesson_plan(grades: str, topics: str):
    prompt = f"Create an optimized teaching schedule for grades {grades} covering topics: {topics}. Use a table format."
    return generate_text(prompt)
