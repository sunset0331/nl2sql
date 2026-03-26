"""
Execution Accuracy Evaluator

Evaluates SQL queries by executing them against actual SQLite databases
and comparing the results.
"""

import sqlite3
from pathlib import Path
from typing import Tuple, Optional, List, Any
import hashlib


class ExecutionEvaluator:
    """
    Evaluates SQL queries by executing them and comparing results.
    
    This requires the actual Spider database files (.sqlite) to be present.
    """
    
    def __init__(self, databases_dir: str):
        """
        Initialize the execution evaluator.
        
        Args:
            databases_dir: Path to directory containing Spider database folders
        """
        self.databases_dir = Path(databases_dir)
        self._connection_cache = {}
    
    def get_database_path(self, db_id: str) -> Optional[Path]:
        """Get the path to a database file."""
        # Spider databases are in subdirectories named after db_id
        db_path = self.databases_dir / db_id / f"{db_id}.sqlite"
        if db_path.exists():
            return db_path
        
        # Try alternate naming
        db_path = self.databases_dir / db_id / "database.sqlite"
        if db_path.exists():
            return db_path
            
        return None
    
    def execute_sql(self, sql: str, db_id: str, timeout: float = 30.0) -> Tuple[bool, Optional[List], Optional[str]]:
        """
        Execute SQL query against a database.
        
        Args:
            sql: SQL query to execute
            db_id: Database identifier
            timeout: Query timeout in seconds
            
        Returns:
            Tuple of (success, results, error_message)
        """
        db_path = self.get_database_path(db_id)
        if db_path is None:
            return False, None, f"Database not found: {db_id}"
        
        try:
            conn = sqlite3.connect(str(db_path), timeout=timeout)
            conn.text_factory = str
            cursor = conn.cursor()
            
            cursor.execute(sql)
            results = cursor.fetchall()
            
            conn.close()
            return True, results, None
            
        except sqlite3.Error as e:
            return False, None, f"SQL Error: {str(e)}"
        except Exception as e:
            return False, None, f"Execution Error: {str(e)}"
    
    def normalize_results(self, results: List) -> str:
        """
        Normalize query results for comparison.
        
        Sorts rows and converts to a canonical string representation.
        """
        if results is None:
            return ""
        
        # Convert all values to strings and sort
        normalized = []
        for row in results:
            normalized_row = tuple(
                str(v).lower().strip() if v is not None else "null"
                for v in row
            )
            normalized.append(normalized_row)
        
        # Sort rows for order-independent comparison
        normalized.sort()
        
        return str(normalized)
    
    def results_match(self, results1: List, results2: List) -> bool:
        """Check if two result sets are equivalent."""
        norm1 = self.normalize_results(results1)
        norm2 = self.normalize_results(results2)
        return norm1 == norm2
    
    def evaluate(
        self,
        gold_sql: str,
        predicted_sql: str,
        db_id: str
    ) -> Tuple[bool, Optional[bool], str]:
        """
        Evaluate execution accuracy.
        
        Args:
            gold_sql: Ground truth SQL query
            predicted_sql: Predicted SQL query
            db_id: Database identifier
            
        Returns:
            Tuple of (could_execute, results_match, message)
            - could_execute: Whether both queries could be executed
            - results_match: Whether results are equivalent (None if couldn't execute)
            - message: Status message
        """
        # Execute gold query
        gold_success, gold_results, gold_error = self.execute_sql(gold_sql, db_id)
        if not gold_success:
            return False, None, f"Gold query failed: {gold_error}"
        
        # Execute predicted query
        pred_success, pred_results, pred_error = self.execute_sql(predicted_sql, db_id)
        if not pred_success:
            return True, False, f"Predicted query failed: {pred_error}"
        
        # Compare results
        match = self.results_match(gold_results, pred_results)
        
        if match:
            return True, True, "Results match"
        else:
            gold_count = len(gold_results) if gold_results else 0
            pred_count = len(pred_results) if pred_results else 0
            return True, False, f"Results differ (gold: {gold_count} rows, predicted: {pred_count} rows)"


def evaluate_execution(
    gold_sql: str,
    predicted_sql: str,
    db_id: str,
    databases_dir: str
) -> Tuple[Optional[bool], str]:
    """
    Convenience function to evaluate execution accuracy.
    
    Args:
        gold_sql: Ground truth SQL query
        predicted_sql: Predicted SQL query
        db_id: Database identifier
        databases_dir: Path to Spider databases directory
        
    Returns:
        Tuple of (match_result, message)
        - match_result: True if results match, False if not, None if couldn't execute
        - message: Status message
    """
    evaluator = ExecutionEvaluator(databases_dir)
    could_execute, match, message = evaluator.evaluate(gold_sql, predicted_sql, db_id)
    
    if not could_execute:
        return None, message
    
    return match, message
