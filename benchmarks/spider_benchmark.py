"""
Spider Benchmark Runner

Main benchmark runner that coordinates data loading, pipeline execution, and evaluation.
Uses modular evaluators for different metrics.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional

from .core import BenchmarkResult, BenchmarkReport, SpiderDataLoader, SQLNormalizer
from .evaluators import evaluate_exact_match


class SpiderBenchmark:
    """Main benchmark runner for Spider evaluation."""
    
    def __init__(self, spider_dir: str, pipeline_func: Callable[[str, str], str] = None):
        """
        Args:
            spider_dir: Path to Spider dataset directory
            pipeline_func: Function that takes (question, schema) and returns SQL
        """
        self.loader = SpiderDataLoader(spider_dir)
        self.pipeline_func = pipeline_func
        self.spider_dir = Path(spider_dir)
        
        # Optional evaluators (set via methods)
        self._use_llm_judge = False
        self._use_execution = False
        self._databases_dir = None
        self._judge_client = None
    
    def set_pipeline(self, pipeline_func: Callable[[str, str], str]):
        """Set the pipeline function to benchmark."""
        self.pipeline_func = pipeline_func
    
    def enable_llm_judge(self, enabled: bool = True):
        """Enable LLM-as-judge evaluation."""
        self._use_llm_judge = enabled
        if enabled:
            from .evaluators.llm_judge import create_judge_client
            self._judge_client = create_judge_client()
    
    def enable_execution_eval(self, databases_dir: str):
        """
        Enable execution accuracy evaluation.
        
        Args:
            databases_dir: Path to Spider databases directory
        """
        self._use_execution = True
        self._databases_dir = databases_dir
    
    def run(
        self,
        n_samples: int = 100,
        shuffle: bool = True,
        seed: int = 42,
        verbose: bool = True,
        save_results: bool = True,
        output_dir: str = "benchmarks/results",
        use_llm_judge: bool = False
    ) -> BenchmarkReport:
        """
        Run the benchmark.
        
        Args:
            n_samples: Number of samples to evaluate
            shuffle: Whether to shuffle samples
            seed: Random seed for reproducibility
            verbose: Whether to print progress
            save_results: Whether to save results to file
            output_dir: Directory to save results
            use_llm_judge: Whether to use LLM as judge for semantic equivalence
        
        Returns:
            BenchmarkReport with aggregated results
        """
        if self.pipeline_func is None:
            raise ValueError("Pipeline function not set. Call set_pipeline() first.")
        
        if not self.loader.load():
            raise RuntimeError("Failed to load Spider dataset")
        
        # Enable LLM judge if requested
        if use_llm_judge:
            self.enable_llm_judge(True)
        
        samples = self.loader.get_samples(n_samples, shuffle, seed)
        report = BenchmarkReport()
        
        if verbose:
            self._print_config(len(samples))
        
        for i, sample in enumerate(samples):
            result = self._evaluate_sample(sample, report)
            report.results.append(result)
            report.total_samples += 1
            report.total_latency_ms += result.latency_ms
            
            if verbose and (i + 1) % 10 == 0:
                self._print_progress(i + 1, len(samples), report)
        
        if verbose:
            print("-" * 60)
            self._print_report(report)
        
        if save_results:
            self._save_results(report, output_dir)
        
        return report
    
    def _evaluate_sample(self, sample: dict, report: BenchmarkReport) -> BenchmarkResult:
        """Evaluate a single sample."""
        question = sample['question']
        db_id = sample['db_id']
        gold_sql = sample['query']
        schema = self.loader.get_schema(db_id)
        
        start_time = time.time()
        
        try:
            predicted_sql = self.pipeline_func(question, schema)
            latency_ms = (time.time() - start_time) * 1000
            
            # Exact match evaluation
            exact_match = evaluate_exact_match(gold_sql, predicted_sql)
            is_valid = self._is_valid_sql(predicted_sql)
            
            result = BenchmarkResult(
                question=question,
                db_id=db_id,
                gold_sql=gold_sql,
                predicted_sql=predicted_sql,
                exact_match=exact_match,
                is_valid_sql=is_valid,
                latency_ms=latency_ms
            )
            
            # LLM Judge evaluation
            if self._use_llm_judge:
                self._evaluate_llm_judge(result, exact_match, report)
            
            # Execution evaluation
            if self._use_execution and self._databases_dir:
                self._evaluate_execution(result, report)
            
            # Update counters
            if exact_match:
                report.exact_match_count += 1
            if is_valid:
                report.valid_sql_count += 1
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            result = BenchmarkResult(
                question=question,
                db_id=db_id,
                gold_sql=gold_sql,
                predicted_sql="",
                exact_match=False,
                is_valid_sql=False,
                error=str(e),
                latency_ms=latency_ms
            )
            report.error_count += 1
        
        return result
    
    def _evaluate_llm_judge(self, result: BenchmarkResult, exact_match: bool, report: BenchmarkReport):
        """Run LLM judge evaluation on a result."""
        if exact_match:
            # Exact match implies LLM judge match
            result.llm_judge_match = True
            result.llm_judge_score = 5
            result.llm_judge_reasoning = "Exact match"
            report.llm_judge_match_count += 1
            report.llm_judge_total_score += 5
        elif result.is_valid_sql:
            from .evaluators.llm_judge import judge_sql_equivalence
            judge_result = judge_sql_equivalence(
                question=result.question,
                gold_sql=result.gold_sql,
                predicted_sql=result.predicted_sql,
                client=self._judge_client
            )
            result.llm_judge_match = judge_result.is_equivalent
            result.llm_judge_score = judge_result.score
            result.llm_judge_reasoning = judge_result.reasoning
            
            if judge_result.is_equivalent:
                report.llm_judge_match_count += 1
            report.llm_judge_total_score += judge_result.score
    
    def _evaluate_execution(self, result: BenchmarkResult, report: BenchmarkReport):
        """Run execution accuracy evaluation."""
        from .evaluators.execution import evaluate_execution
        match, message = evaluate_execution(
            result.gold_sql,
            result.predicted_sql,
            result.db_id,
            self._databases_dir
        )
        result.execution_match = match
        if match:
            report.execution_match_count += 1
    
    def _is_valid_sql(self, sql: str) -> bool:
        """Check if SQL is syntactically valid."""
        try:
            import sqlparse
            parsed = sqlparse.parse(sql)
            return len(parsed) > 0 and parsed[0].get_type() != 'UNKNOWN'
        except Exception:
            return False
    
    def _print_config(self, n_samples: int):
        """Print benchmark configuration."""
        print(f"\nRunning benchmark on {n_samples} samples...")
        if self._use_llm_judge:
            print("  LLM Judge: enabled")
        if self._use_execution:
            print("  Execution Eval: enabled")
        print("-" * 60)
    
    def _print_progress(self, current: int, total: int, report: BenchmarkReport):
        """Print progress update."""
        em = report.exact_match_count / report.total_samples * 100
        if self._use_llm_judge:
            llm = report.llm_judge_accuracy * 100
            print(f"  [{current}/{total}] EM: {em:.1f}% | LLM Judge: {llm:.1f}% | Errors: {report.error_count}")
        else:
            print(f"  [{current}/{total}] Exact Match: {em:.1f}% | Errors: {report.error_count}")
    
    def _print_report(self, report: BenchmarkReport):
        """Print benchmark report."""
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS")
        print("=" * 60)
        print(f"  Total Samples:       {report.total_samples}")
        print(f"  Exact Match:         {report.exact_match_accuracy * 100:.2f}%")
        
        if self._use_llm_judge:
            print(f"  LLM Judge Match:     {report.llm_judge_accuracy * 100:.2f}%")
            print(f"  LLM Judge Avg Score: {report.llm_judge_avg_score:.2f}/5")
        
        if self._use_execution:
            print(f"  Execution Match:     {report.execution_accuracy * 100:.2f}%")
        
        print(f"  Valid SQL Rate:      {report.valid_sql_rate * 100:.2f}%")
        print(f"  Errors:              {report.error_count}")
        print(f"  Avg Latency:         {report.avg_latency_ms:.0f}ms")
        print("=" * 60)
    
    def _save_results(self, report: BenchmarkReport, output_dir: str):
        """Save results to JSON file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_path / f"benchmark_{timestamp}.json"
        
        results_dict = {
            "summary": report.to_dict(),
            "timestamp": timestamp,
            "config": {
                "llm_judge_enabled": self._use_llm_judge,
                "execution_eval_enabled": self._use_execution,
            },
            "details": [
                {
                    "question": r.question,
                    "db_id": r.db_id,
                    "gold_sql": r.gold_sql,
                    "predicted_sql": r.predicted_sql,
                    "exact_match": r.exact_match,
                    "execution_match": r.execution_match,
                    "llm_judge_match": r.llm_judge_match,
                    "llm_judge_score": r.llm_judge_score,
                    "llm_judge_reasoning": r.llm_judge_reasoning,
                    "is_valid_sql": r.is_valid_sql,
                    "error": r.error,
                    "latency_ms": r.latency_ms
                }
                for r in report.results
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"\nResults saved to: {filename}")


def create_pipeline_wrapper():
    """
    Create a wrapper for the NL2SQL pipeline.
    
    Uses the same core pipeline as app.py to ensure identical behavior.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from pipeline.core import NL2SQLPipeline
    
    # Same pipeline as production, just with logging disabled
    pipeline = NL2SQLPipeline(enable_security_logging=False)
    
    return pipeline.generate_sql_only
