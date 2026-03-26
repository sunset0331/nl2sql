"""
NL2SQL Core Pipeline

The core pipeline logic used by both the Flask app and benchmarks.
This ensures consistent behavior across all execution paths.
"""

from dataclasses import dataclass
from typing import Optional

from pipeline.schema_processor import format_schema_for_prompt
from pipeline.reasoning import plan_query
from pipeline.sql_generator import generate_sql, format_sql
from pipeline.verifier import verify_and_correct
from pipeline.answer_generator import generate_answer
from security import SecureLLMPipeline, SQL_SAFETY_DISCLAIMER


@dataclass
class PipelineResult:
    """Result from the NL2SQL pipeline."""
    success: bool
    sql: str = ""
    reasoning: str = ""
    answer: str = ""
    is_valid: bool = True
    corrections_made: int = 0
    verification_notes: list = None
    error: str = ""
    security_blocked: bool = False
    disclaimer: str = SQL_SAFETY_DISCLAIMER
    
    def __post_init__(self):
        if self.verification_notes is None:
            self.verification_notes = []


class NL2SQLPipeline:
    """
    Core NL2SQL pipeline that converts natural language to SQL.
    
    This class encapsulates the entire pipeline flow and is used by:
    - Flask app (/generate endpoint)
    - Benchmark suite
    - Any other consumers
    
    This ensures identical behavior across all execution contexts.
    """
    
    def __init__(self, enable_security_logging: bool = False):
        """
        Initialize the pipeline.
        
        Args:
            enable_security_logging: Whether to log security events
        """
        self.security = SecureLLMPipeline(enable_logging=enable_security_logging)
    
    def generate(
        self,
        question: str,
        schema: str,
        include_answer: bool = True
    ) -> PipelineResult:
        """
        Run the full NL2SQL pipeline.
        
        Args:
            question: Natural language question
            schema: Database schema (CREATE TABLE statements)
            include_answer: Whether to generate human-readable answer
            
        Returns:
            PipelineResult with SQL, reasoning, and metadata
        """
        # Validate inputs
        if not schema or not schema.strip():
            return PipelineResult(
                success=False,
                error="Please provide a database schema"
            )
        
        if not question or not question.strip():
            return PipelineResult(
                success=False,
                error="Please provide a question"
            )
        
        question = question.strip()
        schema = schema.strip()
        
        # Step 1: Security Layer - Validate and sanitize inputs
        validation = self.security.validate_input(question, schema)
        
        if not validation.is_safe:
            return PipelineResult(
                success=False,
                error=validation.rejection_reason,
                security_blocked=True
            )
        
        # Use sanitized input
        question = validation.sanitized_input
        
        try:
            # Step 2: Process and format the schema
            formatted_schema = format_schema_for_prompt(schema)
            
            # Step 3: Generate chain-of-thought reasoning
            reasoning = plan_query(question, formatted_schema)
            
            # Security: Validate LLM output for leakage
            reasoning = self.security.validate_output(reasoning)
            
            # Step 4: Generate SQL based on reasoning
            sql = generate_sql(question, formatted_schema, reasoning)
            
            # Step 5: Verify and correct SQL
            verification = verify_and_correct(sql, question, schema)
            
            # Format the final SQL
            final_sql = format_sql(verification.sql)
            
            # Security: Validate final SQL output
            final_sql = self.security.validate_output(final_sql)
            
            # Step 6: Generate human-readable answer (optional)
            answer = ""
            if include_answer:
                answer = generate_answer(question, final_sql, reasoning)
                # Security: Validate answer output
                answer = self.security.validate_output(answer)
            
            return PipelineResult(
                success=True,
                sql=final_sql,
                reasoning=reasoning,
                answer=answer,
                is_valid=verification.is_valid,
                corrections_made=verification.corrections_made,
                verification_notes=verification.errors
            )
            
        except Exception as e:
            return PipelineResult(
                success=False,
                error=str(e)
            )
    
    def generate_sql_only(self, question: str, schema: str) -> str:
        """
        Convenience method that returns just the SQL string.
        
        Useful for benchmarking where we only need the SQL output.
        Raises ValueError on failure.
        
        Args:
            question: Natural language question
            schema: Database schema
            
        Returns:
            Generated SQL string
            
        Raises:
            ValueError: If generation fails
        """
        result = self.generate(question, schema, include_answer=False)
        
        if not result.success:
            raise ValueError(result.error)
        
        return result.sql


# Singleton instance for convenience
_default_pipeline = None


def get_pipeline(enable_security_logging: bool = False) -> NL2SQLPipeline:
    """Get the pipeline instance."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = NL2SQLPipeline(enable_security_logging)
    return _default_pipeline
