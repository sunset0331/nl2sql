"""
Chain-of-Thought Reasoning Module

Breaks down natural language questions into logical steps for SQL generation.
"""

from config import REASONING_PROMPT
from utils.openai_client import get_client


def plan_query(question: str, formatted_schema: str) -> str:
    """
    Generate step-by-step reasoning for how to construct the SQL query.
    
    Uses chain-of-thought prompting to break down:
    1. Required tables
    2. Columns to select
    3. Joins needed
    4. Filters/conditions
    5. Aggregations/groupings
    
    Args:
        question: Natural language question
        formatted_schema: Formatted database schema
        
    Returns:
        Step-by-step reasoning text
    """
    client = get_client()
    
    prompt = REASONING_PROMPT.format(
        schema=formatted_schema,
        question=question
    )
    
    reasoning = client.generate_text(prompt)
    
    return reasoning


def extract_reasoning_steps(reasoning_text: str) -> list:
    """
    Parse the reasoning text into individual steps.
    
    Args:
        reasoning_text: Raw reasoning from LLM
        
    Returns:
        List of reasoning steps
    """
    steps = []
    lines = reasoning_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        # Match numbered steps or bullet points
        if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
            # Clean up the step
            clean_step = line.lstrip('0123456789.-•) ').strip()
            if clean_step:
                steps.append(clean_step)
    
    return steps if steps else [reasoning_text]
