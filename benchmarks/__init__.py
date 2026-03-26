"""
NL2SQL Benchmarks

Modular benchmark suite for evaluating the NL2SQL pipeline.

Structure:
- core/: Data classes, data loaders, normalizers
- evaluators/: Different evaluation strategies (exact match, execution, LLM judge)
- spider_benchmark.py: Main benchmark runner
- run_benchmark.py: CLI entry point
- download_spider.py: Dataset download script
"""

from .spider_benchmark import SpiderBenchmark, create_pipeline_wrapper
from .core import BenchmarkResult, BenchmarkReport, SpiderDataLoader, SQLNormalizer

__all__ = [
    'SpiderBenchmark',
    'create_pipeline_wrapper',
    'BenchmarkResult',
    'BenchmarkReport',
    'SpiderDataLoader',
    'SQLNormalizer',
]
