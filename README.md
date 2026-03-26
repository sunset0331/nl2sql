# NL-to-SQL: Interpretable Natural Language to SQL Pipeline

A modular, interpretable pipeline that converts natural language questions into SQL queries using LLMs via Z.AI API (OpenAI SDK compatible).

## Features

| Requirement                               | Implementation                                                  |
| ----------------------------------------- | --------------------------------------------------------------- |
| Takes natural language questions as input | Web UI with question input and example queries                  |
| Reasons about the database schema         | Chain-of-thought prompting breaks down query logic step-by-step |
| Generates safe, efficient SQL             | LLM generates SQL with syntax verification and auto-correction  |
| Returns human-readable answers            | "In Plain English" section explains what the query does         |
| Shows its reasoning                       | Displays numbered reasoning steps for transparency              |
| Security hardened                         | Multi-layer prompt injection protection                         |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Flask Web UI                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Security Layer                               │
│         (Input Validation, Prompt Injection Detection)          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Pipeline Modules                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Schema     │→ │  Reasoning   │→ │     SQL      │           │
│  │  Processor   │  │   (CoT)      │  │  Generator   │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                              │                  │
│                                              ▼                  │
│                    ┌──────────────┐  ┌──────────────┐           │
│                    │   Answer     │← │   Verifier   │           │
│                    │  Generator   │  │ & Corrector  │           │
│                    └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    Z.AI API (OpenAI SDK Compatible)
                    (glm-4.7-flash)
```

### Pipeline Stages

1. **Security Validation** - Detects prompt injection attempts, sanitizes inputs
2. **Schema Processing** - Parses CREATE TABLE statements to understand database structure
3. **Chain-of-Thought Reasoning** - Breaks down the question into logical steps (tables needed, joins, filters, etc.)
4. **SQL Generation** - Generates SQL based on the reasoning
5. **Verification & Correction** - Validates syntax and schema references, auto-corrects errors
6. **Answer Generation** - Produces a human-readable explanation of what the query does

## Setup

**This project uses [uv](https://docs.astral.sh/uv/) for local development.** Dependencies are managed via `pyproject.toml` and `uv.lock`. A `requirements.txt` is included for Vercel deployment so `pip install` on Linux fetches the correct binary wheels (e.g. for `pydantic_core`).

1. **Install dependencies:**

   ```bash
   uv sync
   ```

2. **Configure Z.AI API key:**

   - Get your API key from: https://z.ai
   - Create a `.env` file:
     ```
     ZAI_API_KEY=your-Z.AI-api-key
     ```

3. **Run the application:**

   ```bash
   uv run python app.py
   ```

---

## Benchmarking

Built-in benchmark suite based on the Spider dataset for comprehensive evaluation.

### Setup

```bash
# Download Spider dataset
uv run python benchmarks/download_spider.py
```

### Running Benchmarks

```bash
# Basic benchmark (100 samples)
uv run python benchmarks/run_benchmark.py

# With semantic evaluation
uv run python benchmarks/run_benchmark.py --llm-judge

# With execution accuracy (requires Spider databases)
uv run python benchmarks/run_benchmark.py \
  --execution \
  --databases-dir benchmarks/spider/database

# Custom sample size
uv run python benchmarks/run_benchmark.py --num-samples 50
```

### Evaluation Metrics

| Metric                 | Description                                     |
| ---------------------- | ----------------------------------------------- |
| **Exact Match**        | Normalized string comparison of SQL             |
| **Execution Accuracy** | Compares query results against actual databases |
| **LLM Judge**          | Semantic equivalence evaluation via LLM         |
| **Valid SQL Rate**     | Percentage of syntactically valid SQL generated |

### Sample Output

```
============================================================
BENCHMARK RESULTS (100 samples)
============================================================
  Exact Match:         32.00%
  LLM Judge Match:     45.71%
  Execution Match:     78.00%
  Valid SQL Rate:      85.00%
  Avg Latency:         3,124ms
============================================================
```

### Benchmark Structure

```
benchmarks/
├── run_benchmark.py        # CLI entry point
├── spider_benchmark.py     # Main runner
├── download_spider.py      # Dataset download
├── core/
│   ├── results.py          # Result models
│   ├── data_loader.py      # Spider data loading
│   └── normalizer.py       # SQL normalization
└── evaluators/
    ├── exact_match.py      # String matching
    ├── execution.py        # Database execution
    └── llm_judge.py        # Semantic evaluation
```

## Tech Stack

- **Backend:** Python, Flask
- **LLM:** glm-4.7-flash (via Z.AI API, OpenAI SDK compatible)
- **SQL Parsing:** sqlparse
- **Frontend:** Vanilla HTML/CSS/JavaScript
- **Security:** Multi-layer prompt injection detection

## Project Structure

```
├── app.py                  # Flask application entry point
├── config.py               # Configuration management
├── security.py             # Input validation & sanitization
├── pipeline/
│   ├── core.py             # Pipeline orchestration
│   ├── schema_processor.py # Schema parsing
│   ├── reasoning.py        # Chain-of-thought reasoning
│   ├── sql_generator.py    # SQL generation
│   ├── verifier.py         # Validation & correction
│   └── answer_generator.py # Natural language explanation
├── benchmarks/             # Evaluation framework
├── tests/                  # Unit tests
├── utils/
│   └── openai_client.py      # OpenAI SDK client for Z.AI API
├── templates/
│   └── index.html          # Web interface
└── static/
    └── styles.css          # UI styling
```

## Why No SQL Execution in UI?

We intentionally designed this as a **query generation** tool rather than an execution engine:

1. **Security** - Executing arbitrary SQL poses significant risks
2. **Flexibility** - Users can review/modify SQL before running on their databases
3. **Database Agnostic** - Works with any SQL dialect without needing connections
4. **Educational Focus** - Transparent reasoning helps users understand SQL
