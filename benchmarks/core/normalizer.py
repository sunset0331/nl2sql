"""
SQL Normalizer

Normalizes SQL queries for comparison.
"""

import re


class SQLNormalizer:
    """Normalizes SQL queries for comparison."""
    
    @staticmethod
    def normalize(sql: str) -> str:
        """Normalize SQL for exact match comparison."""
        if not sql:
            return ""
        
        # Convert to lowercase
        sql = sql.lower()
        
        # Remove comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Normalize whitespace
        sql = re.sub(r'\s+', ' ', sql)
        
        # Remove trailing semicolon
        sql = sql.strip().rstrip(';')
        
        # Normalize quotes
        sql = sql.replace('"', "'")
        
        # Remove extra spaces around operators
        sql = re.sub(r'\s*([=<>!]+)\s*', r' \1 ', sql)
        sql = re.sub(r'\s*,\s*', ', ', sql)
        sql = re.sub(r'\s*\(\s*', ' (', sql)
        sql = re.sub(r'\s*\)\s*', ') ', sql)
        
        # Final cleanup
        sql = ' '.join(sql.split())
        
        return sql.strip()
    
    @staticmethod
    def exact_match(gold: str, predicted: str) -> bool:
        """Check if two SQL queries are exactly equivalent after normalization."""
        return SQLNormalizer.normalize(gold) == SQLNormalizer.normalize(predicted)
