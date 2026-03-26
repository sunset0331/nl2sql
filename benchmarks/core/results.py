"""
Benchmark Data Classes

Defines result and report structures for benchmarking.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class BenchmarkResult:
    """Result of a single benchmark example."""
    question: str
    db_id: str
    gold_sql: str
    predicted_sql: str
    exact_match: bool
    execution_match: Optional[bool] = None
    llm_judge_match: Optional[bool] = None
    llm_judge_score: int = 0
    llm_judge_reasoning: str = ""
    is_valid_sql: bool = True
    error: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class BenchmarkReport:
    """Aggregated benchmark results."""
    total_samples: int = 0
    exact_match_count: int = 0
    execution_match_count: int = 0
    llm_judge_match_count: int = 0
    llm_judge_total_score: int = 0
    valid_sql_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    results: List[BenchmarkResult] = field(default_factory=list)
    
    @property
    def exact_match_accuracy(self) -> float:
        return self.exact_match_count / self.total_samples if self.total_samples > 0 else 0.0
    
    @property
    def execution_accuracy(self) -> float:
        executed = sum(1 for r in self.results if r.execution_match is not None)
        if executed == 0:
            return 0.0
        return self.execution_match_count / executed
    
    @property
    def llm_judge_accuracy(self) -> float:
        judged = sum(1 for r in self.results if r.llm_judge_match is not None)
        if judged == 0:
            return 0.0
        return self.llm_judge_match_count / judged
    
    @property
    def llm_judge_avg_score(self) -> float:
        judged = sum(1 for r in self.results if r.llm_judge_match is not None)
        if judged == 0:
            return 0.0
        return self.llm_judge_total_score / judged
    
    @property
    def valid_sql_rate(self) -> float:
        return self.valid_sql_count / self.total_samples if self.total_samples > 0 else 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_samples if self.total_samples > 0 else 0.0
    
    def to_dict(self) -> Dict:
        return {
            "total_samples": self.total_samples,
            "exact_match_accuracy": round(self.exact_match_accuracy * 100, 2),
            "execution_accuracy": round(self.execution_accuracy * 100, 2),
            "llm_judge_accuracy": round(self.llm_judge_accuracy * 100, 2),
            "llm_judge_avg_score": round(self.llm_judge_avg_score, 2),
            "valid_sql_rate": round(self.valid_sql_rate * 100, 2),
            "error_count": self.error_count,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }
