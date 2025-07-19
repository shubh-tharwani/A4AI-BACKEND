from services.vertex_ai import generate_text

def create_test(grade: int, subject: str):
    prompt = f"Create 5 multiple-choice questions for grade {grade} in {subject} with correct answers."
    return generate_text(prompt)

def score_answer(question: str, answer: str):
    prompt = f"Evaluate the answer for this question:\nQ: {question}\nA: {answer}. Provide score and feedback."
    return generate_text(prompt)
