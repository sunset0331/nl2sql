"""
SQL Generator Module

Generates SQL queries from natural language questions using LLM.
"""

import re
from config import SQL_GENERATION_PROMPT
from utils.openai_client import get_client


def generate_sql(question: str, formatted_schema: str, reasoning: str) -> str:
    """
    Generate a SQL query based on the question, schema, and reasoning.
    
    Args:
        question: Natural language question
        formatted_schema: Formatted database schema
        reasoning: Chain-of-thought reasoning steps
        
    Returns:
        Generated SQL query
    """
    client = get_client()
    
    prompt = SQL_GENERATION_PROMPT.format(
        schema=formatted_schema,
        question=question,
        reasoning=reasoning
    )
    
    response = client.generate_text(prompt)
    
    # Extract SQL from response
    sql = extract_sql_from_response(response)
    
    return sql


def extract_sql_from_response(response: str) -> str:
    """
    Extract clean SQL query from LLM response.
    
    Handles various formats like:
    - Raw SQL
    - SQL in code blocks
    - SQL with explanations
    
    Args:
        response: Raw LLM response
        
    Returns:
        Clean SQL query
    """
    # Try to find SQL in code blocks first
    code_block_pattern = r'```(?:sql)?\s*(.*?)```'
    matches = re.findall(code_block_pattern, response, re.DOTALL | re.IGNORECASE)
    
    if matches:
        return matches[0].strip()
    
    # Look for SQL keywords to find the query
    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'WITH']
    
    lines = response.strip().split('\n')
    sql_lines = []
    in_sql = False
    
    for line in lines:
        line_upper = line.strip().upper()
        
        # Start capturing if we see a SQL keyword
        if any(line_upper.startswith(kw) for kw in sql_keywords):
            in_sql = True
        
        if in_sql:
            # Stop if we hit obvious non-SQL content
            if line.strip().startswith('#') or line.strip().startswith('//'):
                break
            sql_lines.append(line)
    
    if sql_lines:
        return '\n'.join(sql_lines).strip().rstrip(';') + ';'
    
    # Fallback: return cleaned response
    return response.strip()


def format_sql(sql: str) -> str:
    """
    Format SQL for better readability.
    
    Args:
        sql: Raw SQL query
        
    Returns:
        Formatted SQL query
    """
    try:
        import sqlparse
        return sqlparse.format(
            sql,
            reindent=True,
            keyword_case='upper',
            identifier_case='lower'
        )
    except ImportError:
        return sql
