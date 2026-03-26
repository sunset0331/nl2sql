"""
Exact Match Evaluator

Compares SQL queries using string normalization.
"""

from ..core.normalizer import SQLNormalizer


def evaluate_exact_match(gold_sql: str, predicted_sql: str) -> bool:
    """
    Check if two SQL queries match exactly after normalization.
    
    Args:
        gold_sql: Ground truth SQL query
        predicted_sql: Predicted SQL query
        
    Returns:
        True if queries match after normalization
    """
    return SQLNormalizer.exact_match(gold_sql, predicted_sql)
