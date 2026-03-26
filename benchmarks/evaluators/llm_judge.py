"""
LLM-as-Judge for SQL Semantic Equivalence

Implements semantic SQL comparison using LLM as a judge.
Based on best practices from "How to Use LLM as a Judge (Without Getting Burned)".

Key principles applied:
1. Reference-based evaluation (compare against gold SQL)
2. Require reasoning before scores
3. Clear rubric with specific criteria
4. Structured output format
"""

import re
import json
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class JudgeResult:
    """Result of LLM judge evaluation."""
    is_equivalent: bool
    confidence: str  # "high", "medium", "low"
    score: int  # 0-5 scale
    reasoning: str
    components_analysis: dict


# Reference-based SQL equivalence prompt with clear rubric
SQL_JUDGE_PROMPT = """You are an expert SQL evaluator. Your task is to determine if two SQL queries are SEMANTICALLY EQUIVALENT - meaning they would return the same results when executed on the same database.

## Evaluation Criteria

Analyze these components:

### 1. Tables & Joins (0-1 points)
- 0: Different tables or incompatible join logic
- 1: Same tables with equivalent join conditions

### 2. Selected Columns (0-1 points)  
- 0: Different columns or aggregations
- 1: Same columns/aggregations (order doesn't matter)

### 3. WHERE Conditions (0-1 points)
- 0: Different filter logic
- 1: Equivalent filter conditions

### 4. GROUP BY / ORDER BY (0-1 points)
- 0: Different grouping or ordering that changes results
- 1: Equivalent grouping and ordering

### 5. Overall Logic (0-1 points)
- 0: Queries would return different results
- 1: Queries are logically equivalent

## Important Notes
- IGNORE differences in: capitalization, whitespace, alias names, quote styles
- Column order in SELECT doesn't matter for equivalence
- Different syntax for same logic (e.g., INNER JOIN vs JOIN) is equivalent

## Input

**Question:** {question}

**Gold SQL (Reference):**
```sql
{gold_sql}
```

**Predicted SQL (To Evaluate):**
```sql
{predicted_sql}
```

## Instructions
1. Analyze each component systematically
2. Provide specific reasoning with examples from both queries
3. Score each criterion
4. Determine overall equivalence

## Output Format (JSON)

```json
{{
    "analysis": {{
        "tables_joins": {{
            "gold": "<tables and joins in gold>",
            "predicted": "<tables and joins in predicted>",
            "equivalent": true/false,
            "score": 0 or 1,
            "reason": "<explanation>"
        }},
        "selected_columns": {{
            "gold": "<columns in gold>",
            "predicted": "<columns in predicted>", 
            "equivalent": true/false,
            "score": 0 or 1,
            "reason": "<explanation>"
        }},
        "where_conditions": {{
            "gold": "<conditions in gold>",
            "predicted": "<conditions in predicted>",
            "equivalent": true/false,
            "score": 0 or 1,
            "reason": "<explanation>"
        }},
        "groupby_orderby": {{
            "gold": "<grouping/ordering in gold>",
            "predicted": "<grouping/ordering in predicted>",
            "equivalent": true/false,
            "score": 0 or 1,
            "reason": "<explanation>"
        }},
        "overall_logic": {{
            "equivalent": true/false,
            "score": 0 or 1,
            "reason": "<final determination>"
        }}
    }},
    "total_score": <0-5>,
    "is_equivalent": true/false,
    "confidence": "high" | "medium" | "low",
    "summary": "<one sentence summary>"
}}
```

Respond ONLY with the JSON object, no other text."""


def create_judge_client():
    """Create the OpenAI client for judging."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from utils.openai_client import OpenAIClient
    return OpenAIClient()


def parse_judge_response(response: str) -> dict:
    """Parse JSON from judge response, handling markdown code blocks."""
    # Remove markdown code blocks if present
    response = response.strip()
    if response.startswith("```"):
        # Extract content between code blocks
        match = re.search(r'```(?:json)?\s*(.*?)```', response, re.DOTALL)
        if match:
            response = match.group(1).strip()
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to find JSON object in response
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    
    # Return default structure on parse failure
    return {
        "total_score": 0,
        "is_equivalent": False,
        "confidence": "low",
        "summary": "Failed to parse judge response",
        "analysis": {},
        "parse_error": True
    }


def judge_sql_equivalence(
    question: str,
    gold_sql: str,
    predicted_sql: str,
    client=None
) -> JudgeResult:
    """
    Use LLM to judge if two SQL queries are semantically equivalent.
    
    Args:
        question: The natural language question
        gold_sql: The reference/gold SQL query
        predicted_sql: The generated SQL query to evaluate
        client: Optional OpenAI client (creates one if not provided)
        
    Returns:
        JudgeResult with equivalence determination and reasoning
    """
    if client is None:
        client = create_judge_client()
    
    # Format the prompt
    prompt = SQL_JUDGE_PROMPT.format(
        question=question,
        gold_sql=gold_sql,
        predicted_sql=predicted_sql
    )
    
    try:
        # Call LLM
        response = client.generate_text(prompt, max_tokens=1500, temperature=0.0)
        
        # Parse response
        result = parse_judge_response(response)
        
        return JudgeResult(
            is_equivalent=result.get("is_equivalent", False),
            confidence=result.get("confidence", "low"),
            score=result.get("total_score", 0),
            reasoning=result.get("summary", ""),
            components_analysis=result.get("analysis", {})
        )
        
    except Exception as e:
        return JudgeResult(
            is_equivalent=False,
            confidence="low",
            score=0,
            reasoning=f"Judge error: {str(e)}",
            components_analysis={}
        )


def batch_judge(
    examples: list,
    client=None,
    verbose: bool = True
) -> list:
    """
    Judge multiple SQL pairs.
    
    Args:
        examples: List of dicts with 'question', 'gold_sql', 'predicted_sql'
        client: Optional OpenAI client
        verbose: Whether to print progress
        
    Returns:
        List of JudgeResult objects
    """
    if client is None:
        client = create_judge_client()
    
    results = []
    for i, ex in enumerate(examples):
        if verbose and (i + 1) % 10 == 0:
            print(f"  Judged {i + 1}/{len(examples)}")
        
        result = judge_sql_equivalence(
            question=ex.get("question", ""),
            gold_sql=ex.get("gold_sql", ""),
            predicted_sql=ex.get("predicted_sql", ""),
            client=client
        )
        results.append(result)
    
    return results


# Quick equivalence check for common patterns
def quick_equivalence_check(gold: str, predicted: str) -> Optional[bool]:
    """
    Fast equivalence check for obvious cases before calling LLM.
    Returns None if LLM judge is needed.
    """
    # Normalize both
    def normalize(sql):
        sql = sql.lower().strip()
        sql = re.sub(r'\s+', ' ', sql)
        sql = sql.rstrip(';')
        # Remove quotes
        sql = sql.replace('"', '').replace("'", '')
        # Normalize AS keyword
        sql = re.sub(r'\s+as\s+\w+', '', sql)
        return sql
    
    g = normalize(gold)
    p = normalize(predicted)
    
    # Exact match after normalization
    if g == p:
        return True
    
    # Parse failures
    if not predicted.strip() or "error" in predicted.lower():
        return False
    
    # Need LLM judge
    return None
