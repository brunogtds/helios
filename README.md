# HELIOS — Hypothesis Exploration with LLM-driven Intelligent Orchestration System

HELIOS is a local application for hypothesis-driven exploratory data analysis. It combines an EDA agent, LLM-based hypothesis generation, a Ranking Agent, statistical validation, and interactive visualizations.

## Analysis workflow

1. Upload a CSV dataset and select the target variable.
2. Review preprocessing options, including binary mapping and numeric discretization.
3. Enter a dataset description and a User Query describing the analytical question.
4. Select the AI provider, model, and hypothesis-generation settings.
5. Generate hypotheses. The EDA agent explores the prepared dataset using Python, SQL, and aggregate queries, then supplies an evidence-based summary to the statistical advisor and hypothesis generator.
6. Review the Ranking tab and statistically validated results, then export the results JSON.

EDA is mandatory for AI context generation. It starts from the dataset schema and can access all rows and columns of the prepared dataset through its tools. Tool output limits do not sample the input dataset. The Generation Context panel shows the summary, query evidence, and execution report.

## Requirements

- Python 3.11 is recommended for the setup below.
- Docker Desktop (Windows) or Docker Engine (Linux), running with Linux containers, for the EDA Python tool.
- An API key for the selected provider: OpenAI, Groq, or Anthropic (Claude).

## Installation

Clone the repository and enter its root directory:

```powershell
git clone https://github.com/brunogtds/helios.git
cd helios
```

The commands below assume that `main.py`, `requirements.txt`, and `Dockerfile.eda` are in the current directory.

### Windows PowerShell

Create an independent environment and install dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

With Docker Desktop running, build the EDA image:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_eda_python.ps1
```

Start the application:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

To use a different port:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1 -Port 8002
```

### Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
docker build -f Dockerfile.eda -t helios-eda-python:1 .
.venv/bin/python -B -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Open [http://127.0.0.1:8001](http://127.0.0.1:8001). The local application's default login is `admin` / `password`.

## Provider configuration

Select the provider and model in the application and paste the corresponding API key, or set its environment variable before starting the server:

| Provider | Environment variable |
| --- | --- |
| OpenAI | `OPENAI_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Claude (Anthropic) | `ANTHROPIC_API_KEY` |

For example, in PowerShell:

```powershell
$env:OPENAI_API_KEY="your-key"
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

On Linux/macOS, use `export OPENAI_API_KEY="your-key"` before starting the server. Set only the keys for providers you intend to use. `.env.example` is a reference; `.env` files are not loaded automatically. Keep API keys out of Git.

EDA, statistical advice, AI hypothesis generation, Ranking Agent, and AI chat use the selected provider/model. Claude support is included through `langchain-anthropic` in `requirements.txt`. For Claude, provider default sampling parameters apply; the HELIOS temperature setting does not apply. Enter a model ID available to your provider account.

## Ranking Agent

After all AI generation iterations, the Ranking Agent reviews the complete unique hypothesis list against the original User Query. It assigns each hypothesis a relevance score from 0 to 10, a rank, an acceptance decision, and a justification. Scores measure query relevance; they do not measure statistical significance or probability and do not establish causality.

Hypotheses are ordered by descending score. Model ranks resolve score ties, with original IDs resolving any remaining ties. Missing, repeated, or inconsistent ranks are normalized from scores. Only accepted hypotheses continue to statistical validation. Heuristic generation methods are unchanged.

The Ranking tab displays accepted and rejected hypotheses with their scores, decisions, and justifications. It also includes an expandable report with a critical summary and unanswered aspects. Ranking report text and UI are in English. Statistical Table View fitness sorting is independent of agent ranking.

The results JSON exposes the report at `run_params.ranking` and in AI method logs as `ranking`. The report contains `ranked_hypotheses` in rank order and `decisions` in original ID order; the generated list remains available as `generated_hypotheses` in the AI logs.

Ranking normally adds one model call. Invalid scores or incomplete reports can trigger up to two repair calls before the job fails. Normalizations and repair attempts are recorded in the report. A provider error fails the job. Ranking is explicitly skipped if the User Query or generated hypothesis list is empty.

## EDA execution and resource limits

The Python tool runs analytical code over `df` in a fresh Docker container using image `helios-eda-python:1`. Each call has a default timeout of 120 seconds and a 4 GB memory limit, with no host mounts or network access. Python code state does not persist across calls. SQL queries use the full `dataset` table in fresh in-memory SQLite with a default timeout of 20 seconds.

To change Python limits, set these variables before starting the server:

```powershell
$env:HELIOS_EDA_PYTHON_MEMORY="8g"
$env:HELIOS_EDA_PYTHON_TIMEOUT="240"
```

Restart the backend after changing the limits. The model receives returned query evidence, which can include explicitly requested dataset rows. Execution reports describe the operations and findings.

## Verification

With dependencies installed, run the standalone backend tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -m unittest test_ranking test_llm_support test_eda_execution
```

For real Python-container checks, build the Docker image first and run:

```powershell
$env:HELIOS_TEST_DOCKER="1"
.\.venv\Scripts\python.exe -B -m unittest test_eda_docker
```

These tests do not require paid model calls. `test_legacy_integration.py` includes comparisons against historical snapshots and backup manifests outside the repository; its full suite requires the original development backup layout.
