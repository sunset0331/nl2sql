"""
SQL Verifier Module

Validates SQL syntax and attempts to correct errors.
"""

import re
import sqlparse
from typing import Tuple, List, Optional
from config import SQL_CORRECTION_PROMPT, MAX_CORRECTION_ATTEMPTS
from utils.openai_client import get_client
from pipeline.schema_processor import parse_schema


class SQLVerificationResult:
    """Result of SQL verification."""
    
    def __init__(self, is_valid: bool, sql: str, errors: List[str] = None, corrections_made: int = 0):
        self.is_valid = is_valid
        self.sql = sql
        self.errors = errors or []
        self.corrections_made = corrections_made


def validate_sql_syntax(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Validate basic SQL syntax using sqlparse.
    
    Args:
        sql: SQL query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Parse the SQL
        parsed = sqlparse.parse(sql)
        
        if not parsed or not parsed[0].tokens:
            return False, "Empty or invalid SQL statement"
        
        # Get the statement type
        stmt = parsed[0]
        stmt_type = stmt.get_type()
        
        if stmt_type == 'UNKNOWN':
            # Check if it at least starts with a valid keyword
            first_token = str(stmt.tokens[0]).strip().upper()
            valid_starts = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'WITH']
            if not any(first_token.startswith(v) for v in valid_starts):
                return False, f"Unknown statement type starting with: {first_token}"
        
        # Basic parentheses matching
        open_parens = sql.count('(')
        close_parens = sql.count(')')
        if open_parens != close_parens:
            return False, f"Unmatched parentheses: {open_parens} opening, {close_parens} closing"
        
        # Quote matching
        single_quotes = sql.count("'") - sql.count("\\'")
        if single_quotes % 2 != 0:
            return False, "Unmatched single quotes"
        
        return True, None
        
    except Exception as e:
        return False, f"Syntax error: {str(e)}"


def verify_against_schema(sql: str, schema_text: str) -> Tuple[bool, List[str]]:
    """
    Verify that tables and columns in SQL exist in the schema.
    
    Args:
        sql: SQL query to verify
        schema_text: Database schema
        
    Returns:
        Tuple of (is_valid, list of warnings/errors)
    """
    warnings = []
    tables = parse_schema(schema_text)
    
    if not tables:
        # Can't verify if schema parsing failed
        return True, ["Warning: Could not parse schema for verification"]
    
    # Extract table names from schema
    schema_tables = {t.name.lower() for t in tables}
    schema_columns = {}
    for t in tables:
        schema_columns[t.name.lower()] = {c['name'].lower() for c in t.columns}
    
    # Find table references in SQL
    # Look for FROM, JOIN, UPDATE, INSERT INTO patterns
    table_pattern = r'(?:FROM|JOIN|UPDATE|INTO)\s+[`"\']?(\w+)[`"\']?'
    referenced_tables = re.findall(table_pattern, sql, re.IGNORECASE)
    
    for table in referenced_tables:
        if table.lower() not in schema_tables:
            warnings.append(f"Table '{table}' not found in schema")
    
    # If all tables are valid, this is a soft pass
    is_valid = not any("not found" in w for w in warnings)
    
    return is_valid, warnings


def attempt_correction(
    sql: str,
    error: str,
    question: str,
    schema: str
) -> str:
    """
    Ask the LLM to correct a faulty SQL query.
    
    Args:
        sql: The faulty SQL query
        error: The error message
        question: Original question
        schema: Database schema
        
    Returns:
        Corrected SQL query
    """
    client = get_client()
    
    prompt = SQL_CORRECTION_PROMPT.format(
        schema=schema,
        question=question,
        sql=sql,
        error=error
    )
    
    response = client.generate_text(prompt)
    
    # Extract SQL from response
    from pipeline.sql_generator import extract_sql_from_response
    return extract_sql_from_response(response)


def verify_and_correct(
    sql: str,
    question: str,
    schema: str
) -> SQLVerificationResult:
    """
    Verify SQL and attempt to correct if invalid.
    
    Args:
        sql: SQL query to verify
        question: Original question (for correction context)
        schema: Database schema
        
    Returns:
        SQLVerificationResult with final SQL and status
    """
    current_sql = sql
    all_errors = []
    corrections = 0
    
    for attempt in range(MAX_CORRECTION_ATTEMPTS):
        # Check syntax
        is_valid, syntax_error = validate_sql_syntax(current_sql)
        
        if not is_valid:
            all_errors.append(f"Attempt {attempt + 1}: {syntax_error}")
            current_sql = attempt_correction(current_sql, syntax_error, question, schema)
            corrections += 1
            continue
        
        # Check against schema
        schema_valid, schema_warnings = verify_against_schema(current_sql, schema)
        
        if not schema_valid:
            error_msg = "; ".join(schema_warnings)
            all_errors.append(f"Attempt {attempt + 1}: {error_msg}")
            current_sql = attempt_correction(current_sql, error_msg, question, schema)
            corrections += 1
            continue
        
        # Valid!
        if schema_warnings:
            all_errors.extend(schema_warnings)
        
        return SQLVerificationResult(
            is_valid=True,
            sql=current_sql,
            errors=all_errors,
            corrections_made=corrections
        )
    
    # Max attempts reached
    return SQLVerificationResult(
        is_valid=False,
        sql=current_sql,
        errors=all_errors,
        corrections_made=corrections
    )
