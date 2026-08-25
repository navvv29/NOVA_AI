from langchain_core.tools import tool


@tool
def generate_quiz(
    topic: str,
    num_questions: int = 5,
    difficulty: str = "medium",
    question_type: str = "mixed",
) -> str:
    """Generate a quiz on any topic to test understanding.

    This tool prepares quiz parameters for the LLM to generate questions.
    The LLM will use this to create a tailored quiz.

    Parameters:
    - topic: The subject or concept to quiz on (e.g., "Python decorators", "OSI model", "binary trees")
    - num_questions: Number of questions (1-20, default 5)
    - difficulty: 'easy', 'medium', or 'hard'
    - question_type: 'mcq' (multiple choice), 'short_answer', 'true_false', or 'mixed' (default)
    """
    num_questions = max(1, min(20, num_questions))
    difficulty = difficulty.lower() if difficulty.lower() in ("easy", "medium", "hard") else "medium"
    question_type = question_type.lower() if question_type.lower() in ("mcq", "short_answer", "true_false", "mixed") else "mixed"

    return (
        f"QUIZ_GENERATION_REQUEST\n"
        f"topic: {topic}\n"
        f"num_questions: {num_questions}\n"
        f"difficulty: {difficulty}\n"
        f"question_type: {question_type}\n\n"
        f"Generate a {difficulty} quiz with {num_questions} {question_type} questions about {topic}. "
        f"Format each question clearly with numbers. For MCQ, provide 4 options (A-D) and mark the correct one. "
        f"For true/false, state whether the answer is True or False. "
        f"After all questions, provide an answer key."
    )
