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
python -m venv .venv
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

Open [http://127.0.0.1:8001/helios.html](http://127.0.0.1:8001/helios.html).

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

