#!/usr/bin/env python
"""
Quick Benchmark Runner

A simplified script to run benchmarks with sensible defaults.
Usage:
    python run_benchmark.py                    # Run 100 samples
    python run_benchmark.py --samples 50       # Run 50 samples
    python run_benchmark.py --llm-judge        # Use LLM-as-judge
    python run_benchmark.py --execution        # Use execution accuracy
    python run_benchmark.py --full             # Run full dev set
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(
        description="Run NL2SQL benchmark evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_benchmark.py                    # Quick test: 100 samples
  python run_benchmark.py --samples 200      # Medium test: 200 samples  
  python run_benchmark.py --llm-judge        # Enable LLM-as-judge evaluation
  python run_benchmark.py --execution        # Enable execution accuracy
  python run_benchmark.py --full             # Full evaluation: all samples
  python run_benchmark.py --dry-run          # Check setup without running
        """
    )
    parser.add_argument("--samples", "-n", type=int, default=100,
                        help="Number of samples (default: 100)")
    parser.add_argument("--full", action="store_true",
                        help="Run on full dev set (~1034 samples)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--llm-judge", action="store_true",
                        help="Use LLM-as-judge for semantic SQL equivalence")
    parser.add_argument("--execution", action="store_true",
                        help="Use execution accuracy (requires Spider databases)")
    parser.add_argument("--databases-dir", type=str, default=None,
                        help="Path to Spider databases (for --execution)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check setup without running benchmark")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Minimal output")
    
    args = parser.parse_args()
    
    # Check Spider dataset
    spider_dir = Path(__file__).parent / "spider"
    dev_json = spider_dir / "dev.json"
    tables_json = spider_dir / "tables.json"
    
    if not dev_json.exists() or not tables_json.exists():
        print("[ERROR] Spider dataset not found!")
        print(f"\nExpected files at:")
        print(f"  - {dev_json}")
        print(f"  - {tables_json}")
        print(f"\nTo download, run:")
        print(f"  python benchmarks/download_spider.py")
        print(f"\nOr download manually from: https://yale-lily.github.io/spider")
        return 1
    
    # Check databases for execution eval
    if args.execution:
        databases_dir = args.databases_dir or (spider_dir / "database")
        if not Path(databases_dir).exists():
            print("[WARNING] Spider databases not found for execution evaluation!")
            print(f"\nExpected at: {databases_dir}")
            print("\nDownload the full Spider dataset with databases from:")
            print("  https://yale-lily.github.io/spider")
            print("\nContinuing without execution evaluation...")
            args.execution = False
    
    if args.dry_run:
        print("[OK] Spider dataset found!")
        print(f"  - {dev_json}")
        print(f"  - {tables_json}")
        if args.execution:
            print(f"  - Databases: {databases_dir}")
        print("\nSetup looks good. Remove --dry-run to run benchmark.")
        return 0
    
    # Import benchmark
    try:
        from benchmarks.spider_benchmark import SpiderBenchmark, create_pipeline_wrapper
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        print("Make sure you're running from the project root.")
        return 1
    
    # Check Z.AI API key
    from config import ZAI_API_KEY
    if not ZAI_API_KEY:
        print("[ERROR] Z.AI API key not set!")
        print("Add your API key to .env file: ZAI_API_KEY=your-key...")
        return 1
    
    # Create pipeline
    try:
        pipeline = create_pipeline_wrapper()
    except Exception as e:
        print(f"[ERROR] Error creating pipeline: {e}")
        return 1
    
    # Determine sample count
    n_samples = None if args.full else args.samples
    if args.full:
        import json
        with open(dev_json) as f:
            n_samples = len(json.load(f))
        print(f"Running FULL benchmark: {n_samples} samples")
        print("[WARNING] This may take several hours and use significant API quota!")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            return 0
    
    # Print header
    print(f"\n{'='*60}")
    print(f"NL2SQL BENCHMARK - Spider Dataset")
    print(f"{'='*60}")
    print(f"Samples: {n_samples}")
    print(f"Seed: {args.seed}")
    print(f"LLM Judge: {'Enabled' if args.llm_judge else 'Disabled'}")
    print(f"Execution Eval: {'Enabled' if args.execution else 'Disabled'}")
    print(f"{'='*60}")
    
    # Create and configure benchmark
    benchmark = SpiderBenchmark(str(spider_dir), pipeline)
    
    if args.execution:
        benchmark.enable_execution_eval(str(databases_dir))
    
    # Run benchmark
    report = benchmark.run(
        n_samples=n_samples,
        seed=args.seed,
        verbose=not args.quiet,
        use_llm_judge=args.llm_judge
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
