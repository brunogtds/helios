# HELIOS — Hypothesis Exploration with LLM-driven Intelligent Orchestration System

HELIOS is a tool for hypothesis-driven exploratory data analysis over datasets. It combines statistical validation, visual analytics, and LLM-based agents to support the generation, interpretation, and refinement of statistically grounded hypotheses.

The current version runs as a local application with:
- Python FastAPI backend;
- The statistical tests: one-sample t-test, Welch's t-test, ANOVA, and Levene's test;
- LLM support through OpenAI and Groq APIs.

## Requirements

- Python 3.10 or newer;
- One LLM API key, which you should define in your local configurations as:
  - `OPENAI_API_KEY` for OpenAI models;
  - `GROQ_API_KEY` for Groq models;

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR-USER/helios.git
cd helios
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Linux/macOS:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## API keys

Do not hard-code API keys in the source code. Use environment variables instead.

On Linux/macOS:

```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export GROQ_API_KEY="your_groq_api_key_here"
export GEMINI_API_KEY="your_gemini_api_key_here"
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your_openai_api_key_here"
$env:GROQ_API_KEY="your_groq_api_key_here"
$env:GEMINI_API_KEY="your_gemini_api_key_here"
```

You only need to define the keys for the providers you intend to use.

## Running HELIOS locally

Start the backend:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open the frontend.

Option 1: open the landing page directly in your browser:

```text
helios.html
```

## Basic workflow

1. Open `helios.html`.
2. Upload a CSV file.
3. Select the target variable.
4. Optionally map binary columns and discretize numeric columns.
5. Add a dataset description or user intent if relevant.
6. Choose hypothesis-generation methods.
7. Generate hypotheses.
8. Explore significant hypotheses in the visualizations.
9. Use the AI analysis panel to generate a narrative summary and suggested next steps.
10. Download the hypotheses JSON if needed.


```bash
git status
git add .
git commit -m "Describe the update"
git push
```
