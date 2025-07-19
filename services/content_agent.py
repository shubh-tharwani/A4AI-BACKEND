from services.vertex_ai import generate_text

def generate_activity(grade: int, topic: str):
    prompt = f"Create an engaging classroom activity for grade {grade} on {topic}."
    return generate_text(prompt)

def generate_visual_aid(concept: str):
    prompt = f"Explain {concept} with a simple diagram description and easy words."
    return generate_text(prompt)
