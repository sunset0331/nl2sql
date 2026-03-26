"""
Answer Generator Module

Generates human-readable explanations of the SQL query and what it does.
"""

from config import ANSWER_GENERATION_PROMPT
from utils.openai_client import get_client


def generate_answer(question: str, sql: str, reasoning: str) -> str:
    """
    Generate a human-readable explanation of what the SQL query does.
    
    Args:
        question: Original natural language question
        sql: Generated SQL query
        reasoning: Chain-of-thought reasoning steps
        
    Returns:
        Human-readable explanation of the query
    """
    client = get_client()
    
    prompt = ANSWER_GENERATION_PROMPT.format(
        question=question,
        sql=sql,
        reasoning=reasoning
    )
    
    response = client.generate_text(prompt, max_tokens=512)
    
    return clean_answer(response)


def clean_answer(answer: str) -> str:
    """
    Clean up the answer text.
    
    Args:
        answer: Raw answer from LLM
        
    Returns:
        Cleaned answer text
    """
    # Remove any markdown formatting
    answer = answer.strip()
    
    # Remove common prefixes the LLM might add
    prefixes_to_remove = [
        "Here's the explanation:",
        "Here is the explanation:",
        "Answer:",
        "Explanation:",
    ]
    
    for prefix in prefixes_to_remove:
        if answer.lower().startswith(prefix.lower()):
            answer = answer[len(prefix):].strip()
    
    return answer
